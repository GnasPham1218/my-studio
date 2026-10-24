"""Provider VieNeu-TTS: preset có sẵn, ONNX CPU, xuất 48 kHz."""

from __future__ import annotations

import json
from typing import Any

import numpy as np

from .base import normalize_spec

DEFAULT_VOICE = "Mai Anh"


class VieneuProvider:
    name = "vieneu"
    sampleRate = 48_000

    def __init__(self) -> None:
        self._model: Any = None

    def load(self) -> None:
        if self._model is not None:
            return
        from vieneu import Vieneu

        # backend="onnx": không cần torch, chạy CPU.
        self._model = Vieneu(backend="onnx")

    def list_voices(self) -> list[str]:
        self.load()
        raw = self._model.list_preset_voices()
        voices: list[str] = []
        for item in raw:
            if isinstance(item, (tuple, list)) and len(item) >= 2:
                voices.append(str(item[1]))
            elif isinstance(item, dict):
                voices.append(str(item.get("id") or item.get("voice") or item.get("name")))
            else:
                voices.append(str(item))
        return voices

    def synthesize(self, text: str, spec: dict[str, Any]) -> np.ndarray:
        self.load()
        voice = str(normalize_spec(spec).get("voiceId") or DEFAULT_VOICE)
        audio = self._model.infer(text, voice=voice)
        return np.asarray(audio, dtype=np.float32)

    def fingerprint(self, spec: dict[str, Any]) -> str:
        spec = normalize_spec(spec)
        spec.setdefault("voiceId", DEFAULT_VOICE)
        return "vieneu:" + json.dumps(spec, sort_keys=True, ensure_ascii=False)
