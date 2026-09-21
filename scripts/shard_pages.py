"""One-time migration of imported articles into smaller CMS collections."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = (ROOT / "content" / "pages").resolve()
if PAGES.parent != (ROOT / "content").resolve() or PAGES.name != "pages":
    raise SystemExit("Unexpected page directory")
for path in PAGES.glob("*.json"):
    if not path.stem.isdigit():
        continue
    target_dir = PAGES / f"imported-{int(path.stem) % 12:02d}"
    if target_dir.resolve().parent != PAGES:
        raise SystemExit("Refusing to move outside page directory")
    target_dir.mkdir(exist_ok=True)
    path.rename(target_dir / path.name)
print("Moved imported pages into 12 editor collections")
