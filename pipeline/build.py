from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import paths, review
from .align import build_cards
from .sfx import ensure_sfx, load_catalog

ROOT = Path(__file__).resolve().parent.parent
FORMATS_PATH = ROOT / "config" / "formats.json"

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.build",
        description="Ghép script + audio + timing thành props.json cho Remotion.",
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--format", choices=["short", "long"])
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
    review.require_approved(pid, fmt, bypass=args.unapproved)
    paths.snapshot(pid)

    script = load_json(paths.script_path(pid, fmt))
    manifest = load_json(paths.manifest_path(pid, fmt))
    aligned = load_json(paths.words_path(pid, fmt))
    brand = paths.load_brand(pid)
    formats = load_json(FORMATS_PATH)
    cfg = formats["formats"][fmt]

    entries = manifest["scenes"]
    timing = {scene["id"]: scene for scene in aligned["scenes"]}
    sfx_items = load_catalog()

    scenes: list[dict[str, Any]] = []
    cards: list[dict[str, Any]] = []
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
                "visual": scene.get("visual"),
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

        for card in build_cards(words, cfg["caption"]["maxWordsPerCard"]):
            cards.append(
                {
                    "start": card[0]["start"],
                    "end": card[-1]["end"],
                    "words": card,
                }
            )

        cursor += duration

    total = round(cursor, 3)
    if abs(aligned["totalSec"] - total) > 0.05:
        raise SystemExit(
            f"Tổng thời lượng lệch: align={aligned['totalSec']}s, build={total}s"
        )

    out = paths.out_dir(pid)
    audio_dir = paths.audio_dir(pid, fmt)
    sfx_dir = audio_dir / "sfx"
    ensure_sfx(sfx_dir)

    props = {
        "format": fmt,
        "styleId": paths.style_id(pid),
        "audioDir": audio_dir.relative_to(out).as_posix(),
        "sfxDir": sfx_dir.relative_to(out).as_posix(),
        "sfxCatalog": {
            sfx_id: {
                "file": item["file"],
                "durationSec": float(item.get("durationSec", 1.0)),
                "defaultVolume": float(item.get("defaultVolume", 0.4)),
            }
            for sfx_id, item in sfx_items.items()
        },
        "width": cfg["width"],
        "height": cfg["height"],
        "fps": cfg["fps"],
        "totalSec": total,
        "projectId": script["meta"]["projectId"],
        "title": script["meta"]["title"],
        "brand": brand,
        "safeArea": cfg["safeArea"],
        "scenes": scenes,
        "captions": cards,
    }

    target = paths.props_path(pid, fmt)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        f"✓ {paths.rel(target)} · {len(scenes)} scene · "
        f"{total:.1f}s · {len(cards)} caption card"
    )
    print(
        f"  render: python -m pipeline.render --project-id {args.project_id} "
        f"--format {fmt}"
    )
    paths.update_status(
        pid,
        title=script["meta"]["title"],
        format=fmt,
        props={fmt: {"scenes": len(scenes), "totalSec": total}},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
