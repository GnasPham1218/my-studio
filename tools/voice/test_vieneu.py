"""Test VieNeu-TTS v3 Turbo (local, CPU/ONNX) — không cần GPU, không cần API key.

Cài đặt:
    py -3.14 -m venv .venv
    .\\.venv\\Scripts\\Activate.ps1
    pip install -U pip
    pip install vieneu

Chạy:
    python tools/voice/test_vieneu.py                 # liệt kê giọng + đọc 1 câu mẫu
    python tools/voice/test_vieneu.py --all           # đọc cùng 1 câu bằng TẤT CẢ giọng (để chọn giọng kênh)
    python tools/voice/test_vieneu.py --voice "Phạm Tuyên" --text "Xin chào, đây là kênh của tôi."
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

OUT_DIR = Path(__file__).parent / "out"

# Câu mẫu có code-switching Việt–Anh + cảm xúc, đúng kiểu nội dung video công nghệ.
SAMPLE = (
    "[cười] Chào mừng các bạn đến với kênh! Hôm nay mình sẽ nói về một chủ đề "
    "cực kỳ thú vị: làm sao để tự động hoá toàn bộ quy trình sản xuất video, "
    "từ khâu ý tưởng cho đến lúc xuất bản MP4."
)


def get_voices(vieneu) -> list[tuple[str, str]]:
    """Chuẩn hoá list_preset_voices() về [(label, voice_id), ...]."""
    raw = vieneu.list_preset_voices()
    out: list[tuple[str, str]] = []
    for item in raw:
        if isinstance(item, (tuple, list)) and len(item) >= 2:
            out.append((str(item[0]), str(item[1])))
        elif isinstance(item, dict):
            out.append((str(item.get("label") or item.get("name")), str(item.get("id") or item.get("voice"))))
        else:
            out.append((str(item), str(item)))
    return out


def synth(vieneu, text: str, voice: str, out_path: Path) -> float:
    t0 = time.perf_counter()
    audio = vieneu.infer(text, voice=voice)
    elapsed = time.perf_counter() - t0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    vieneu.save(audio, str(out_path))

    duration = len(audio) / 48_000  # v3 Turbo xuất 48 kHz
    rtf = elapsed / duration if duration else 0.0
    print(f"  → {out_path.name}  {duration:5.1f}s audio | {elapsed:5.1f}s xử lý | RTF {rtf:.3f}")
    return rtf


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", default=None, help="Tên giọng preset (vd: 'Phạm Tuyên')")
    parser.add_argument("--text", default=SAMPLE)
    parser.add_argument("--all", action="store_true", help="Đọc câu mẫu bằng mọi giọng preset")
    parser.add_argument("--backend", default=None, choices=["onnx", "torch"], help="Mặc định tự phát hiện")
    args = parser.parse_args()

    from vieneu import Vieneu

    print("Đang nạp model (lần đầu sẽ tải ~0.5 GB từ Hugging Face)...")
    t0 = time.perf_counter()
    vieneu = Vieneu(backend=args.backend) if args.backend else Vieneu()
    print(f"Nạp xong sau {time.perf_counter() - t0:.1f}s\n")

    voices = get_voices(vieneu)
    print(f"{len(voices)} giọng preset:")
    for label, vid in voices:
        print(f"  - {label}  ({vid})")
    print()

    if args.all:
        for label, vid in voices:
            safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)
            try:
                synth(vieneu, args.text, vid, OUT_DIR / f"{safe}.wav")
            except Exception as exc:  # một giọng lỗi không nên chặn cả vòng lặp
                print(f"  ! {label}: {exc}")
        return

    voice = args.voice or voices[0][1]
    synth(vieneu, args.text, voice, OUT_DIR / "sample.wav")
    print(f"\nXong. File nằm trong: {OUT_DIR}")


if __name__ == "__main__":
    main()
