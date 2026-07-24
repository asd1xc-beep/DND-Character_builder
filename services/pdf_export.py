from pathlib import Path
from textwrap import fill

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.pdfbase.acroform import AcroForm
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter
from pypdf.generic import BooleanObject, NameObject

from services.save_load import safe_filename


ROOT_DIR = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT_DIR / "output" / "pdf"
TEMPLATE_DIR = ROOT_DIR / "templates" / "pdf"
WOTC_TEMPLATE = TEMPLATE_DIR / "5E_CharacterSheet_Fillable.pdf"

PAGE_WIDTH, PAGE_HEIGHT = letter
MARGIN = 36
FIELD_HEIGHT = 18
LINE_HEIGHT = 14
LABEL_SIZE = 7
TEXT_SIZE = 9

WOTC_FIELD_FONT_SIZES = {
    "AttacksSpellcasting": 8,
    "ProficienciesLang": 7,
    "Equipment": 7,
    "Features and Traits": 7,
    "Feat+Traits": 7,
    "Backstory": 8,
    "Allies": 8,
    "Treasure": 8,
}

WOTC_FIELD_WRAP_WIDTHS = {
    "AttacksSpellcasting": 33,
    "ProficienciesLang": 38,
    "Equipment": 31,
    "Features and Traits": 41,
    "Feat+Traits": 65,
    "Backstory": 80,
    "Allies": 65,
    "Treasure": 65,
}

WOTC_SPELL_FIELDS = {
    0: [f"Spells {index}" for index in range(1014, 1023)],
    1: [f"Spells {index}" for index in range(1023, 1034)],
    2: [f"Spells {index}" for index in range(1034, 1047)],
    3: [f"Spells {index}" for index in range(1047, 1060)],
    4: [f"Spells {index}" for index in range(1060, 1073)],
    5: [f"Spells {index}" for index in range(1073, 1082)],
    6: [f"Spells {index}" for index in range(1082, 1091)],
    7: [f"Spells {index}" for index in range(1091, 1100)],
    8: [f"Spells 1010{index}" for index in range(0, 7)],
    9: [f"Spells 1010{index}" for index in range(7, 14)],
}

WOTC_SLOT_FIELDS = {
    1: "19",
    2: "20",
    3: "21",
    4: "22",
    5: "23",
    6: "24",
    7: "25",
    8: "26",
    9: "27",
}


def export_character_pdf(sheet):
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    name = sheet.get("identity", {}).get("name") or "unnamed_character"
    path = PDF_DIR / f"{safe_filename(name)}_character_sheet.pdf"
    if WOTC_TEMPLATE.exists():
        fill_wotc_template(sheet, path)
    else:
        create_editable_character_pdf(sheet, path)
    return path


def fill_wotc_template(sheet, path, template_path=WOTC_TEMPLATE):
    reader = PdfReader(str(template_path))
    writer = PdfWriter()
    writer.clone_reader_document_root(reader)

    field_values = build_wotc_field_values(sheet)
    for page in writer.pages:
        writer.update_page_form_field_values(page, field_values, auto_regenerate=False)

    # Use pypdf's generated appearances so long fields render predictably.
    if "/AcroForm" in writer._root_object:
        writer._root_object["/AcroForm"].update({
            NameObject("/NeedAppearances"): BooleanObject(False)
        })

    with Path(path).open("wb") as file:
        writer.write(file)
    return path


