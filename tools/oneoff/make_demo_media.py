"""Tạo audio im lặng + timing cho demo visual (không dùng TTS).

Dùng khi chỉ muốn kiểm tra style/visual trước khi có giọng đọc thật:

    python tools/oneoff/make_demo_media.py --project-id english-whiteboard-demo

Script này ghi vào out/<id>/02-audio/<fmt>/ và out/<id>/03-captions/<fmt>/.
Sau đó chạy pipeline.build như bình thường.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--format", default="short")
    parser.add_argument("--sample-rate", type=int, default=48000)
    args = parser.parse_args()

    pid = args.project_id
    fmt = args.format
    script_path = ROOT / "projects" / pid / "scripts" / f"{fmt}.json"
    script = json.loads(script_path.read_text(encoding="utf-8"))

    audio_dir = ROOT / "out" / pid / "02-audio" / fmt
    captions_dir = ROOT / "out" / pid / "03-captions" / fmt
    audio_dir.mkdir(parents=True, exist_ok=True)
    captions_dir.mkdir(parents=True, exist_ok=True)

    manifest_scenes: dict[str, dict] = {}
    words_scenes: list[dict] = []
    cursor = 0.0

    for scene in script["scenes"]:
        sid = scene["id"]
        duration = float(scene["durationTargetSec"])
        samples = max(1, int(round(duration * args.sample_rate)))
        wav = audio_dir / f"{sid}.wav"
        sf.write(wav, np.zeros(samples, dtype=np.float32), args.sample_rate)
        rel = wav.relative_to(ROOT).as_posix()
        manifest_scenes[sid] = {
            "file": rel,
            "hash": "demo-silent",
            "durationSec": round(duration, 3),
            "chars": len(scene["narration"]),
            "provider": "demo-silent",
            "spec": {},
        }

        raw = scene["narration"].split()
        count = max(1, len(raw))
        # Chừa 0.12s đầu/cuối để caption không dính mép scene.
        span = max(0.1, duration - 0.24)
        step = span / count
        words = []
        for index, word in enumerate(raw):
            start = cursor + 0.12 + index * step
            end = start + max(0.05, step * 0.86)
            words.append(
                {
                    "w": word,
                    "start": round(start, 3),
                    "end": round(min(end, cursor + duration - 0.02), 3),
                }
            )
        words_scenes.append(
            {
                "id": sid,
                "type": scene["type"],
                "start": round(cursor, 3),
                "end": round(cursor + duration, 3),
                "words": words,
            }
        )
        cursor += duration

    total = round(cursor, 3)
    voice = {"provider": "demo-silent", "spec": {}}
    manifest = {
        "format": fmt,
        "provider": "demo-silent",
        "voice": voice,
        "sampleRate": args.sample_rate,
        "scenes": manifest_scenes,
        "totalSec": total,
    }
    (audio_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    words = {
        "format": fmt,
        "fps": 30,
        "totalSec": total,
        "voice": voice,
        "hashes": {sid: item["hash"] for sid, item in manifest_scenes.items()},
        "scenes": words_scenes,
    }
    (captions_dir / "words.json").write_text(
        json.dumps(words, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"demo media: {len(manifest_scenes)} scene · {total:.1f}s · silent")
    print(f"  {audio_dir.relative_to(ROOT)}")
    print(f"  {captions_dir.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
