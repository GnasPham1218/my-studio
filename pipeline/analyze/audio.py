"""Đặc điểm âm thanh của video mẫu (chỉ để tham khảo, không điều khiển render)."""

from __future__ import annotations

from typing import Any

import numpy as np

FRAME_SEC = 0.05
# Sàn nhiễu của tiếng đọc thu sạch thường dưới mức này; cao hơn nghĩa là có nhạc nền/ồn đều.
MUSIC_FLOOR_DBFS = -45.0
SILENCE_DBFS = -60.0


def frame_rms_db(samples: np.ndarray, sample_rate: int) -> np.ndarray:
    size = max(1, int(FRAME_SEC * sample_rate))
    count = len(samples) // size
    if count == 0:
        return np.array([])
    frames = samples[: count * size].reshape(count, size)
    rms = np.sqrt(np.mean(frames**2, axis=1))
    return 20 * np.log10(np.maximum(rms, 1e-9))


def analyze_audio(samples: np.ndarray | None, sample_rate: int) -> dict[str, Any]:
    """Độ ồn, sàn nhiễu, có nhạc nền không, nhịp (nếu có nhạc)."""
    if samples is None or len(samples) < sample_rate:
        return {"loudnessDbfs": None, "floorDbfs": None, "hasMusicBed": None, "tempoBpm": None}

    levels = frame_rms_db(samples, sample_rate)
    speaking = levels[levels > SILENCE_DBFS]
    if len(speaking) == 0:
        return {"loudnessDbfs": None, "floorDbfs": None, "hasMusicBed": False, "tempoBpm": None}

    loud = float(np.percentile(speaking, 90))
    floor = float(np.percentile(levels, 10))
    has_music = floor > MUSIC_FLOOR_DBFS
    return {
        "loudnessDbfs": round(loud, 1),
        "floorDbfs": round(floor, 1),
        # Suy đoán từ sàn nhiễu: nhạc nền và tiếng ồn đều cho cùng dấu hiệu.
        "hasMusicBed": bool(has_music),
        "tempoBpm": _tempo(samples, sample_rate) if has_music else None,
    }


def _tempo(samples: np.ndarray, sample_rate: int) -> float | None:
    try:
        import librosa

        tempo, _ = librosa.beat.beat_track(y=samples, sr=sample_rate)
        value = float(np.atleast_1d(tempo)[0])
        return round(value, 1) if value > 0 else None
    except Exception:  # librosa tuỳ chọn, lỗi ở đây không đáng làm hỏng phân tích
        return None