def build_wotc_field_values(sheet):
    ability = {item["name"]: item for item in sheet["abilities"]}
    saves = {item["name"]: item for item in sheet["saving_throws"]}
    skills = {item["name"]: item for item in sheet["skills"]}
    resources = sheet.get("resources", {})
    hp = sheet["core_stats"]["hit_points"]

    values = {
        "CharacterName": sheet["identity"]["name"],
        "CharacterName 2": sheet["identity"]["name"],
        "ClassLevel": f"{sheet['identity']['class']} {sheet['identity']['level']}",
        "Background": sheet["identity"]["background"],
        "Race ": sheet["identity"]["species"],
        "XP": "0",
        "ProfBonus": sheet["core_stats"]["proficiency_bonus_display"],
        "AC": str(sheet["core_stats"]["armor_class"]),
        "Initiative": sheet["core_stats"]["initiative_display"],
        "Speed": f"{sheet['identity']['speed']} ft",
        "HPMax": str(hp.get("max", "")),
        "HPCurrent": str(hp.get("current", "")),
        "HDTotal": sheet["core_stats"]["hit_die"],
        "HD": sheet["core_stats"]["hit_die"],
        "Passive": passive_perception(skills),
        "ProficienciesLang": wotc_value("ProficienciesLang", proficiencies_text(sheet)),
        "Equipment": wotc_value("Equipment", join_values(sheet["equipment"])),
        "Features and Traits": wotc_value("Features and Traits", features_text(sheet)),
        "Feat+Traits": wotc_value("Feat+Traits", features_text(sheet)),
        "AttacksSpellcasting": "",
        "Spellcasting Class 2": sheet["identity"]["class"],
        "SpellcastingAbility 2": sheet["spells"].get("spellcasting_ability", ""),
    }
    values.update(wotc_attack_field_values(sheet))

    spell_slots = resources.get("spell_slots", {})
    for spell_level, field_suffix in WOTC_SLOT_FIELDS.items():
        slots = spell_slots.get(str(spell_level), "")
        values[f"SlotsTotal {field_suffix}"] = str(slots)
        values[f"SlotsRemaining {field_suffix}"] = str(slots)

    ability_fields = {
        "Strength": ("STR", "STRmod"),
        "Dexterity": ("DEX", "DEXmod "),
        "Constitution": ("CON", "CONmod"),
        "Intelligence": ("INT", "INTmod"),
        "Wisdom": ("WIS", "WISmod"),
        "Charisma": ("CHA", "CHamod"),
    }
    for name, (score_field, mod_field) in ability_fields.items():
        values[score_field] = str(ability[name]["score"])
        values[mod_field] = ability[name]["modifier_display"]

    save_fields = {
        "Strength": "ST Strength",
        "Dexterity": "ST Dexterity",
        "Constitution": "ST Constitution",
        "Intelligence": "ST Intelligence",
        "Wisdom": "ST Wisdom",
        "Charisma": "ST Charisma",
    }
    for name, field in save_fields.items():
        values[field] = saves[name]["bonus_display"]

    skill_fields = {
        "Acrobatics": "Acrobatics",
        "Animal Handling": "Animal",
        "Arcana": "Arcana",
        "Athletics": "Athletics",
        "Deception": "Deception ",
        "History": "History ",
        "Insight": "Insight",
        "Intimidation": "Intimidation",
        "Investigation": "Investigation ",
        "Medicine": "Medicine",
        "Nature": "Nature",
        "Perception": "Perception ",
        "Performance": "Performance",
        "Persuasion": "Persuasion",
        "Religion": "Religion",
        "Sleight of Hand": "SleightofHand",
        "Stealth": "Stealth ",
        "Survival": "Survival",
    }
    for name, field in skill_fields.items():
        values[field] = skills[name]["bonus_display"]

    populate_wotc_spell_fields(values, sheet)

    return values


def wotc_attack_field_values(sheet):
    rows = attack_rows(sheet)
    return {
        "Wpn Name": rows[0]["name"],
        "Wpn1 AtkBonus": rows[0]["attack_display"],
        "Wpn1 Damage": rows[0]["damage_display"],
        "Wpn Name 2": rows[1]["name"],
        "Wpn2 AtkBonus ": rows[1]["attack_display"],
        "Wpn2 Damage ": rows[1]["damage_display"],
        "Wpn Name 3": rows[2]["name"],
        "Wpn3 AtkBonus  ": rows[2]["attack_display"],
        "Wpn3 Damage ": rows[2]["damage_display"],
    }


