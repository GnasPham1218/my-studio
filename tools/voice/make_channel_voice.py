"""Sinh và khoá giọng riêng cho một brand/kênh bằng OmniVoice design mode.

Ví dụ:

    # 1. Sinh 4 ứng viên giọng tiếng Anh
    python tools/voice/make_channel_voice.py `
        --brand config/brands/english-learner-1218.json --candidates 4

    # 2. Nghe out/voice-samples/english-learner-1218/voice-*.wav
    #    rồi khoá ứng viên đã chọn
    python tools/voice/make_channel_voice.py `
        --brand config/brands/english-learner-1218.json `
        --lock 2 --name englishlearner

Sau khi khoá, brand chuyển sang `mode: clone` với file trong `assets/voice/`,
nên mọi scene của kênh đó dùng đúng một giọng.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pipeline.voice import get_provider, resolve_spec  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# OmniVoice chỉ nhận các tag cố định cho design mode.
# Xem danh sách trong README của model hoặc lỗi ValueError khi chạy.
DEFAULT_INSTRUCT = "female, american accent, moderate pitch, young adult"
DEFAULT_REF_TEXT = (
    "Hello, welcome to EnglishLearner1218. Today we will learn one small rule "
    "that makes your English sound more natural."
)


def f0_median(audio: np.ndarray, sample_rate: int) -> float:
    import librosa

    values = librosa.yin(
        audio.astype(np.float32), fmin=70, fmax=400, sr=sample_rate, frame_length=1024
    )
    rms = librosa.feature.rms(y=audio, frame_length=1024, hop_length=256)[0]
    count = min(len(values), len(rms))
    voiced = (values[:count] > 70) & (values[:count] < 400) & (rms[:count] > 0.01)
    values = values[:count][voiced]
    return float(np.median(values)) if len(values) else 0.0


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def brand_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        raise SystemExit(f"Không thấy brand: {path}")
    return path


def samples_dir(path: Path) -> Path:
    return ROOT / "out" / "voice-samples" / path.stem


def design_spec(brand: dict, args: argparse.Namespace) -> dict:
    provider = brand["voice"]["provider"]
    spec = dict(resolve_spec(brand["voice"], provider))
    language = args.language or brand.get("channel", {}).get("language") or "en"
    spec.update(
        {
            "mode": "design",
            "instruct": args.instruct or spec.get("instruct") or DEFAULT_INSTRUCT,
            "language": language,
            "speed": 1.0,
            "numStep": int(spec.get("numStep", 32)),
            "tightenPauses": False,
        }
    )
    for key in ("refAudio", "refText"):
        spec.pop(key, None)
    return spec


def make_candidates(args: argparse.Namespace) -> int:
    path = brand_path(args.brand)
    brand = load_json(path)
    provider_name = brand["voice"]["provider"]
    provider = get_provider(provider_name)
    spec = design_spec(brand, args)
    ref_text = args.ref_text or DEFAULT_REF_TEXT

    out = samples_dir(path)
    out.mkdir(parents=True, exist_ok=True)
    (out / "ref-text.txt").write_text(ref_text, encoding="utf-8")
    write_json(
        out / "meta.json",
        {
            "brand": path.stem,
            "provider": provider_name,
            "language": spec["language"],
            "instruct": spec["instruct"],
            "refText": ref_text,
        },
    )

    provider.load()
    print(f"Brand: {path.relative_to(ROOT).as_posix()}")
    print(f"Language: {spec['language']}")
    print(f"Ref text: {ref_text}\n")

    for index in range(1, args.candidates + 1):
        audio = provider.synthesize(ref_text, spec)
        sample = out / f"voice-{index}.wav"
        sf.write(sample, audio, provider.sampleRate)
        seconds = len(audio) / provider.sampleRate
        peak = float(np.abs(audio).max()) if len(audio) else 0.0
        print(
            f"  voice-{index}.wav · {seconds:5.2f}s · "
            f"peak {peak:.2f} · f0 {f0_median(audio, provider.sampleRate):.0f} Hz"
        )

    print("\nNghe các file trên, chọn một ứng viên rồi khoá:")
    print(
        "  python tools/voice/make_channel_voice.py "
        f"--brand {path.relative_to(ROOT).as_posix()} --lock <số> --name <tên>"
    )
    return 0


def lock(args: argparse.Namespace) -> int:
    path = brand_path(args.brand)
    out = samples_dir(path)
    meta_path = out / "meta.json"
    if not meta_path.exists():
        print(f"Chưa có {meta_path}. Chạy --candidates trước.")
        return 1

    source = out / f"voice-{args.lock}.wav"
    if not source.exists():
        print(f"Không thấy {source}.")
        return 1

    meta = load_json(meta_path)
    name = args.name or path.stem
    target = ROOT / "assets" / "voice" / f"omnivoice-{name}.wav"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)

    brand = load_json(path)
    cfg = brand["voice"].setdefault(brand["voice"]["provider"], {})
    cfg.update(
        {
            "mode": "clone",
            "refAudio": target.relative_to(ROOT).as_posix(),
            "refText": meta["refText"],
            "language": meta["language"],
            "speed": 1.0,
            "numStep": int(cfg.get("numStep", 32)),
        }
    )
    cfg.pop("instruct", None)
    write_json(path, brand)

    audio, sr = sf.read(target, dtype="float32")
    print(f"✓ Khoá {source.name} → {target.relative_to(ROOT).as_posix()}")
    print(
        f"  {len(audio) / sr:.2f}s · f0 {f0_median(audio, sr):.0f} Hz · "
        f"mode=clone trong {path.relative_to(ROOT).as_posix()}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sinh/khoá giọng riêng cho một brand bằng OmniVoice."
    )
    parser.add_argument("--brand", required=True, help="Đường dẫn file brand JSON")
    parser.add_argument("--candidates", type=int, default=4, help="Số ứng viên cần sinh")
    parser.add_argument("--lock", type=int, help="Số thứ tự ứng viên muốn khoá (1-based)")
    parser.add_argument("--name", help="Tên file giọng trong assets/voice")
    parser.add_argument("--instruct", help="Mô tả giọng cho design mode")
    parser.add_argument("--ref-text", help="Câu mẫu đọc khi sinh giọng")
    parser.add_argument("--language", help="Mã ngôn ngữ, mặc định lấy từ brand")
    args = parser.parse_args(argv)

    if args.lock:
        return lock(args)
    return make_candidates(args)


if __name__ == "__main__":
    raise SystemExit(main())
