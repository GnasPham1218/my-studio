"""Tạo và khoá một giọng cố định cho OmniVoice.

Lý do: `mode=auto` để model tự bốc giọng **mỗi lần generate**, nên các scene
trong cùng video có thể đổi cả giọng nam lẫn nữ. Cách xử lý là lấy một mẫu
giọng do chính model sinh ra, rồi dùng `mode=clone` với mẫu đó cho toàn bộ
video (không nhân bản giọng người ngoài).

Quy trình:

    # 1. Sinh vài ứng viên (cùng một câu mẫu), xem thời lượng + cao độ
    python tools/voice/make_voice_ref.py --candidates 4

    # 2. Nghe tools/voice/out/samples/voice-1.wav … chọn một file ưng ý rồi khoá
    python tools/voice/make_voice_ref.py --lock tools/voice/out/samples/voice-2.wav --name nam

    # 3. Kiểm tra giọng đã ổn định chưa (f0 giữa các câu không nhảy)
    python tools/voice/make_voice_ref.py --test

Sau khi khoá, chạy lại pipeline cho từng format.
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

BRAND_PATH = ROOT / "config" / "brand.json"
SAMPLES = ROOT / "tts" / "out" / "samples"
VOICE_DIR = ROOT / "assets" / "voice"

# Câu mẫu: đủ dài (7–8 s), không có số/viết tắt để model đọc ổn định.
REF_TEXT = (
    "Xin chào, đây là kênh DiveCode1218. "
    "Hôm nay chúng ta cùng tìm hiểu vì sao các mô hình AI nhỏ đang quay trở lại."
)

TEST_TEXTS = (
    "Mô hình nhỏ chạy ngay trên điện thoại, không cần kết nối internet.",
    "Nhưng rồi cuộc đua mô hình lớn nổ ra, và câu chuyện về AI nhỏ bị bỏ quên.",
    "Chi phí chạy trên đám mây tăng nhanh, buộc các công ty phải tính lại.",
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


def load_brand() -> dict:
    return json.loads(BRAND_PATH.read_text(encoding="utf-8"))


def voice_spec(brand: dict) -> dict:
    return dict(resolve_spec(brand["voice"], brand["voice"]["provider"]))


def candidates(count: int) -> None:
    brand = load_brand()
    spec = voice_spec(brand)
    spec["mode"] = "auto"
    # Giữ nguyên khoảng lặng gốc: bản thu càng sát text thì clone càng chính xác.
    spec["tightenPauses"] = False
    for key in ("refAudio", "refText", "instruct"):
        spec.pop(key, None)

    SAMPLES.mkdir(parents=True, exist_ok=True)
    (SAMPLES / "ref-text.txt").write_text(REF_TEXT, encoding="utf-8")

    provider = get_provider(brand["voice"]["provider"])
    provider.load()

    print(f"Câu mẫu: {REF_TEXT}\n")
    for index in range(1, count + 1):
        audio = provider.synthesize(REF_TEXT, spec)
        path = SAMPLES / f"voice-{index}.wav"
        sf.write(path, audio, provider.sampleRate)
        seconds = len(audio) / provider.sampleRate
        print(
            f"  voice-{index}.wav · {seconds:5.2f}s · "
            f"{len(REF_TEXT.split()) / seconds:4.2f} từ/giây · "
            f"f0 {f0_median(audio, provider.sampleRate):.0f} Hz"
        )

    print("\nNghe rồi chọn, ví dụ:")
    print("  python tools/voice/make_voice_ref.py --lock tools/voice/out/samples/voice-1.wav --name nam")
    print("  (f0 ~110–140 Hz là giọng nam, ~190–260 Hz là giọng nữ)")


def lock(source: str, name: str) -> int:
    src = Path(source)
    if not src.is_absolute():
        src = ROOT / src
    if not src.exists():
        print(f"Không thấy file: {src}")
        return 1

    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    target = VOICE_DIR / f"omnivoice-{name}.wav"
    shutil.copyfile(src, target)

    brand = load_brand()
    config = brand["voice"].setdefault("omnivoice", {})
    config.update(
        {
            "mode": "clone",
            "refAudio": target.relative_to(ROOT).as_posix(),
            "refText": REF_TEXT,
            "language": config.get("language", "vi"),
        }
    )
    # Bỏ khoá không còn dùng để brand.json không mập mờ.
    for key in ("instruct",):
        config.pop(key, None)
    BRAND_PATH.write_text(
        json.dumps(brand, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    audio, sr = sf.read(target, dtype="float32")
    print(f"✓ Khoá giọng từ {src.name} → {target.relative_to(ROOT).as_posix()}")
    print(
        f"  {len(audio) / sr:.2f}s · f0 {f0_median(audio, sr):.0f} Hz · "
        f"mode=clone trong config/brand.json"
    )
    print("\nChạy lại video:")
    print("  .\\.venv\\Scripts\\python.exe -u -m pipeline.make --project-id <id> --format short")
    return 0


def test() -> int:
    brand = load_brand()
    spec = voice_spec(brand)
    if spec.get("mode") != "clone" or not spec.get("refAudio"):
        print("brand.json chưa ở mode=clone — chạy --lock trước.")
        return 1

    provider = get_provider(brand["voice"]["provider"])
    provider.load()
    values = []
    for text in TEST_TEXTS:
        audio = provider.synthesize(text, spec)
        hz = f0_median(audio, provider.sampleRate)
        values.append(hz)
        print(
            f"  {len(audio) / provider.sampleRate:5.2f}s · "
            f"{len(text.split()) / (len(audio) / provider.sampleRate):4.2f} từ/giây · "
            f"f0 {hz:.0f} Hz"
        )
    spread = max(values) - min(values)
    print(f"\nf0 chênh lệch giữa các câu: {spread:.0f} Hz", end=" — ")
    print("ổn định" if spread <= 25 else "vẫn còn đổi giọng, thử ứng viên khác")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Tạo/khoá giọng cố định cho OmniVoice.")
    parser.add_argument("--candidates", type=int, metavar="N", help="Sinh N mẫu giọng")
    parser.add_argument("--lock", metavar="FILE", help="Khoá giọng từ file wav")
    parser.add_argument("--name", default="chinh", help="Tên file giọng khi khoá")
    parser.add_argument("--test", action="store_true", help="Kiểm tra giọng đang khoá")
    args = parser.parse_args(argv)

    if args.candidates:
        candidates(args.candidates)
        return 0
    if args.lock:
        return lock(args.lock, args.name)
    if args.test:
        return test()
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