def attack_rows(sheet):
    blanks = {"name": "", "attack_display": "", "damage_display": "", "kind": ""}
    weapon = next(
        (profile for profile in sheet.get("attack_profiles", []) if profile.get("kind") == "weapon"),
        blanks,
    )
    cantrip = next(
        (profile for profile in sheet.get("attack_profiles", []) if profile.get("kind") == "cantrip"),
        blanks,
    )
    return [weapon, cantrip, blanks]


def populate_wotc_spell_fields(values, sheet):
    for level, spells in spells_grouped_by_level(sheet).items():
        fields = WOTC_SPELL_FIELDS.get(level, [])
        for field, spell in zip(fields, spells):
            values[field] = spell


def spells_grouped_by_level(sheet):
    details_by_name = {
        detail.get("name"): detail
        for detail in sheet.get("spell_details", [])
    }
    grouped = {level: [] for level in WOTC_SPELL_FIELDS}
    spells = sheet.get("spells", {})
    for spell in unique_values(spells.get("cantrips", [])):
        grouped[0].append(spell)
    for spell in unique_values(
        list(spells.get("prepared", []))
        + list(spells.get("spellbook", []))
        + list(spells.get("known", []))
        + list(spells.get("granted", []))
    ):
        if spell in grouped[0]:
            continue
        level = details_by_name.get(spell, {}).get("level")
        if not isinstance(level, int) or level not in WOTC_SPELL_FIELDS:
            level = 1
        grouped[level].append(spell)
    return grouped


def spells_by_level_text(sheet):
    lines = []
    for level, spells in spells_grouped_by_level(sheet).items():
        if not spells:
            continue
        label = "Cantrips" if level == 0 else f"Level {level}"
        lines.append(f"{label}: {join_values(spells)}")
    return "\n".join(lines)


def wotc_value(field_name, value):
    text = str(value or "")
    if field_name in WOTC_FIELD_WRAP_WIDTHS:
        text = wrap_multiline(text, WOTC_FIELD_WRAP_WIDTHS[field_name])
    if field_name in WOTC_FIELD_FONT_SIZES:
        return (text, "/Helv", WOTC_FIELD_FONT_SIZES[field_name])
    return text


def wrap_multiline(text, width):
    lines = []
    for paragraph in text.splitlines():
        if paragraph:
            lines.append(fill(paragraph, width=width))
        else:
            lines.append("")
    return "\n".join(lines)


def passive_perception(skills):
    perception = skills.get("Perception", {}).get("bonus", 0)
    return str(10 + perception)


def proficiencies_text(sheet):
    proficiencies = sheet["proficiencies"]
    parts = [
        "Armor: " + join_values(proficiencies["armor"]),
        "Weapons: " + join_values(proficiencies["weapons"]),
        "Tools: " + join_values(proficiencies["tools"]),
        "Languages: " + join_values(proficiencies["languages"]),
    ]
    return "\n".join(part for part in parts if not part.endswith(": "))


def features_text(sheet):
    origin_feats = unique_values(sheet.get("origin_feats", []))
    general_feats = unique_values(sheet.get("general_feats", []))
    features = feature_detail_lines(
        sheet,
        [
            feature for feature in unique_values(sheet.get("features", []))
            if feature not in origin_feats
            and feature not in general_feats
            and not feature.startswith("Origin Feat:")
        ],
    )
    origin_feat_lines = feature_detail_lines(sheet, origin_feats)
    general_feat_lines = general_feat_detail_lines(sheet, general_feats)
    resources = resources_text(sheet.get("resources", {})).replace("\n", "; ")
    masteries = join_values(unique_values(sheet.get("weapon_masteries", [])))
    parts = [
        "Origin feats:\n" + "\n".join(origin_feat_lines),
        "General feats:\n" + "\n".join(general_feat_lines),
        "Features:\n" + "\n".join(features),
        "Resources: " + resources,
        "Weapon mastery: " + masteries,
    ]
    return "\n".join(part for part in parts if not part.endswith(": ") and not part.endswith(":\n"))


