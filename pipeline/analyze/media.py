"""Đọc video/audio bằng PyAV (đã có sẵn cùng faster-whisper, không cần ffmpeg ngoài)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import av
import numpy as np


@dataclass
class VideoInfo:
    path: str
    width: int
    height: int
    fps: float
    duration_sec: float
    has_audio: bool
    codec: str

    @property
    def ratio(self) -> float:
        return self.width / self.height


def probe(path: Path) -> VideoInfo:
    with av.open(str(path)) as container:
        video = container.streams.video[0]
        fps = float(video.average_rate or video.guessed_rate or 30)
        duration = (
            float(container.duration) / av.time_base
            if container.duration
            else float(video.duration * video.time_base)
            if video.duration
            else 0.0
        )
        return VideoInfo(
            path=str(path),
            width=video.codec_context.width,
            height=video.codec_context.height,
            fps=fps,
            duration_sec=duration,
            has_audio=len(container.streams.audio) > 0,
            codec=video.codec_context.name,
        )


@dataclass
class Scan:
    """Kết quả một lượt đọc video: mọi frame đều được đo, chỉ một số được giữ lại."""

    frame_times: list[float] = field(default_factory=list)
    #: Độ khác nhau giữa frame i và frame i-1 (0..1), frame đầu = 0.
    diffs: list[float] = field(default_factory=list)
    #: (thời điểm, ảnh RGB uint8) tại các điểm lấy mẫu.
    samples: list[tuple[float, np.ndarray]] = field(default_factory=list)


def scan_video(
    path: Path,
    *,
    sample_every: float = 0.5,
    sample_width: int = 540,
    diff_width: int = 64,
    max_seconds: float | None = None,
) -> Scan:
    """Một lượt giải mã: đo độ khác biệt từng frame + giữ ảnh mẫu đã thu nhỏ."""
    scan = Scan()
    previous: np.ndarray | None = None
    next_sample = 0.0

    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        stream.thread_type = "AUTO"
        height_ratio = stream.codec_context.height / stream.codec_context.width
        diff_size = (diff_width, max(8, int(round(diff_width * height_ratio))))
        sample_size = (sample_width, int(round(sample_width * height_ratio)))

        for frame in container.decode(stream):
            if frame.time is None:
                continue
            t = float(frame.time)
            if max_seconds is not None and t > max_seconds:
                break

            small = frame.to_ndarray(
                width=diff_size[0], height=diff_size[1], format="gray"
            ).astype(np.float32)
            diff = 0.0 if previous is None else float(np.abs(small - previous).mean() / 255.0)
            previous = small
            scan.frame_times.append(t)
            scan.diffs.append(diff)

            if t >= next_sample:
                image = frame.to_ndarray(
                    width=sample_size[0], height=sample_size[1], format="rgb24"
                )
                scan.samples.append((t, image))
                next_sample = t + sample_every
    return scan


def read_audio(path: Path, *, sample_rate: int = 16000, max_seconds: float | None = None):
    """Mono float32 ở `sample_rate`; None nếu video không có audio."""
    with av.open(str(path)) as container:
        if not container.streams.audio:
            return None
        resampler = av.AudioResampler(format="fltp", layout="mono", rate=sample_rate)
        chunks: list[np.ndarray] = []
        total = 0
        limit = None if max_seconds is None else int(max_seconds * sample_rate)
        for frame in container.decode(audio=0):
            for out in resampler.resample(frame):
                data = out.to_ndarray().reshape(-1)
                chunks.append(data)
                total += len(data)
            if limit is not None and total >= limit:
                break
        if not chunks:
            return None
        audio = np.concatenate(chunks).astype(np.float32)
        return audio[:limit] if limit is not None else audio
