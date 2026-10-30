"""Đọc chữ trên frame (OCR) và suy ra caption, watermark, số scene.

Chia hai tầng để test được mà không cần OCR:

- tầng I/O: ``OcrEngine.read`` biến ảnh thành ``TextBox`` (toạ độ chuẩn hoá 0..1),
- tầng logic thuần: ``group_blocks``, ``find_caption``, ``find_chrome``, ... chỉ
  làm việc trên ``TextBox`` và ``numpy``.

Toạ độ luôn chuẩn hoá theo bề rộng/chiều cao khung, nên kết quả không phụ thuộc
độ phân giải của ảnh mẫu.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from . import colors

# Hệ số line-height của caption trong Remotion (components/Captions.tsx).
LINE_HEIGHT = 1.22
# OCR đo hộp chữ gồm cả dấu/đuôi chữ nên cao hơn cỡ chữ ~15%.
SINGLE_LINE_RATIO = 1.15
# Chữ ở giữa khung (caption căn giữa) chấp nhận lệch tối đa từng này.
CENTER_TOLERANCE = 0.14
# Màu sát hai bên chữ lệch từng này ΔE so với màu xa hơn thì coi là có thẻ nền.
# Nền mượt lệch dưới 2 ở khoảng cách này nên 6 vẫn an toàn trước dương tính giả.
CARD_MIN_DELTA_E = 6.0
SCENE_INDEX = re.compile(r"^\d{1,3}\s*[/|]\s*\d{1,3}$")


@dataclass
class TextBox:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    conf: float = 1.0

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def h(self) -> float:
        return self.y1 - self.y0

    @property
    def w(self) -> float:
        return self.x1 - self.x0

    def to_json(self) -> dict[str, Any]:
        return {
            "box": [round(self.x0, 4), round(self.y0, 4), round(self.x1, 4), round(self.y1, 4)],
            "text": self.text,
            "conf": round(self.conf, 2),
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "TextBox":
        x0, y0, x1, y1 = data["box"]
        return cls(x0, y0, x1, y1, data["text"], data.get("conf", 1.0))


@dataclass
class FrameText:
    t: float
    boxes: list[TextBox] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {"t": round(self.t, 3), "boxes": [b.to_json() for b in self.boxes]}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "FrameText":
        return cls(data["t"], [TextBox.from_json(b) for b in data["boxes"]])


# ---------------------------------------------------------------- OCR (I/O)


def ocr_available() -> bool:
    try:
        import rapidocr_onnxruntime  # noqa: F401
    except ImportError:
        return False
    return True


class OcrEngine:
    """Bọc RapidOCR (ONNX, chạy CPU, không cần mạng). Nạp lười."""

    def __init__(self, min_conf: float = 0.5):
        from rapidocr_onnxruntime import RapidOCR

        self._engine = RapidOCR()
        self.min_conf = min_conf

    def read(self, image_rgb: np.ndarray) -> list[TextBox]:
        height, width, _ = image_rgb.shape
        result, _ = self._engine(image_rgb[:, :, ::-1])  # RapidOCR nhận BGR
        boxes: list[TextBox] = []
        for points, text, conf in result or []:
            if float(conf) < self.min_conf or not str(text).strip():
                continue
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            boxes.append(
                TextBox(
                    max(0.0, min(xs) / width),
                    max(0.0, min(ys) / height),
                    min(1.0, max(xs) / width),
                    min(1.0, max(ys) / height),
                    str(text).strip(),
                    float(conf),
                )
            )
        return boxes


# ---------------------------------------------------------------- khối chữ


@dataclass
class Block:
    """Nhóm các dòng chữ liền nhau (một caption nhiều dòng, một headline...)."""

    lines: list[TextBox]

    @property
    def x0(self) -> float:
        return min(b.x0 for b in self.lines)

    @property
    def x1(self) -> float:
        return max(b.x1 for b in self.lines)

    @property
    def y0(self) -> float:
        return min(b.y0 for b in self.lines)

    @property
    def y1(self) -> float:
        return max(b.y1 for b in self.lines)

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def text(self) -> str:
        return " ".join(b.text for b in self.lines)

    @property
    def pitch(self) -> float | None:
        """Khoảng cách trung bình giữa tâm hai dòng liên tiếp; None nếu 1 dòng."""
        if len(self.lines) < 2:
            return None
        centers = [b.cy for b in self.lines]
        return float(np.mean(np.diff(centers)))


def group_blocks(boxes: list[TextBox]) -> list[Block]:
    """Gom các dòng gần nhau theo chiều dọc và cùng trục ngang thành khối."""
    blocks: list[list[TextBox]] = []
    for box in sorted(boxes, key=lambda b: b.y0):
        if blocks:
            last = blocks[-1]
            height = float(np.median([b.h for b in last + [box]]))
            gap = box.y0 - max(b.y1 for b in last)
            same_axis = abs(box.cx - float(np.mean([b.cx for b in last]))) <= 0.12
            if gap <= 0.8 * height and same_axis:
                last.append(box)
                continue
        blocks.append([box])
    return [Block(lines) for lines in blocks]


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


# ---------------------------------------------------------------- caption


@dataclass
class CaptionMeasure:
    bottom: float  # y đáy khối chữ, chuẩn hoá theo chiều cao (0 = đỉnh)
    font_px_rel: float  # cỡ chữ / cạnh ngắn của khung
    max_width: float  # bề rộng khối chữ lớn nhất / bề rộng khung
    uppercase: bool
    lines_per_card: float
    presence: float  # tỉ lệ frame có caption
    change: float  # tỉ lệ nội dung khác nhau giữa các frame
    frames: list[float]  # thời điểm các frame có caption
    confidence: float

    def to_json(self) -> dict[str, Any]:
        return {
            "bottom": round(self.bottom, 4),
            "bottomRel": round(1 - self.bottom, 4),
            "fontSizeRel": round(self.font_px_rel, 4),
            "maxWidthRel": round(self.max_width, 4),
            "uppercase": self.uppercase,
            "linesPerCard": round(self.lines_per_card, 2),
            "presence": round(self.presence, 3),
            "change": round(self.change, 3),
            "confidence": round(self.confidence, 2),
        }


def centered_blocks(frame: FrameText) -> list[Block]:
    return [b for b in group_blocks(frame.boxes) if abs(b.cx - 0.5) <= CENTER_TOLERANCE]


def find_caption(frames: list[FrameText], width: int, height: int) -> CaptionMeasure | None:
    """Tìm dải chữ là phụ đề: căn giữa, hiện gần như suốt video, nội dung đổi liên tục.

    Headline đổi theo scene nên thay đổi nhiều nhưng vị trí dọc không cố định;
    chữ trong visual cố định theo scene nhưng không xuất hiện ở mọi frame.
    Phụ đề là dải duy nhất vừa chiếm nhiều frame vừa đổi nội dung.
    """
    if not frames:
        return None

    bins: dict[int, list[tuple[float, Block]]] = defaultdict(list)
    for frame in frames:
        for block in centered_blocks(frame):
            bins[round(block.y1 / 0.025)].append((frame.t, block))

    best_key, best_score = None, 0.0
    for key, items in bins.items():
        present = len({round(t, 2) for t, _ in items}) / len(frames)
        change = len({_normalize(b.text) for _, b in items}) / max(1, len(items))
        score = present * (0.3 + 0.7 * min(1.0, change * 2))
        if score > best_score:
            best_key, best_score = key, score
    if best_key is None:
        return None

    # Gộp các bin kề nhau: khối nhiều dòng có đáy dao động ±1 bin.
    items = [
        item
        for key in (best_key - 1, best_key, best_key + 1)
        for item in bins.get(key, [])
    ]
    blocks = [b for _, b in items]
    present = len({round(t, 2) for t, _ in items}) / len(frames)
    if present < 0.12:
        return None

    short_side = min(width, height)
    pitches = [b.pitch for b in blocks if b.pitch]
    if pitches:
        font_px = float(np.median(pitches)) * height / LINE_HEIGHT
    else:
        line_h = float(np.median([b.lines[0].h for b in blocks]))
        font_px = line_h * height / SINGLE_LINE_RATIO

    letters = [c for b in blocks for c in b.text if c.isalpha()]
    upper = sum(1 for c in letters if c.isupper()) / len(letters) if letters else 0.0
    widths = np.array([b.x1 - b.x0 for b in blocks])
    change = len({_normalize(b.text) for b in blocks}) / max(1, len(blocks))
    confidence = min(1.0, present * 2) * min(1.0, 0.4 + change)
    return CaptionMeasure(
        bottom=float(np.median([b.y1 for b in blocks])),
        font_px_rel=font_px / short_side,
        max_width=min(1.0, float(np.percentile(widths, 95)) * 1.04),
        uppercase=upper >= 0.8,
        lines_per_card=float(np.mean([len(b.lines) for b in blocks])),
        presence=present,
        change=change,
        frames=sorted({round(t, 3) for t, _ in items}),
        confidence=confidence,
    )


def caption_blocks_in(frame: FrameText, caption: CaptionMeasure) -> list[Block]:
    """Khối caption của một frame (đáy gần đáy trung vị đã đo)."""
    return [
        b for b in centered_blocks(frame) if abs(b.y1 - caption.bottom) <= 0.04
    ]


# ---------------------------------------------------------------- chrome


def find_chrome(frames: list[FrameText], caption: CaptionMeasure | None) -> dict[str, Any]:
    """Chữ cố định suốt video: watermark kênh và số scene `03 / 13`."""
    cells: dict[tuple[int, int], list[TextBox]] = defaultdict(list)
    for frame in frames:
        seen: set[tuple[int, int]] = set()
        for box in frame.boxes:
            if caption and abs(box.y1 - caption.bottom) <= 0.05:
                continue
            key = (round(box.cx / 0.04), round(box.cy / 0.04))
            if key in seen:
                continue
            seen.add(key)
            cells[key].append(box)

    result: dict[str, Any] = {"watermark": None, "sceneIndex": None}
    for (kx, ky), boxes in cells.items():
        presence = len(boxes) / len(frames)
        if presence < 0.6:
            continue
        sample = Counter(_normalize(b.text) for b in boxes).most_common(1)[0][0]
        center = (float(np.mean([b.cx for b in boxes])), float(np.mean([b.cy for b in boxes])))
        if SCENE_INDEX.match(boxes[0].text.replace(" ", "")) or all(
            SCENE_INDEX.match(b.text.replace(" ", "")) for b in boxes[: max(3, len(boxes) // 3)]
        ):
            result["sceneIndex"] = {"x": round(center[0], 3), "y": round(center[1], 3)}
        elif sample and result["watermark"] is None:
            letters = [c for b in boxes for c in b.text if c.isalpha()]
            upper = sum(c.isupper() for c in letters) / len(letters) if letters else 0.0
            result["watermark"] = {
                "x": round(center[0], 3),
                "y": round(center[1], 3),
                "text": boxes[0].text,
                "uppercase": upper >= 0.8,
                "presence": round(presence, 2),
            }
    return result


# ---------------------------------------------------------------- màu chữ


def _crop(image: np.ndarray, x0: float, y0: float, x1: float, y1: float) -> np.ndarray:
    h, w, _ = image.shape
    ix0, ix1 = int(max(0, x0) * w), int(min(1, x1) * w)
    iy0, iy1 = int(max(0, y0) * h), int(min(1, y1) * h)
    return image[iy0:iy1, ix0:ix1]


def _distance_to_segment(pixels: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Khoảng cách RGB từ mỗi pixel tới đoạn thẳng a-b (nét chữ khử răng cưa nằm trên đoạn này)."""
    ab = b - a
    denom = float(ab @ ab) or 1.0
    t = np.clip(((pixels - a) @ ab) / denom, 0, 1)
    return np.linalg.norm(pixels - (a + t[:, None] * ab), axis=1)