def feature_detail_lines(sheet, feature_names):
    details = {
        detail.get("name"): detail
        for detail in sheet.get("feature_details", [])
    }
    lines = []
    for feature in feature_names:
        detail = details.get(feature, {})
        description = detail.get("description", "")
        lines.append(f"{feature}: {description}" if description else feature)
        for related in detail.get("related_features", []):
            label = related.get("name", "")
            if related.get("cost"):
                label = f"{label} - Cost: {related['cost']}"
            if related.get("description"):
                lines.append(f"  {label}: {related['description']}")
            elif label:
                lines.append(f"  {label}")
    return lines


def general_feat_detail_lines(sheet, feature_names):
    details_by_name = {}
    for detail in sheet.get("general_feat_details", []):
        details_by_name.setdefault(detail.get("name", ""), []).append(detail)
    descriptions = {
        detail.get("name"): detail.get("description", "")
        for detail in sheet.get("feature_details", [])
    }
    lines = []
    for feature in feature_names:
        instances = details_by_name.get(feature, [])
        if instances:
            for instance in instances:
                label = feat_detail_label(instance)
                description = descriptions.get(feature, "")
                lines.append(f"{label}: {description}" if description else label)
        else:
            description = descriptions.get(feature, "")
            lines.append(f"{feature}: {description}" if description else feature)
    return lines


def feat_detail_label(instance):
    choices = instance.get("choices", {})
    parts = []
    if choices.get("ability"):
        parts.append(str(choices["ability"]))
    for key, value in choices.items():
        if key == "ability":
            continue
        label = key.replace("_", " ").title()
        if isinstance(value, list):
            value_text = ", ".join(str(item) for item in value if item)
        else:
            value_text = str(value)
        if value_text:
            parts.append(f"{label}: {value_text}")
    if not parts:
        return instance.get("name", "")
    return f"{instance.get('name', '')} ({'; '.join(parts)})"


def attacks_text(sheet):
    spells = sheet.get("spells", {})
    parts = []
    if sheet.get("weapon_masteries"):
        parts.append("Weapon Masteries: " + join_values(sheet["weapon_masteries"]))
    if spells.get("cantrips"):
        parts.append("Cantrips: " + join_values(spells["cantrips"]))
    if spells.get("granted"):
        parts.append("Granted: " + join_values(spells["granted"]))
    spell_details = spell_detail_lines(sheet)
    if spell_details:
        parts.append("Spell details:\n" + "\n".join(spell_details))
    return "\n".join(parts)


def spell_detail_lines(sheet):
    return [
        f"{detail.get('name')}: {detail.get('description')}"
        for detail in sheet.get("spell_details", [])
        if detail.get("name") and detail.get("description")
    ]


def create_editable_character_pdf(sheet, path):
    pdf = canvas.Canvas(str(path), pagesize=letter)
    pdf.setTitle(f"{sheet['identity'].get('name', 'Character')} Character Sheet")
    pdf.acroform = AcroForm(pdf)

    draw_page_one(pdf, sheet)
    pdf.showPage()
    pdf.acroform = AcroForm(pdf)
    draw_page_two(pdf, sheet)
    pdf.save()
    return path


