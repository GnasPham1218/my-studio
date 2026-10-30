"""Props xem trước khi chưa đọc giọng: thời lượng ước tính, không audio.

Giao diện duyệt (pipeline.ui) dùng để chiếu animation của kịch bản, kể cả bản
đang sửa dở chưa lưu. Timeline ước tính theo ``durationTargetSec`` hoặc tốc độ
nói trong config/formats.json; từ trải đều trong cảnh để phụ đề vẫn chạy.
"""

from __future__ import annotations

from typing import Any

from . import build, captions, config, paths, validate
from .sfx import load_catalog

MIN_SCENE_SEC = 1.2
PAD_SEC = 0.3  # khoảng thở cuối cảnh, gần với khoảng lặng TTS thật


def estimate_seconds(scene: dict[str, Any]) -> float:
    return round(max(MIN_SCENE_SEC, validate._scene_seconds(scene) + PAD_SEC), 2)


def spread_words(text: str, start: float, duration: float) -> list[dict[str, Any]]:
    """Trải đều từng từ trong cảnh, chừa đầu/cuối như giọng đọc thật."""
    tokens = text.split()
    if not tokens:
        return []
    lead = min(0.15, duration * 0.1)
    span = max(0.1, duration - lead - PAD_SEC)
    step = span / len(tokens)
    return [
        {
            "w": token,
            "start": round(start + lead + index * step, 3),
            "end": round(start + lead + (index + 1) * step, 3),
        }
        for index, token in enumerate(tokens)
    ]


def draft_props(
    pid: str,
    fmt: str,
    aspect_id: str | None = None,
    *,
    script: dict[str, Any] | None = None,
    template_id: str | None = None,
) -> dict[str, Any]:
    """Props Remotion cho bản xem trước; ``script`` là bản đang sửa (None = file đã lưu)."""
    if script is None:
        script = build.load_json(paths.script_path(pid, fmt))
    aspect_id = paths.resolve_aspect(pid, fmt, aspect_id)
    layout = config.layout(aspect_id)
    template = config.template(template_id or paths.style_id(pid))
    brand = build.themed_brand(paths.load_brand(pid), template)
    rules = captions.CardRules.from_layout(layout)
    sfx_items = load_catalog()

    entries: dict[str, Any] = {}
    timing: dict[str, Any] = {}
    cursor = 0.0
    for scene in script["scenes"]:
        duration = estimate_seconds(scene)
        entries[scene["id"]] = {"durationSec": duration}
        timing[scene["id"]] = {
            "start": round(cursor, 3),
            "words": spread_words(validate._scene_text(scene), cursor, duration),
        }
        cursor += duration

    scenes, cards, total = build.build_scenes(script, entries, timing, sfx_items, rules)
    props = build.assemble_props(
        pid,
        fmt,
        aspect_id,
        script=script,
        layout=layout,
        template=template,
        brand=brand,
        sfx_items=sfx_items,
        scenes=scenes,
        cards=cards,
        total=round(total, 3),
    )
    props["silent"] = True
    return props
