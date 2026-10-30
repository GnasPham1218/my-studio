"""Nơi duy nhất đọc config dùng chung của repo.

| File | Ý nghĩa | Hàm |
|---|---|---|
| ``config/formats.json`` | Luật NỘI DUNG theo độ dài (short, long) | ``format_rules`` |
| ``config/aspects.json`` | Bố cục theo KHUNG HÌNH (vertical, horizontal, square) | ``aspect`` |
| ``config/templates/<id>.json`` | Giao diện (màu, nền, caption, chrome) | ``template`` |
| ``config/visuals.json`` | Catalog visual: kind, schema dữ liệu, mặc định | ``pipeline.visuals`` |

Mọi module khác phải đi qua đây thay vì tự ``json.loads`` file config, để một
thay đổi cấu trúc chỉ cần sửa ở một nơi.
"""

from __future__ import annotations

import copy
import json
from functools import cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
TEMPLATES_DIR = CONFIG_DIR / "templates"
SCHEMAS_DIR = ROOT / "schemas"

BASE_TEMPLATE = "_base"
DEFAULT_TEMPLATE = "tech-explainer"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def deep_merge(base: Any, override: Any) -> Any:
    """Gộp dict lồng nhau; kiểu khác (list, số, null) thì lấy giá trị ghi đè."""
    if isinstance(base, dict) and isinstance(override, dict):
        merged = {key: copy.deepcopy(value) for key, value in base.items()}
        for key, value in override.items():
            merged[key] = deep_merge(base.get(key), value)
        return merged
    return copy.deepcopy(override)


# ---------------------------------------------------------------- formats


@cache
def _formats() -> dict[str, Any]:
    return read_json(CONFIG_DIR / "formats.json")


def format_ids() -> tuple[str, ...]:
    return tuple(_formats()["formats"])


def format_rules(fmt: str) -> dict[str, Any]:
    try:
        return _formats()["formats"][fmt]
    except KeyError:
        raise SystemExit(
            f"Format không hợp lệ: {fmt!r}. Chọn một trong: {', '.join(format_ids())}"
        ) from None


def words_per_second() -> float:
    return float(_formats()["wordsPerSecond"])


# ---------------------------------------------------------------- aspects


@cache
def _aspects() -> dict[str, Any]:
    return read_json(CONFIG_DIR / "aspects.json")["aspects"]


def aspect_ids() -> tuple[str, ...]:
    return tuple(_aspects())


def aspect(aspect_id: str) -> dict[str, Any]:
    try:
        return _aspects()[aspect_id]
    except KeyError:
        raise SystemExit(
            f"Khung hình không hợp lệ: {aspect_id!r}. "
            f"Chọn một trong: {', '.join(aspect_ids())}"
        ) from None


def default_aspect(fmt: str) -> str:
    return str(format_rules(fmt)["defaultAspect"])


def layout(aspect_id: str) -> dict[str, Any]:
    """Khối bố cục đưa vào ``props.layout`` (Remotion chỉ đọc khối này)."""
    return {"aspect": aspect_id, **copy.deepcopy(aspect(aspect_id))}


# ---------------------------------------------------------------- templates


def template_ids() -> list[str]:
    return sorted(
        path.stem for path in TEMPLATES_DIR.glob("*.json") if path.stem != BASE_TEMPLATE
    )


def template_path(template_id: str) -> Path:
    return TEMPLATES_DIR / f"{template_id}.json"


def template(template_id: str) -> dict[str, Any]:
    """Template đầy đủ: ``_base.json`` được gộp dưới template đã chọn."""
    path = template_path(template_id)
    if not path.exists():
        raise SystemExit(
            f"Không thấy template '{template_id}' ở {path.relative_to(ROOT).as_posix()}. "
            f"Có sẵn: {', '.join(template_ids())}"
        )
    base = read_json(template_path(BASE_TEMPLATE))
    merged = deep_merge(base, read_json(path))
    errors = template_errors(merged)
    if errors:
        detail = "\n  - ".join(errors)
        raise SystemExit(f"Template '{template_id}' không hợp lệ:\n  - {detail}")
    return merged


def template_schema() -> dict[str, Any]:
    return read_json(SCHEMAS_DIR / "template.schema.json")


def template_errors(data: dict[str, Any]) -> list[str]:
    """Lỗi của một template theo schemas/template.schema.json; rỗng = hợp lệ."""
    import jsonschema

    validator = jsonschema.Draft202012Validator(template_schema())
    return [
        f"{'/'.join(str(part) for part in err.path) or '<root>'}: {err.message}"
        for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    ]
