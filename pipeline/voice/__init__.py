"""Chọn engine TTS theo tên, import lười để không kéo torch khi dùng VieNeu."""

from __future__ import annotations

import importlib
from typing import Any

from .base import TTSProvider, normalize_spec

# provider -> (module, class)
_REGISTRY: dict[str, tuple[str, str]] = {
    "vieneu": ("pipeline.voice.vieneu_provider", "VieneuProvider"),
    "omnivoice": ("pipeline.voice.omnivoice_provider", "OmniVoiceProvider"),
}

PROVIDERS = tuple(_REGISTRY)


def get_provider(name: str) -> TTSProvider:
    try:
        module_name, class_name = _REGISTRY[name]
    except KeyError:
        raise SystemExit(
            f"Provider TTS không hỗ trợ: {name!r}. Chọn một trong: {', '.join(PROVIDERS)}"
        ) from None
    module = importlib.import_module(module_name)
    return getattr(module, class_name)()


def resolve_spec(voice_cfg: dict[str, Any], provider: str) -> dict[str, Any]:
    """Lấy khối cấu hình riêng của provider trong brand.json.

    brand.json:
        "voice": {
          "provider": "vieneu",
          "vieneu":   {"voiceId": "Mai Anh"},
          "omnivoice": {"mode": "clone", "refAudio": "assets/voice/ref.wav", ...}
        }
    """
    return normalize_spec(voice_cfg.get(provider) or {})


def voice_config(brand: dict[str, Any], language: str | None = None) -> dict[str, Any]:
    """Chọn khối voice theo ngôn ngữ của scene/segment.

    `voice` vẫn là mặc định để tương thích brand cũ. Brand đa ngữ có thể thêm
    `voices` theo mã ngôn ngữ; nếu không có ngôn ngữ tương ứng thì fallback về
    `voice` mặc định.
    """
    voices = brand.get("voices") or {}
    candidate = voices.get(language) if language else None
    if candidate is None:
        default_language = (brand.get("channel") or {}).get("language")
        candidate = voices.get(default_language) if default_language else None
    if candidate is None:
        candidate = brand.get("voice")
    if not candidate:
        raise SystemExit(
            "Brand thiếu 'voice' hoặc 'voices'. Không biết dùng giọng nào."
        )
    return candidate


__all__ = [
    "PROVIDERS",
    "TTSProvider",
    "get_provider",
    "resolve_spec",
    "voice_config",
]
