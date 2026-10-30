from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import captions, config, paths, review, visuals
from .sfx import ensure_sfx, load_catalog

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def themed_brand(brand: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    """Brand sau khi template ghi đè màu/font (template từ video mẫu có palette riêng)."""
    return config.deep_merge(
        brand,
        {"colors": template.get("colors") or {}, "fonts": template.get("fonts") or {}},
    )


def build_scenes(
    script: dict[str, Any],
    entries: dict[str, Any],
    timing: dict[str, Any],
    sfx_items: dict[str, Any],
    rules: captions.CardRules,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], float]:
    """Ghép script + audio + timing thành scene và card phụ đề."""
    scenes: list[dict[str, Any]] = []
    cards: list[captions.Card] = []
    cursor = 0.0

    for scene in script["scenes"]:
        sid = scene["id"]
        entry = entries.get(sid)
        timed = timing.get(sid)
        if not entry or not timed:
            raise SystemExit(f"Thiếu audio hoặc timing cho {sid}")

        duration = float(entry["durationSec"])
        if abs(timed["start"] - cursor) > 0.02:
            raise SystemExit(
                f"Lệch timeline ở {sid}: align={timed['start']:.3f}s, build={cursor:.3f}s"
            )

        words = timed["words"]
        sfx_id = scene.get("sfx")
        if sfx_id == "none":
            sfx_id = None
        if sfx_id and sfx_id not in sfx_items:
            raise SystemExit(
                f"SFX '{sfx_id}' ở {sid} không có trong config/sfx.json"
            )
        sfx_at = scene.get("sfxAtSec")
        if sfx_at is not None and not 0 <= float(sfx_at) <= duration:
            raise SystemExit(
                f"sfxAtSec của {sid} phải nằm trong 0..{duration:.2f}s"
            )
        scenes.append(
            {
                "id": sid,
                "type": scene["type"],
                "startSec": round(cursor, 3),
                "durationSec": round(duration, 3),
                "narration": scene["narration"],
                "onScreenText": scene.get("onScreenText"),
                "kicker": scene.get("kicker"),
                "bullets": scene.get("bullets"),
                "emphasis": scene.get("emphasis"),
                "visual": visuals.resolve(scene.get("visual")),
                "sfx": sfx_id,
                "sfxAtSec": sfx_at,
                "sfxVolume": scene.get("sfxVolume"),
                "chart": scene.get("chart"),
                "stat": scene.get("stat"),
                "timeline": scene.get("timeline"),
                "compare": scene.get("compare"),
                "words": words,
            }
        )
        cards.extend(captions.build_cards(words, rules))
        cursor += duration

    return scenes, cards, cursor


@dataclass
class Composed:
    """Kết quả ghép một (project, format, aspect, template); chưa ghi file nào."""

    props: dict[str, Any]
    cards: list[captions.Card]
    layout: dict[str, Any]
    brand: dict[str, Any]
    template: dict[str, Any]