def draw_page_one(pdf, sheet):
    draw_header(pdf, sheet, "Character Sheet")
    y = PAGE_HEIGHT - 110

    draw_section_title(pdf, "Core", MARGIN, y)
    y -= 22
    draw_text_field(pdf, "character_name", "Character Name", sheet["identity"]["name"], MARGIN, y, 210)
    draw_text_field(pdf, "class_level", "Class & Level", f"{sheet['identity']['class']} {sheet['identity']['level']}", 260, y, 130)
    draw_text_field(pdf, "background", "Background", sheet["identity"]["background"], 410, y, 130)
    y -= 34
    draw_text_field(pdf, "species", "Species", sheet["identity"]["species"], MARGIN, y, 140)
    draw_text_field(pdf, "size", "Size", sheet["identity"]["size"], 190, y, 70)
    draw_text_field(pdf, "speed", "Speed", f"{sheet['identity']['speed']} ft", 280, y, 70)
    draw_text_field(pdf, "proficiency_bonus", "Proficiency Bonus", sheet["core_stats"]["proficiency_bonus_display"], 370, y, 80)
    draw_text_field(pdf, "initiative", "Initiative", sheet["core_stats"]["initiative_display"], 470, y, 70)
    y -= 34
    draw_text_field(pdf, "armor_class", "Armor Class", str(sheet["core_stats"]["armor_class"]), MARGIN, y, 80)
    draw_text_field(pdf, "max_hp", "Max HP", str(sheet["core_stats"]["hit_points"].get("max", "")), 140, y, 80)
    draw_text_field(pdf, "current_hp", "Current HP", str(sheet["core_stats"]["hit_points"].get("current", "")), 240, y, 80)
    draw_text_field(pdf, "hit_die", "Hit Die", sheet["core_stats"]["hit_die"], 340, y, 80)

    y -= 50
    draw_section_title(pdf, "Abilities", MARGIN, y)
    y -= 24
    x = MARGIN
    for ability in sheet["abilities"]:
        draw_text_field(pdf, f"ability_{slug(ability['name'])}_score", ability["name"], str(ability["score"]), x, y, 70)
        draw_text_field(pdf, f"ability_{slug(ability['name'])}_mod", "Mod", ability["modifier_display"], x, y - 28, 70)
        x += 86

    y -= 88
    draw_section_title(pdf, "Saving Throws", MARGIN, y)
    draw_section_title(pdf, "Skills", 300, y)
    y -= 22
    draw_bonus_list(pdf, "save", sheet["saving_throws"], MARGIN, y, 240, 6)
    draw_bonus_list(pdf, "skill", sheet["skills"], 300, y, 245, 18)


def draw_page_two(pdf, sheet):
    draw_header(pdf, sheet, "Features, Spells, Equipment")
    y = PAGE_HEIGHT - 110

    left = MARGIN
    right = 316
    width = 240

    draw_section_title(pdf, "Proficiencies", left, y)
    y -= 22
    draw_multiline_field(pdf, "armor_proficiencies", "Armor", join_values(sheet["proficiencies"]["armor"]), left, y, width, 42)
    y -= 58
    draw_multiline_field(pdf, "weapon_proficiencies", "Weapons", join_values(sheet["proficiencies"]["weapons"]), left, y, width, 42)
    y -= 58
    draw_multiline_field(pdf, "tool_proficiencies", "Tools", join_values(sheet["proficiencies"]["tools"]), left, y, width, 42)
    y -= 58
    draw_multiline_field(pdf, "languages", "Languages", join_values(sheet["proficiencies"]["languages"]), left, y, width, 42)

    y = PAGE_HEIGHT - 110
    draw_section_title(pdf, "Spells", right, y)
    y -= 22
    draw_multiline_field(pdf, "spell_cantrips", "Cantrips", join_values(sheet["spells"]["cantrips"]), right, y, width, 46)
    y -= 62
    known_label = "Spellbook" if sheet["spells"].get("spellbook") else "Known"
    known_spells = sheet["spells"].get("spellbook") or sheet["spells"]["known"]
    draw_multiline_field(pdf, "spell_known", known_label, join_values(known_spells), right, y, width, 46)
    y -= 62
    draw_multiline_field(pdf, "spell_prepared", "By Level", spells_by_level_text(sheet), right, y, width, 70)
    y -= 86
    draw_multiline_field(pdf, "spell_granted", "Species / Feat Spells", join_values(sheet["spells"]["granted"]), right, y, width, 52)

    y = 350
    draw_section_title(pdf, "Features and Resources", MARGIN, y)
    y -= 22
    draw_multiline_field(pdf, "features", "Features", join_values(sheet["features"]), MARGIN, y, 250, 140)
    draw_multiline_field(pdf, "resources", "Resources", resources_text(sheet["resources"]), 310, y, 235, 70)
    draw_multiline_field(pdf, "weapon_masteries", "Weapon Mastery", join_values(sheet["weapon_masteries"]), 310, y - 86, 235, 54)

    y = 160
    draw_section_title(pdf, "Equipment and Notes", MARGIN, y)
    y -= 22
    draw_multiline_field(pdf, "equipment", "Equipment", join_values(sheet["equipment"]), MARGIN, y, 250, 105)
    draw_multiline_field(pdf, "notes", "Notes", sheet["identity"].get("notes", ""), 310, y, 235, 105)