@dataclass
class InkReading:
    background: colors.RGB
    text: colors.RGB | None
    secondary: list[tuple[colors.RGB, float]]  # (màu, tỉ lệ trên pixel chữ)
    outline: colors.RGB | None
    outline_share: float


def read_ink(image: np.ndarray, block: Block, pad: float = 0.004) -> InkReading | None:
    """Màu nền cục bộ, màu chữ chính, màu nhấn và viền quanh một khối chữ."""
    from sklearn.cluster import MiniBatchKMeans

    crop = _crop(image, block.x0 - pad, block.y0 - pad, block.x1 + pad, block.y1 + pad)
    if crop.size == 0 or min(crop.shape[:2]) < 6:
        return None
    pixels = crop.reshape(-1, 3).astype(np.float32)
    ring = np.concatenate([crop[0], crop[-1], crop[:, 0], crop[:, -1]]).astype(np.float32)
    bg = np.median(ring, axis=0)

    far = np.linalg.norm(pixels - bg, axis=1) > 60
    ink = pixels[far]
    if len(ink) < 30:
        return None
    clusters = min(3, max(1, len(ink) // 60))
    model = MiniBatchKMeans(n_clusters=clusters, random_state=0, n_init=3, batch_size=1024)
    labels = model.fit_predict(ink)
    shares = np.bincount(labels, minlength=clusters) / len(labels)
    centers = model.cluster_centers_
    order = np.argsort(shares)[::-1]
    text = tuple(int(round(v)) for v in centers[order[0]])
    secondary = [
        (tuple(int(round(v)) for v in centers[i]), float(shares[i])) for i in order[1:]
    ]

    # Viền: pixel xa cả nền lẫn đoạn nền→chữ (khử răng cưa nằm trên đoạn này).
    # Viền thật là một màu đặc; bóng đổ (text-shadow) mờ dần nên độ lệch màu lớn.
    text_vec = np.array(text, dtype=np.float32)
    off_line = _distance_to_segment(pixels, bg, text_vec) > 45
    outline_pixels = pixels[off_line & (np.linalg.norm(pixels - bg, axis=1) > 40)]
    outline = None
    share = len(outline_pixels) / max(1, len(ink))
    if (
        len(outline_pixels) > 40
        and share > 0.06
        and float(outline_pixels.std(axis=0).max()) < 20
    ):
        outline = tuple(int(round(v)) for v in np.median(outline_pixels, axis=0))
    return InkReading(
        background=tuple(int(round(v)) for v in bg),  # type: ignore[arg-type]
        text=text,  # type: ignore[arg-type]
        secondary=secondary,  # type: ignore[arg-type]
        outline=outline,  # type: ignore[arg-type]
        outline_share=share,
    )


def detect_card(image: np.ndarray, block: Block) -> colors.RGB | None:
    """Có thẻ nền sau chữ không? So màu sát hai bên khối chữ với màu xa hơn.

    Chỉ so theo chiều ngang (cùng hàng) để scrim chuyển dần theo chiều dọc
    không bị nhầm thành thẻ.
    """
    line_h = max(0.01, float(np.median([b.h for b in block.lines])))
    results = []
    for side in (-1, 1):
        edge = block.x0 if side < 0 else block.x1
        near = sorted([edge + side * 0.05 * line_h, edge + side * 0.4 * line_h])
        far = sorted([edge + side * 1.1 * line_h, edge + side * 1.9 * line_h])
        if min(near + far) < 0 or max(near + far) > 1:
            continue
        a = _crop(image, near[0], block.y0, near[1], block.y1).reshape(-1, 3)
        b = _crop(image, far[0], block.y0, far[1], block.y1).reshape(-1, 3)
        if len(a) < 10 or len(b) < 10:
            continue
        results.append((np.median(a, axis=0), np.median(b, axis=0), a.std(axis=0).max()))
    if not results:
        return None
    if all(colors.delta_e(a, b) > CARD_MIN_DELTA_E and std < 12 for a, b, std in results):
        return tuple(int(round(v)) for v in np.mean([a for a, _, _ in results], axis=0))  # type: ignore[return-value]
    return None


def has_scrim(image: np.ndarray) -> bool:
    """Đáy khung có tối/đổi màu dần so với giữa khung không (cột sát mép trái)."""
    h, w, _ = image.shape
    column = image[:, : max(2, int(0.06 * w))]
    mid = np.median(column[int(0.45 * h) : int(0.55 * h)].reshape(-1, 3), axis=0)
    bottom = np.median(column[int(0.93 * h) : int(0.99 * h)].reshape(-1, 3), axis=0)
    return colors.delta_e(mid, bottom) >= 3.0
