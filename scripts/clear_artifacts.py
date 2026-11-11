"""
Remove generated healing artifacts (audit logs, snapshots, screenshots, SQLite KB).

Usage (from repo root):
    python scripts/clear_artifacts.py
    python scripts/clear_artifacts.py --dry-run
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from framework.config.settings import Settings, get_settings


def _clear_tree(directory: Path, dry_run: bool) -> int:
    removed = 0
    if not directory.is_dir():
        return 0
    for child in directory.iterdir():
        removed += 1
        if dry_run:
            print(f"  would remove: {child}")
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    return removed


def clear_artifacts(settings: Settings, dry_run: bool) -> int:
    base = settings.artifacts_dir.expanduser().resolve()
    sqlite = settings.sqlite_path.expanduser().resolve()
    total = 0

    for sub in ("logs", "html", "screenshots"):
        path = base / sub
        count = _clear_tree(path, dry_run)
        if count:
            label = "would clear" if dry_run else "cleared"
            print(f"{label} {count} item(s) under {path}")
        elif not dry_run and not path.is_dir():
            path.mkdir(parents=True, exist_ok=True)
        total += count

    if sqlite.is_file():
        total += 1
        if dry_run:
            print(f"  would remove: {sqlite}")
        else:
            sqlite.unlink()
            print(f"removed {sqlite}")
    elif not dry_run:
        sqlite.parent.mkdir(parents=True, exist_ok=True)

    if dry_run:
        print(f"[dry-run] would reset artifacts under {base}")
    else:
        print(f"Artifacts reset under {base}")
    return total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Clear healing runtime artifacts.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be deleted without removing files.",
    )
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=None,
        help="Override artifacts directory (default: from .env / Settings).",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    if args.artifacts_dir is not None:
        root = args.artifacts_dir.expanduser().resolve()
        settings = settings.model_copy(
            update={
                "artifacts_dir": root,
                "sqlite_path": root / "locator_kb.db",
            }
        )

    clear_artifacts(settings, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