def draw_header(pdf, sheet, title):
    pdf.setFillColor(colors.HexColor("#202124"))
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(MARGIN, PAGE_HEIGHT - 48, title)
    pdf.setFont("Helvetica", 9)
    pdf.drawRightString(PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 44, sheet["identity"].get("name") or "Unnamed Character")
    pdf.setStrokeColor(colors.HexColor("#60646c"))
    pdf.line(MARGIN, PAGE_HEIGHT - 62, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 62)


def draw_section_title(pdf, title, x, y):
    pdf.setFillColor(colors.HexColor("#202124"))
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(x, y, title)


def draw_label(pdf, label, x, y):
    pdf.setFillColor(colors.HexColor("#4f5661"))
    pdf.setFont("Helvetica-Bold", LABEL_SIZE)
    pdf.drawString(x, y, label.upper())


def draw_text_field(pdf, name, label, value, x, y, width):
    draw_label(pdf, label, x, y + FIELD_HEIGHT + 3)
    pdf.acroform.textfield(
        name=name,
        value=str(value or ""),
        x=x,
        y=y,
        width=width,
        height=FIELD_HEIGHT,
        borderStyle="underlined",
        borderColor=colors.HexColor("#777777"),
        fillColor=colors.white,
        textColor=colors.black,
        fontName="Helvetica",
        fontSize=TEXT_SIZE,
    )


def draw_multiline_field(pdf, name, label, value, x, y, width, height):
    draw_label(pdf, label, x, y + height + 4)
    pdf.acroform.textfield(
        name=name,
        value=str(value or ""),
        x=x,
        y=y,
        width=width,
        height=height,
        borderStyle="solid",
        borderColor=colors.HexColor("#777777"),
        fillColor=colors.white,
        textColor=colors.black,
        fontName="Helvetica",
        fontSize=TEXT_SIZE,
        fieldFlags="multiline",
    )


def draw_bonus_list(pdf, prefix, rows, x, y, width, limit):
    name_width = width - 54
    for index, row in enumerate(rows[:limit]):
        row_y = y - (index * 17)
        marker = "P" if row.get("proficient") else ""
        if row.get("expertise"):
            marker = "E"
        pdf.setFillColor(colors.HexColor("#202124"))
        pdf.setFont("Helvetica", 8)
        pdf.drawString(x, row_y + 5, row["name"])
        pdf.acroform.textfield(
            name=f"{prefix}_{slug(row['name'])}_bonus",
            value=f"{row['bonus_display']} {marker}".strip(),
            x=x + name_width,
            y=row_y,
            width=48,
            height=14,
            borderStyle="underlined",
            borderColor=colors.HexColor("#777777"),
            fillColor=colors.white,
            textColor=colors.black,
            fontName="Helvetica",
            fontSize=8,
        )


def join_values(values):
    return ", ".join(str(value) for value in values if value)


def unique_values(values):
    seen = set()
    unique = []
    for value in values:
        if value and value not in seen:
            unique.append(value)
            seen.add(value)
    return unique


def resources_text(resources):
    ignored = {"proficiency_bonus"}
    return "\n".join(
        f"{key.replace('_', ' ').title()}: {value}"
        for key, value in resources.items()
        if key not in ignored
    )


def slug(value):
    return "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_")
