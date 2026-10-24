"""Chép SFX thật vào thư mục audio của project.

Danh mục nằm ở ``config/sfx.json``; file gốc ở ``assets/sfx/``. Build chỉ copy
file cục bộ, không gọi mạng. Thiếu asset hoặc ID lạ sẽ báo lỗi rõ ràng.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from . import paths

ASSET_DIR = paths.ROOT / "assets" / "sfx"
CONFIG_PATH = paths.ROOT / "config" / "sfx.json"


def load_catalog() -> dict[str, Any]:
    """Đọc config/sfx.json và trả về phần ``items``."""
    if not CONFIG_PATH.exists():
        raise SystemExit(f"Thiếu danh mục SFX: {paths.rel(CONFIG_PATH)}")
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    items = data.get("items")
    if not isinstance(items, dict) or not items:
        raise SystemExit("config/sfx.json phải có ít nhất một item trong 'items'.")
    return items


def ensure_sfx(target: Path) -> list[Path]:
    """Copy toàn bộ SFX trong danh mục vào ``target``; trả về file đã ghi."""
    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for sfx_id, item in load_catalog().items():
        name = item.get("file")
        if not isinstance(name, str) or not name:
            raise SystemExit(f"SFX '{sfx_id}' thiếu trường 'file'.")
        source = ASSET_DIR / name
        if not source.exists():
            raise SystemExit(
                f"Thiếu SFX: {paths.rel(source)}. "
                "Xem assets/sfx/SOURCES.md để tải lại."
            )
        destination = target / name
        shutil.copyfile(source, destination)
        written.append(destination)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.sfx",
        description="Chép SFX thật trong config/sfx.json vào project.",
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--format", choices=["short", "long"], required=True)
    args = parser.parse_args(argv)

    written = ensure_sfx(paths.audio_dir(args.project_id, args.format) / "sfx")
    for path in written:
        print(f"✓ {paths.rel(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
