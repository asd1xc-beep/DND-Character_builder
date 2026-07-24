"""Build a portable source zip for the local character builder."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT_DIR / "dnd-character-builder-portable.zip"

EXCLUDED_DIRS = {
    ".agents",
    ".codex",
    ".git",
    ".pytest_cache",
    ".pytest-tmp",
    ".ruff_cache",
    ".tmp",
    ".venv",
    ".work",
    "__pycache__",
    "outputs",
    "tmp",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log", ".zip"}
KEEP_OUTPUT_FILES = {
    Path("output/pdf/.gitkeep"),
    Path("output/packages/.gitkeep"),
    Path("output/saved_characters/.gitkeep"),
}


def normalized_relative(path: Path) -> Path:
    return path.relative_to(ROOT_DIR)


def should_include(path: Path, output_path: Path) -> bool:
    rel_path = normalized_relative(path)
    if path == output_path:
        return False
    if any(part in EXCLUDED_DIRS for part in rel_path.parts):
        return False
    if rel_path in KEEP_OUTPUT_FILES:
        return True
    if rel_path.parts[:2] in {
        ("output", "packages"),
        ("output", "pdf"),
        ("output", "saved_characters"),
    }:
        return False
    return path.suffix.lower() not in EXCLUDED_SUFFIXES


def project_files(output_path: Path):
    for path in sorted(ROOT_DIR.rglob("*")):
        if path.is_file() and should_include(path, output_path):
            yield path


def build_zip(output_path: Path) -> Path:
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    for keep_file in KEEP_OUTPUT_FILES:
        full_path = ROOT_DIR / keep_file
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.touch(exist_ok=True)

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in project_files(output_path):
            archive.write(path, normalized_relative(path).as_posix())
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Create a portable D&D Character Builder zip.")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Destination zip path. Defaults to dnd-character-builder-portable.zip in the project root.",
    )
    args = parser.parse_args()

    output_path = build_zip(Path(args.output))
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"Wrote {output_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
