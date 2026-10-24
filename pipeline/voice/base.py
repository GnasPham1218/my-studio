"""Giao diện chung cho mọi engine TTS.

Mỗi provider chỉ cần trả về waveform float32 mono và sample rate của nó;
pipeline/tts.py lo phần resample, chuẩn hoá âm lượng và padding, nên thêm
engine mới không phải sửa chỗ khác.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class TTSProvider(Protocol):
    """Hợp đồng tối thiểu mà pipeline/tts.py cần."""

    name: str
    sampleRate: int

    def load(self) -> None:
        """Nạp model. Gọi một lần trước khi synth."""

    def list_voices(self) -> list[str]:
        """Danh sách giọng/preset để in ra cho người dùng chọn."""

    def synthesize(self, text: str, spec: dict[str, Any]) -> np.ndarray:
        """Trả về waveform float32 mono ở self.sampleRate."""

    def fingerprint(self, spec: dict[str, Any]) -> str:
        """Chuỗi ổn định đại diện cho cấu hình giọng, dùng làm cache key."""


def normalize_spec(spec: dict[str, Any] | None) -> dict[str, Any]:
    """Bỏ các giá trị rỗng để hai cấu hình tương đương cho cùng fingerprint."""
    return {k: v for k, v in (spec or {}).items() if v not in (None, "", [], {})}
