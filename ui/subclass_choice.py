from presentation.option_models import OptionViewModel
from ui.compact_choice import render_compact_single_choice


def render_subclass_choice(
    options: tuple[OptionViewModel, ...],
    selected_id: str | None,
    *,
    state_key: str,
    label: str,
) -> str | None:
    return render_compact_single_choice(
        options,
        selected_id,
        state_key=state_key,
        label=label,
        placeholder="Choose a subclass",
        detail_label="View subclass progression",
    )
