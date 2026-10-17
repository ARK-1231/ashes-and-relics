"""Restore missing runtime character PNGs from the bundled archive."""

from pathlib import Path
from zipfile import ZipFile


def main():
    root = Path(__file__).resolve().parents[1]
    archive = root / "assets/sprites/archive/superseded_assets_2026-08-29.zip"
    restored = 0
    with ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            parts = entry.filename.replace("\\", "/").split("/")
            if parts[0] not in ("frames_v5", "frames_v6") or not parts[-1].endswith(".png"):
                continue
            actor = "player" if parts[0] == "frames_v5" else "enemies"
            base = root / "assets/sprites" / actor
            target = base.joinpath(*parts).resolve()
            if not target.is_relative_to(base.resolve()):
                raise ValueError(f"Invalid archive path: {entry.filename}")
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(bundle.read(entry))
                restored += 1
    print(f"Restored {restored} missing character frames.")


if __name__ == "__main__":
    main()