def compose(
    pid: str,
    fmt: str,
    aspect_id: str,
    template_id: str | None = None,
) -> Composed:
    """Ghép props cho Remotion. Thuần: không ghi file, không kiểm duyệt.

    `template_id` ghi đè `style` của project (dùng để thử template khác lên một
    project có sẵn mà không sửa project.json).
    """
    script = load_json(paths.script_path(pid, fmt))
    manifest = load_json(paths.manifest_path(pid, fmt))
    aligned = load_json(paths.words_path(pid, fmt))
    layout = config.layout(aspect_id)
    template = config.template(template_id or paths.style_id(pid))
    brand = themed_brand(paths.load_brand(pid), template)
    rules = captions.CardRules.from_layout(layout)

    sfx_items = load_catalog()
    scenes, cards, total = build_scenes(
        script,
        manifest["scenes"],
        {scene["id"]: scene for scene in aligned["scenes"]},
        sfx_items,
        rules,
    )
    total = round(total, 3)
    if abs(aligned["totalSec"] - total) > 0.05:
        raise SystemExit(
            f"Tổng thời lượng lệch: align={aligned['totalSec']}s, build={total}s"
        )

    out = paths.out_dir(pid)
    audio_dir = paths.audio_dir(pid, fmt)
    props = {
        "format": fmt,
        "aspect": aspect_id,
        "audioDir": audio_dir.relative_to(out).as_posix(),
        "sfxDir": (audio_dir / "sfx").relative_to(out).as_posix(),
        "sfxCatalog": {
            sfx_id: {
                "file": item["file"],
                "durationSec": float(item.get("durationSec", 1.0)),
                "defaultVolume": float(item.get("defaultVolume", 0.4)),
            }
            for sfx_id, item in sfx_items.items()
        },
        "width": layout["width"],
        "height": layout["height"],
        "fps": layout["fps"],
        "totalSec": total,
        "projectId": script["meta"]["projectId"],
        "title": script["meta"]["title"],
        "brand": brand,
        "template": template,
        "layout": layout,
        "scenes": scenes,
        "captions": captions.cards_to_json(cards),
    }
    return Composed(props, cards, layout, brand, template)


def write_caption_files(pid: str, fmt: str, aspect_id: str, built: Composed) -> Path:
    """SRT/ASS cho người dùng muốn đưa lên nền tảng; chia card theo khung hình."""
    cards_dir = paths.cards_dir(pid, fmt, aspect_id)
    cards_dir.mkdir(parents=True, exist_ok=True)
    uppercase = bool(built.template["caption"]["uppercase"])
    captions.write_srt(cards_dir / "captions.srt", built.cards, uppercase)
    captions.write_ass(
        cards_dir / "captions.ass",
        built.cards,
        layout=built.layout,
        colors=built.brand["colors"],
        font=built.brand["fonts"]["body"],
        uppercase=uppercase,
    )
    return cards_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.build",
        description="Ghép script + audio + timing thành props.json cho Remotion.",
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--format", choices=config.format_ids())
    parser.add_argument(
        "--aspect",
        choices=config.aspect_ids(),
        help="Khung hình (mặc định: project.json hoặc mặc định của format)",
    )
    parser.add_argument(
        "--template",
        help="Ghi đè template của project (id trong config/templates), không sửa project.json",
    )
    parser.add_argument(
        "--unapproved",
        action="store_true",
        help="Chạy nháp khi script chưa được duyệt (pipeline.review)",
    )
    args = parser.parse_args(argv)

    pid = args.project_id
    fmt = args.format or paths.detect_format(pid)
    if not fmt:
        raise SystemExit(
            f"Không tìm thấy script trong {paths.rel(paths.script_dir(pid))}"
        )
    aspect_id = paths.resolve_aspect(pid, fmt, args.aspect)
    review.require_approved(pid, fmt, bypass=args.unapproved)
    paths.snapshot(pid)

    built = compose(pid, fmt, aspect_id, args.template)
    ensure_sfx(paths.audio_dir(pid, fmt) / "sfx")
    write_caption_files(pid, fmt, aspect_id, built)

    props = built.props
    target = paths.props_path(pid, fmt, aspect_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        f"✓ {paths.rel(target)} · {fmt}/{aspect_id} · template {built.template['id']} · "
        f"{len(props['scenes'])} scene · {props['totalSec']:.1f}s · "
        f"{len(built.cards)} caption card"
    )
    print(
        f"  render: python -m pipeline.render --project-id {pid} "
        f"--format {fmt} --aspect {aspect_id}"
        + (f" --template {args.template}" if args.template else "")
    )
    paths.update_status(
        pid,
        title=props["title"],
        format=fmt,
        props={
            f"{fmt}-{aspect_id}": {
                "scenes": len(props["scenes"]),
                "totalSec": props["totalSec"],
                "template": built.template["id"],
            }
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
