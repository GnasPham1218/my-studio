"""Provider OmniVoice: zero-shot đa ngôn ngữ, chạy PyTorch trên GPU, xuất 24 kHz.

Ba chế độ (xem omnivoice.models.omnivoice.OmniVoice.generate):
    auto   — model tự chọn giọng
    design — mô tả giọng bằng ``instruct`` (chỉ đáng tin với tiếng Trung/Anh)
    clone  — nhân bản giọng từ ``refAudio`` + ``refText`` (khuyến nghị cho tiếng Việt)

Mặc định bắt buộc chạy CUDA: CPU chậm gấp ~50 lần nên chỉ dùng khi debug bằng
biến môi trường ``OMNIVOICE_DEVICE=cpu``.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

from .base import normalize_spec

ROOT = Path(__file__).resolve().parents[2]

DEFAULT_MODEL = "k2-fsa/OmniVoice"
DEFAULT_LANGUAGE = "vi"
MODES = ("auto", "design", "clone")

# OmniVoice hay chèn khoảng lặng ~1s giữa các câu, làm video dài hơn hẳn.
# Cắt bớt nhưng vẫn giữ nhịp nghỉ tự nhiên.
MAX_PAUSE_SEC = 0.5
KEEP_PAUSE_SEC = 0.35

# Ưu tiên bản local: tránh việc hf tự tải lại 2.3 GB mỗi lần nạp.
LOCAL_MODEL = ROOT / "models" / "omnivoice"


def _tighten_pauses(audio: Any, sample_rate: int) -> Any:
    """Rút ngắn khoảng lặng dài bất thường mà model chèn vào giữa câu."""
    import numpy as np

    frame = max(1, int(0.02 * sample_rate))
    count = len(audio) // frame
    if count < 2:
        return audio

    frames = np.abs(audio[: count * frame]).reshape(count, frame)
    rms = np.sqrt(np.mean(frames**2, axis=1))
    threshold = max(0.008, float(rms.max()) * 0.02)
    quiet = rms < threshold

    keep = int(KEEP_PAUSE_SEC / 0.02)
    keep_frames = int(MAX_PAUSE_SEC / 0.02)
    pieces: list[Any] = []
    cursor = 0
    index = 0
    while index < count:
        if not quiet[index]:
            index += 1
            continue
        start = index
        while index < count and quiet[index]:
            index += 1
        end = index
        if end - start <= keep_frames:
            continue
        # Giữ lại đầu và cuối khoảng lặng, bỏ phần giữa.
        cut_from = start + keep // 2
        cut_to = end - keep // 2
        pieces.append(audio[cursor * frame : cut_from * frame])
        cursor = cut_to

    if not pieces:
        return audio
    pieces.append(audio[cursor * frame :])
    return np.concatenate(pieces)


def _pick_device(torch: Any) -> tuple[str, Any]:
    """Chọn thiết bị chạy: mặc định CUDA, chỉ CPU khi được chỉ định rõ."""
    requested = os.environ.get("OMNIVOICE_DEVICE", "auto").strip().lower()
    if requested in ("", "auto", "gpu", "cuda"):
        if not torch.cuda.is_available():
            raise SystemExit(
                "OmniVoice cần GPU CUDA nhưng torch không thấy CUDA.\n"
                "Cài bản CUDA rồi chạy lại:\n"
                "  uv pip install --python .venv\\Scripts\\python.exe "
                "--torch-backend=auto torch torchaudio\n"
                "Nếu chỉ muốn thử bằng CPU (rất chậm): đặt OMNIVOICE_DEVICE=cpu"
            )
        device = "cuda"
        dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        return device, dtype
    return requested, torch.float32


class OmniVoiceProvider:
    name = "omnivoice"
    sampleRate = 24_000

    def __init__(self) -> None:
        self._model: Any = None
        self._prompt: Any = None
        self._prompt_key: str | None = None
        self._torch: Any = None
        self._device: str = "cuda"

    def load(self) -> None:
        if self._model is not None:
            return

        # Có sẵn weights local thì cấm mọi request tới Hugging Face:
        # tránh cả chuyện chậm và giới hạn tải của bản free.
        local_ready = (LOCAL_MODEL / "config.json").exists()
        if local_ready:
            os.environ.setdefault("HF_HUB_OFFLINE", "1")

        try:
            import torch
            from omnivoice import OmniVoice
        except ImportError as exc:  # pragma: no cover - phụ thuộc môi trường
            raise SystemExit(
                "Chưa cài OmniVoice. Chạy:\n"
                "  uv pip install --torch-backend=auto torch torchaudio\n"
                "  uv pip install omnivoice"
            ) from exc

        device, dtype = _pick_device(torch)
        model_id = str(LOCAL_MODEL) if local_ready else DEFAULT_MODEL

        if device.startswith("cuda"):
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
            torch.cuda.empty_cache()

        self._model = OmniVoice.from_pretrained(
            model_id, device_map=device, dtype=dtype
        )
        self.sampleRate = int(getattr(self._model, "sampling_rate", None) or 24_000)
        self._torch = torch
        self._device = device

        if device.startswith("cuda"):
            used = torch.cuda.memory_allocated() / 1024**3
            total = torch.cuda.get_device_properties(0).total_memory / 1024**3
            print(
                f"  · OmniVoice trên {torch.cuda.get_device_name(0)} · "
                f"{str(dtype).replace('torch.', '')} · {used:.1f}/{total:.1f} GB VRAM",
                flush=True,
            )

    def list_voices(self) -> list[str]:
        return [
            "auto   - model tự chọn giọng",
            "design - cần instruct; chỉ nên dùng cho tiếng Trung/Anh",
            "clone  - cần refAudio (3-10s) + refText; khuyến nghị cho tiếng Việt",
        ]

    def _resolve(self, raw: str) -> Path:
        path = Path(raw)
        return path if path.is_absolute() else ROOT / path

    def _clone_prompt(self, ref_audio: Path, ref_text: str | None) -> Any:
        key = hashlib.sha256(ref_audio.read_bytes()).hexdigest() + "|" + (ref_text or "")
        if self._prompt is None or self._prompt_key != key:
            self._prompt = self._model.create_voice_clone_prompt(
                ref_audio=str(ref_audio), ref_text=ref_text
            )
            self._prompt_key = key
        return self._prompt

    def synthesize(self, text: str, spec: dict[str, Any]) -> np.ndarray:
        self.load()
        spec = normalize_spec(spec)
        mode = str(spec.get("mode") or "auto")
        if mode not in MODES:
            raise SystemExit(f"Chế độ OmniVoice không hợp lệ: {mode!r}. Chọn: {', '.join(MODES)}")

        kwargs: dict[str, Any] = {
            "text": text,
            "language": spec.get("language", DEFAULT_LANGUAGE),
            "num_step": int(spec.get("numStep", 32)),
            "speed": float(spec.get("speed", 1.0)),
        }

        if mode == "clone":
            raw = spec.get("refAudio")
            if not raw:
                raise SystemExit("OmniVoice mode=clone cần 'refAudio' trong brand.json")
            ref_audio = self._resolve(str(raw))
            if not ref_audio.exists():
                raise SystemExit(f"Không thấy file giọng mẫu: {ref_audio}")
            kwargs["voice_clone_prompt"] = self._clone_prompt(ref_audio, spec.get("refText"))
        elif mode == "design":
            instruct = spec.get("instruct")
            if not instruct:
                raise SystemExit("OmniVoice mode=design cần 'instruct' trong brand.json")
            kwargs["instruct"] = instruct

        torch = self._torch
        with torch.inference_mode():
            audios = self._model.generate(**kwargs)
        if not audios:
            raise RuntimeError("OmniVoice không trả về audio")
        audio = np.asarray(audios[0], dtype=np.float32).reshape(-1)
        if spec.get("tightenPauses", True):
            audio = _tighten_pauses(audio, self.sampleRate)
        if self._device.startswith("cuda"):
            torch.cuda.empty_cache()
        return audio

    def fingerprint(self, spec: dict[str, Any]) -> str:
        spec = normalize_spec(spec)
        extra = ""
        raw = spec.get("refAudio")
        if spec.get("mode") == "clone" and raw:
            path = self._resolve(str(raw))
            if path.exists():
                extra = "|ref:" + hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        return "omnivoice:" + json.dumps(spec, sort_keys=True, ensure_ascii=False) + extra
