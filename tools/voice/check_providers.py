"""Kiểm tra nhanh một provider TTS mà không đụng tới project nào.

Ví dụ:
    python tools/voice/check_providers.py --provider vieneu --voice "Mai Anh" \
        --text "Xin chào, đây là giọng đọc của kênh." --out tools/voice/out/check.wav
    python tools/voice/check_providers.py --provider omnivoice --mode auto \
        --text "Xin chào, đây là OmniVoice." --out tools/voice/out/check-omni.wav
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pipeline.voice import PROVIDERS, get_provider, resolve_spec  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=PROVIDERS, default="vieneu")
    parser.add_argument("--text", default="Xin chào, đây là bản thử giọng của kênh DiveCode1218.")
    parser.add_argument("--out", default="tools/voice/out/check.wav")
    parser.add_argument("--voice", help="[vieneu] tên preset")
    parser.add_argument("--mode", choices=["auto", "design", "clone"])
    parser.add_argument("--ref-audio")
    parser.add_argument("--ref-text")
    parser.add_argument("--instruct")
    parser.add_argument("--list", action="store_true", help="Chỉ in danh sách giọng")
    args = parser.parse_args()

    brand = json.loads((ROOT / "config" / "brand.json").read_text(encoding="utf-8"))
    spec = resolve_spec(brand["voice"], args.provider)
    overrides = {
        "voiceId": args.voice,
        "mode": args.mode,
        "refAudio": args.ref_audio,
        "refText": args.ref_text,
        "instruct": args.instruct,
    }
    spec.update({key: value for key, value in overrides.items() if value})

    provider = get_provider(args.provider)

    if args.list:
        for voice in provider.list_voices():
            print(f"  - {voice}")
        return 0

    started = time.perf_counter()
    provider.load()
    print(f"Nạp {args.provider} sau {time.perf_counter() - started:.1f}s")

    started = time.perf_counter()
    audio = np.asarray(provider.synthesize(args.text, spec), dtype=np.float32)
    elapsed = time.perf_counter() - started
    duration = len(audio) / provider.sampleRate

    target = ROOT / args.out
    target.parent.mkdir(parents=True, exist_ok=True)
    sf.write(target, audio, provider.sampleRate, subtype="PCM_16")

    print(f"spec      : {spec}")
    print(f"audio     : {duration:.2f}s @ {provider.sampleRate} Hz")
    print(f"xử lý      : {elapsed:.2f}s · RTF {elapsed / duration:.2f}")
    print(f"file      : {target.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
