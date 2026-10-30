"""Catalog visual: kind hợp lệ, kiểm tra ``visual.data`` và gộp giá trị mặc định.

Nguồn sự thật là ``config/visuals.json``. Remotion không chứa dữ liệu nào: build
gọi ``resolve`` để ghi đầy đủ ``visual.data`` vào props.

    python -m pipeline.visuals --list     # bảng kind cho người và agent đọc
"""

from __future__ import annotations

import argparse
import sys
from functools import cache
from typing import Any

import jsonschema

from . import config


@cache
def catalog() -> dict[str, Any]:
    return config.read_json(config.CONFIG_DIR / "visuals.json")


def kinds() -> tuple[str, ...]:
    """Các kind có component vẽ trong Remotion."""
    return tuple(catalog()["kinds"])


def passthrough() -> tuple[str, ...]:
    """Kind hợp lệ trong schema nhưng không có visual procedural."""
    return tuple(catalog()["passthrough"])


def all_kinds() -> tuple[str, ...]:
    return passthrough() + kinds()


def defaults(kind: str) -> dict[str, Any]:
    return config.deep_merge({}, catalog()["kinds"][kind].get("defaults") or {})


def data_errors(visual: dict[str, Any] | None) -> list[str]:
    """Lỗi của một ``scene.visual``; rỗng = hợp lệ (không gồm tiền tố scene)."""
    if not visual:
        return []
    kind = visual.get("kind")
    if kind not in all_kinds():
        return [
            f"visual.kind '{kind}' không có trong config/visuals.json. "
            f"Chọn một trong: {', '.join(all_kinds())}"
        ]
    data = visual.get("data")
    if not data:
        if kind in kinds() and catalog()["kinds"][kind].get("requireData"):
            return [
                f"visual '{kind}' cần visual.data của chủ đề này: giá trị mặc định chỉ là "
                "mẫu trung tính. Xem `python -m pipeline.visuals --list`."
            ]
        return []
    if kind not in kinds():
        return [f"visual.kind '{kind}' không nhận visual.data"]
    validator = jsonschema.Draft202012Validator(catalog()["kinds"][kind]["dataSchema"])
    errors: list[str] = []
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        path = ".".join(str(part) for part in err.path) or "<data>"
        errors.append(f"visual.data.{path}: {err.message}")
    return errors


def resolve(visual: dict[str, Any] | None) -> dict[str, Any] | None:
    """Gộp ``defaults`` của kind vào ``visual.data``; kind khác giữ nguyên."""
    if not visual or visual.get("kind") not in kinds():
        return visual
    resolved = dict(visual)
    resolved["data"] = config.deep_merge(defaults(visual["kind"]), visual.get("data") or {})
    return resolved


def render_listing() -> str:
    lines = ["# Visual có sẵn", ""]
    for kind, entry in catalog()["kinds"].items():
        lines.append(f"## {kind}")
        lines.append(f"- {entry['summary']}")
        lines.append(f"- Dùng khi: {entry['useFor']}")
        keys = list((entry["dataSchema"].get("properties") or {}))
        need = "BẮT BUỘC" if entry.get("requireData") else "tuỳ chọn"
        lines.append(f"- visual.data ({need}): {', '.join(keys) if keys else '(không có)'}")
        lines.append("")
    lines.append(f"Kind không vẽ procedural: {', '.join(passthrough())}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.visuals", description="Xem catalog visual."
    )
    parser.add_argument("--list", action="store_true", help="In bảng kind + data")
    args = parser.parse_args(argv)
    if args.list:
        print(render_listing())
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
