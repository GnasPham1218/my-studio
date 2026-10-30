"""Đo một tập frame: nền, bảng màu, caption, chrome. Kết quả là dict JSON-able.

Hai nơi dùng chung hàm này để so sánh công bằng:
- ``measure_video``: video mẫu của người dùng,
- ``compare``: các frame do chính Remotion render ra từ template đã suy ra.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import numpy as np

from .. import config
from . import audio, colors, frames, media, text

Progress = Callable[[int, int], None]


def aspect_for(width: int, height: int) -> str:
    """Khung hình gần nhất trong config/aspects.json theo tỉ lệ."""
    ratio = width / height
    return min(
        config.aspect_ids(),
        key=lambda a: abs(
            np.log(ratio / (config.aspect(a)["width"] / config.aspect(a)["height"]))
        ),
    )


def _hex(rgb: colors.RGB | None) -> str | None:
    return colors.to_hex(rgb) if rgb is not None else None


def _evenly(items: list[Any], limit: int) -> list[Any]:
    if len(items) <= limit:
        return items
    picks = np.linspace(0, len(items) - 1, limit).round().astype(int)
    return [items[i] for i in sorted(set(picks.tolist()))]


def read_frames_text(
    samples: list[tuple[float, np.ndarray]],
    engine: text.OcrEngine,
    *,
    limit: int,
    progress: Progress | None = None,
) -> list[tuple[text.FrameText, np.ndarray]]:
    chosen = _evenly(samples, limit)
    out: list[tuple[text.FrameText, np.ndarray]] = []
    for index, (t, image) in enumerate(chosen, start=1):
        out.append((text.FrameText(t, engine.read(image)), image))
        if progress:
            progress(index, len(chosen))
    return out


def measure_caption_style(
    read: list[tuple[text.FrameText, np.ndarray]], caption: text.CaptionMeasure
) -> dict[str, Any]:
    """Màu chữ, màu từ đang đọc, viền, thẻ nền, scrim của phụ đề (tổng hợp nhiều frame)."""
    text_colors: list[np.ndarray] = []
    highlights: list[colors.RGB] = []
    outlines: list[colors.RGB] = []
    cards: list[colors.RGB] = []
    scrims = 0
    analyzed = 0
    for frame_text, image in read:
        blocks = text.caption_blocks_in(frame_text, caption)
        if not blocks:
            continue
        reading = text.read_ink(image, blocks[-1])
        if reading is None or reading.text is None:
            continue
        analyzed += 1
        text_colors.append(np.array(reading.text))
        highlights += [
            c for c, share in reading.secondary if share >= 0.04 and colors.saturation(c) > 0.35
        ]
        if reading.outline is not None:
            outlines.append(reading.outline)
        card = text.detect_card(image, blocks[-1])
        if card is not None:
            cards.append(card)
        scrims += int(text.has_scrim(image))

    def share(items: list[Any]) -> float:
        return round(len(items) / analyzed, 3) if analyzed else 0.0

    def median_color(items: list[colors.RGB]) -> colors.RGB | None:
        if not items:
            return None
        return tuple(int(v) for v in np.median(np.array(items), axis=0))  # type: ignore[return-value]

    return {
        "framesAnalyzed": analyzed,
        "textColor": _hex(median_color(text_colors)),  # type: ignore[arg-type]
        "highlightColor": _hex(median_color(highlights)),
        "highlightShare": share(highlights),
        "outlineColor": _hex(median_color(outlines)),
        "outlineShare": share(outlines),
        "cardColor": _hex(median_color(cards)),
        "cardShare": share(cards),
        "scrimShare": round(scrims / analyzed, 3) if analyzed else 0.0,
    }


def ink_palette(
    read: list[tuple[text.FrameText, np.ndarray]], per_frame: int = 12
) -> list[tuple[colors.RGB, float]]:
    """Màu nét chữ trên mọi khối chữ (nguồn tin cậy nhất cho fg và màu nhấn)."""
    ink: list[tuple[colors.RGB, float]] = []
    for frame_text, image in _evenly(read, 20):
        for block in text.group_blocks(frame_text.boxes)[:per_frame]:
            reading = text.read_ink(image, block)
            if reading is None or reading.text is None:
                continue
            area = (block.x1 - block.x0) * (block.y1 - block.y0)
            ink.append((reading.text, area))
            ink += [(c, area * s) for c, s in reading.secondary if colors.saturation(c) > 0.35]
    total = sum(w for _, w in ink) or 1.0
    return [(c, w / total) for c, w in ink]


def measure_images(
    samples: list[tuple[float, np.ndarray]],
    *,
    engine: text.OcrEngine | None,
    max_ocr: int = 80,
    progress: Progress | None = None,
) -> dict[str, Any]:
    """Đo nền, bảng màu và (nếu có OCR) caption/chrome trên các ảnh mẫu."""
    images = [image for _, image in samples]
    height, width, _ = images[0].shape

    background = frames.analyze_background(images)
    vivid = frames.vivid_clusters(images)
    clusters = frames.color_clusters(images)

    result: dict[str, Any] = {
        "background": {
            "kind": background.kind,
            "color": _hex(background.color),
            "angle": background.angle,
            "stops": [_hex(c) for c in background.stops] if background.stops else None,
            "spread": round(background.spread, 1),
            "residual": round(background.residual, 3),
        },
        "caption": None,
        "chrome": {"watermark": None, "sceneIndex": None},
        "ocr": [],
    }

    ink: list[tuple[colors.RGB, float]] = []
    if engine is not None:
        read = read_frames_text(samples, engine, limit=max_ocr, progress=progress)
        frame_texts = [f for f, _ in read]
        result["ocr"] = [f.to_json() for f in frame_texts]
        caption = text.find_caption(frame_texts, width, height)
        result["chrome"] = text.find_chrome(frame_texts, caption)
        if caption is not None:
            result["caption"] = {
                **caption.to_json(),
                **measure_caption_style(read, caption),
            }
        ink = ink_palette(read)

    result["colorSources"] = frames.pack_sources(background.color, ink, vivid, clusters)
    result["palette"] = frames.palette_from_sources(result["colorSources"])
    return result


def measure_video(
    path: Path,
    *,
    sample_every: float = 0.5,
    max_ocr: int = 80,
    max_seconds: float | None = None,
    use_ocr: bool = True,
    progress: Progress | None = None,
) -> tuple[dict[str, Any], list[tuple[float, np.ndarray]]]:
    """Phân tích đầy đủ một video; trả về (analysis, các frame mẫu)."""
    info = media.probe(path)
    scan = media.scan_video(path, sample_every=sample_every, max_seconds=max_seconds)
    duration = scan.frame_times[-1] if scan.frame_times else info.duration_sec
    cuts = frames.detect_cuts(scan.frame_times, scan.diffs)

    engine = text.OcrEngine() if use_ocr and text.ocr_available() else None
    analysis = measure_images(scan.samples, engine=engine, max_ocr=max_ocr, progress=progress)

    track = media.read_audio(path, max_seconds=max_seconds)
    analysis.update(
        {
            "video": {
                "file": path.name,
                "width": info.width,
                "height": info.height,
                "fps": round(info.fps, 2),
                "durationSec": round(duration, 2),
                "aspect": aspect_for(info.width, info.height),
                "hasAudio": info.has_audio,
            },
            "cuts": cuts,
            "pacing": frames.pacing(cuts, duration),
            "audio": audio.analyze_audio(track, 16000),
            "ocrUsed": engine is not None,
        }
    )
    return analysis, scan.samples


def keyframes(
    samples: list[tuple[float, np.ndarray]], cuts: list[float], limit: int = 12
) -> list[tuple[float, np.ndarray]]:
    """Frame đại diện từng cảnh (0,6s sau mỗi điểm cắt) cho contact sheet."""
    starts = [0.0, *cuts]
    picks: list[tuple[float, np.ndarray]] = []
    times = np.array([t for t, _ in samples])
    for start in _evenly(starts, limit):
        index = int(np.argmin(np.abs(times - (start + 0.6))))
        picks.append(samples[index])
    unique = list({round(t, 3): (t, im) for t, im in picks}.values())
    return unique

