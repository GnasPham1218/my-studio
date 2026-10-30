"""Đo hình ảnh thuần từ frame đã thu nhỏ: cắt cảnh, nền, bảng màu."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from . import colors

# Đỉnh nhỏ hơn mức này coi là nhiễu nén, không phải thay đổi hình ảnh.
PEAK_FLOOR = 0.003
# Thay đổi lớn hơn mức này chắc chắn là cắt cảnh, không cần phân nhóm.
SURE_CUT = 0.08


# ---------------------------------------------------------------- cắt cảnh


def local_peaks(times: list[float], diffs: list[float], window_sec: float = 0.25):
    """Các đỉnh cục bộ (thời điểm, độ lớn) của chuỗi diff, bỏ đỉnh dưới PEAK_FLOOR."""
    t = np.asarray(times)
    d = np.asarray(diffs)
    peaks: list[tuple[float, float]] = []
    for i in range(len(d)):
        if d[i] < PEAK_FLOOR:
            continue
        near = (t >= t[i] - window_sec) & (t <= t[i] + window_sec)
        if d[i] >= d[near].max():
            peaks.append((float(t[i]), float(d[i])))
    return peaks


def otsu_threshold(values: np.ndarray) -> tuple[float, float]:
    """Ngưỡng Otsu 1 chiều; trả về (ngưỡng, tỉ lệ tách nhóm = mean_cao / mean_thấp)."""
    ordered = np.sort(values)
    best_score, best_cut = -1.0, ordered[0]
    for i in range(1, len(ordered)):
        low, high = ordered[:i], ordered[i:]
        score = len(low) * len(high) * (high.mean() - low.mean()) ** 2
        if score > best_score:
            best_score, best_cut = score, (ordered[i - 1] + ordered[i]) / 2
    low, high = ordered[ordered <= best_cut], ordered[ordered > best_cut]
    if len(low) == 0 or len(high) == 0:
        return float(best_cut), 1.0
    return float(best_cut), float(high.mean() - low.mean())


def detect_cuts(
    times: list[float],
    diffs: list[float],
    *,
    min_scene_sec: float = 0.6,
) -> list[float]:
    """Thời điểm cắt cảnh.

    Video tối/ít chuyển động có diff rất nhỏ nên ngưỡng cố định không dùng được.
    Ở đây tách các đỉnh thành hai nhóm (cắt cảnh vs thay đổi trong cảnh như đổi
    card phụ đề) bằng Otsu trên log độ cao đỉnh; chỉ tin kết quả khi hai nhóm
    cách nhau đủ xa, ngược lại coi mọi đỉnh đáng kể là cắt.
    """
    peaks = local_peaks(times, diffs)
    if not peaks:
        return []
    heights = np.log(np.array([h for _, h in peaks]))
    threshold = float(np.exp(heights.min())) - 1e-9
    if len(peaks) >= 4:
        cut, gap = otsu_threshold(heights)
        if gap >= np.log(1.6):  # nhóm cao lớn hơn nhóm thấp ≥ 1.6 lần
            threshold = float(np.exp(cut))
    kept = [(t, h) for t, h in peaks if h >= threshold or h >= SURE_CUT]

    # Hai cắt quá gần nhau: giữ cái mạnh hơn.
    result: list[tuple[float, float]] = []
    for t, h in kept:
        if result and t - result[-1][0] < min_scene_sec:
            if h > result[-1][1]:
                result[-1] = (t, h)
            continue
        result.append((t, h))
    return [round(t, 3) for t, _ in result]


def scene_lengths(cuts: list[float], duration: float) -> list[float]:
    edges = [0.0, *cuts, duration]
    return [round(b - a, 3) for a, b in zip(edges, edges[1:]) if b > a]


def pacing(cuts: list[float], duration: float) -> dict[str, float]:
    lengths = scene_lengths(cuts, duration)
    if not lengths or duration <= 0:
        return {}
    return {
        "durationSec": round(duration, 2),
        "avgSceneSec": round(float(np.mean(lengths)), 2),
        "medianSceneSec": round(float(np.median(lengths)), 2),
        "cutsPerMinute": round(len(cuts) / duration * 60, 1),
    }


# ---------------------------------------------------------------- nền


@dataclass
class Background:
    kind: str  # "solid" | "gradient" | "glow"
    color: colors.RGB  # màu nền chính (trung vị các ô)
    angle: float | None = None
    stops: list[colors.RGB] | None = None
    #: Chênh lệch lớn nhất giữa các ô lưới (ΔE); nhỏ = nền phẳng.
    spread: float = 0.0
    #: Phần dư (0..1) khi khớp mặt phẳng tuyến tính vào độ sáng; lớn = có quầng sáng.
    residual: float = 0.0


def grid_colors(image: np.ndarray, grid: int = 3) -> np.ndarray:
    """Trung vị màu của lưới grid x grid, shape (grid, grid, 3)."""
    h, w, _ = image.shape
    out = np.zeros((grid, grid, 3))
    for r in range(grid):
        for c in range(grid):
            cell = image[r * h // grid : (r + 1) * h // grid, c * w // grid : (c + 1) * w // grid]
            out[r, c] = np.median(cell.reshape(-1, 3), axis=0)
    return out


# Phần dư lớn hơn mức này nghĩa là độ sáng không tuyến tính (quầng sáng cục bộ).
GLOW_RESIDUAL = 0.15


def planar_residual(lum: np.ndarray) -> float:
    """Sai lệch lớn nhất giữa độ sáng lưới và mặt phẳng khớp tốt nhất, chia cho biên độ.

    Gradient tuyến tính cho ~0; quầng sáng/vignette không nằm trên mặt phẳng nào.
    """
    rows, cols = lum.shape
    ys, xs = np.mgrid[0:rows, 0:cols]
    design = np.stack([np.ones(lum.size), xs.reshape(-1), ys.reshape(-1)], axis=1)
    values = lum.reshape(-1)
    coeffs, *_ = np.linalg.lstsq(design, values, rcond=None)
    span = float(values.max() - values.min())
    if span < 1e-9:
        return 0.0
    return float(np.abs(values - design @ coeffs).max() / span)


def border_color(images: list[np.ndarray], edge: float = 0.05) -> colors.RGB:
    """Màu phổ biến nhất ở viền khung trên mọi mẫu (ít bị chữ/visual che)."""
    pixels = []
    for image in images:
        h, w, _ = image.shape
        eh, ew = max(2, int(h * edge)), max(2, int(w * edge))
        strips = [image[:eh], image[-eh:], image[:, :ew], image[:, -ew:]]
        pixels.append(np.concatenate([s.reshape(-1, 3)[::7] for s in strips]))
    stack = np.concatenate(pixels)
    bins = (stack // 12).astype(np.int32)
    keys = bins[:, 0] * 10000 + bins[:, 1] * 100 + bins[:, 2]
    values, counts = np.unique(keys, return_counts=True)
    mode = values[np.argmax(counts)]
    members = stack[keys == mode]
    return tuple(int(v) for v in np.median(members, axis=0))  # type: ignore[return-value]


def analyze_background(images: list[np.ndarray]) -> Background:
    """Phân loại nền solid/gradient từ lưới màu trung vị của các mẫu.

    Chữ và visual chiếm ít diện tích nên trung vị theo ô gần như bỏ qua chúng.
    """
    grids = np.stack([grid_colors(image) for image in images])
    grid = np.median(grids, axis=0)  # (3,3,3)
    main = border_color(images)
    cells = grid.reshape(-1, 3)
    spread = max(
        colors.delta_e(a, b) for i, a in enumerate(cells) for b in cells[i + 1 :]
    )
    if spread < 6.0:
        return Background("solid", main, spread=spread)

    # Hướng sáng dần trên màn hình (x sang phải, y xuống dưới).
    lum = np.array([[colors.luminance(c) for c in row] for row in grid])
    residual = planar_residual(lum)
    if residual > GLOW_RESIDUAL:
        return Background("glow", main, spread=spread, residual=residual)
    gx = float(lum[:, 2].mean() - lum[:, 0].mean())
    gy = float(lum[2, :].mean() - lum[0, :].mean())
    if abs(gx) < 1e-3 and abs(gy) < 1e-3:
        return Background("solid", main, spread=spread)

    # CSS: 0deg hướng lên, 90deg hướng phải, 180deg hướng xuống.
    angle = float(np.degrees(np.arctan2(gx, -gy)) % 360)
    direction = np.array([gx, gy]) / np.hypot(gx, gy)
    ys, xs = np.mgrid[0:3, 0:3]
    projection = (xs - 1) * direction[0] + (ys - 1) * direction[1]
    order = np.argsort(projection.reshape(-1))
    low = cells[order[:3]].mean(axis=0)
    high = cells[order[-3:]].mean(axis=0)
    return Background(
        "gradient",
        main,
        angle=round(angle),
        stops=[tuple(int(v) for v in low), tuple(int(v) for v in high)],  # type: ignore[list-item]
        spread=spread,
        residual=residual,
    )


# ---------------------------------------------------------------- bảng màu


def color_clusters(
    images: list[np.ndarray], k: int = 8, max_pixels: int = 60000, seed: int = 0
) -> list[tuple[colors.RGB, float]]:
    """Cụm màu chủ đạo [(RGB, tỉ lệ)] giảm dần theo tỉ lệ."""
    from sklearn.cluster import MiniBatchKMeans

    rng = np.random.default_rng(seed)
    pixels = np.concatenate([img.reshape(-1, 3)[:: max(1, img.shape[0] // 60)] for img in images])
    if len(pixels) > max_pixels:
        pixels = pixels[rng.choice(len(pixels), max_pixels, replace=False)]
    model = MiniBatchKMeans(n_clusters=k, random_state=seed, n_init=3, batch_size=2048)
    labels = model.fit_predict(pixels.astype(np.float32))
    counts = np.bincount(labels, minlength=k) / len(labels)
    order = np.argsort(counts)[::-1]
    return [
        (tuple(int(round(v)) for v in model.cluster_centers_[i]), float(counts[i]))  # type: ignore[misc]
        for i in order
    ]


def vivid_clusters(
    images: list[np.ndarray], k: int = 4, seed: int = 0
) -> list[tuple[colors.RGB, float]]:
    """Cụm màu của riêng các pixel rực (thanh, icon, từ nhấn), tỉ lệ theo tổng pixel.

    k-means toàn khung bỏ sót màu nhấn vì chúng chiếm vài phần nghìn diện tích.
    """
    from sklearn.cluster import MiniBatchKMeans

    stack = np.concatenate([img.reshape(-1, 3) for img in images]).astype(np.float32)
    high, low = stack.max(axis=1), stack.min(axis=1)
    mask = (high >= 0.35 * 255) & ((high - low) / np.maximum(high, 1) >= 0.45)
    vivid = stack[mask]
    if len(vivid) < 200:
        return []
    clusters = min(k, max(1, len(vivid) // 200))
    model = MiniBatchKMeans(n_clusters=clusters, random_state=seed, n_init=3, batch_size=2048)
    labels = model.fit_predict(vivid)
    counts = np.bincount(labels, minlength=clusters) / len(stack)
    order = np.argsort(counts)[::-1]
    return [
        (tuple(int(round(v)) for v in model.cluster_centers_[i]), float(counts[i]))  # type: ignore[misc]
        for i in order
    ]


def pack_sources(
    background: colors.RGB,
    ink: list[tuple[colors.RGB, float]],
    vivid: list[tuple[colors.RGB, float]],
    clusters: list[tuple[colors.RGB, float]],
) -> dict[str, Any]:
    """Nguyên liệu chọn bảng màu, dạng JSON-able để lưu và chọn lại không cần video."""

    def pack(items: list[tuple[colors.RGB, float]]) -> list[list[Any]]:
        return [[colors.to_hex(c), round(float(w), 5)] for c, w in items]

    return {
        "background": colors.to_hex(background),
        "ink": pack(ink),
        "vivid": pack(vivid),
        "clusters": pack(clusters),
    }


def palette_from_sources(sources: dict[str, Any]) -> dict[str, str]:
    """Chọn lại bảng màu (hex) từ `pack_sources`."""

    def unpack(items: list[list[Any]]) -> list[tuple[colors.RGB, float]]:
        return [(colors.from_hex(h), float(w)) for h, w in items]

    palette = pick_palette(
        colors.from_hex(sources["background"]),
        unpack(sources["ink"]) + unpack(sources["vivid"]),
        unpack(sources["clusters"]),
    )
    return {role: colors.to_hex(rgb) for role, rgb in palette.items()}


def pick_palette(
    background: colors.RGB,
    ink: list[tuple[colors.RGB, float]],
    clusters: list[tuple[colors.RGB, float]],
) -> dict[str, Any]:
    """Gán vai trò màu (bg/surface/fg/muted/primary/accent) từ các màu quan sát được.

    `ink`: màu nét chữ từ OCR (nguồn tin cậy nhất cho fg/primary vì chữ chiếm ít
    diện tích nên k-means toàn khung bỏ sót). `clusters`: màu toàn khung, dùng
    cho thanh/biểu tượng và surface.
    """
    bg = background
    pool = [(c, w * 2.0) for c, w in ink] + [(c, w) for c, w in clusters]
    # Gộp các màu gần nhau để một màu không bị tính thành nhiều ứng viên.
    # Mỗi nhóm giữ màu rực nhất: nét chữ khử răng cưa luôn nhạt hơn màu thật.
    merged: list[list[Any]] = []
    for color, weight in pool:
        for entry in merged:
            if colors.delta_e(entry[0], color) < 9:
                entry[1] += weight
                if colors.saturation(color) > colors.saturation(entry[0]):
                    entry[0] = color
                break
        else:
            merged.append([color, weight])

    def contrast(c: colors.RGB) -> float:
        return colors.delta_e(c, bg)

    candidates = [(tuple(c), w) for c, w in merged if contrast(c) > 12]
    fg = max(
        (c for c, w in candidates if colors.saturation(c) < 0.35 and w > 0),
        key=lambda c: contrast(c) * (1 + 0.3 * np.log1p(dict(candidates)[c])),
        default=colors.mix(bg, (255, 255, 255) if colors.luminance(bg) < 0.5 else (0, 0, 0), 0.92),
    )
    vivid = sorted(
        (c for c, w in candidates if colors.saturation(c) >= 0.35),
        key=lambda c: -dict(candidates)[c],
    )
    primary = vivid[0] if vivid else colors.mix(bg, fg, 0.7)
    accent = next(
        (c for c in vivid[1:] if colors.hue_distance(c, primary) >= 35),
        colors.mix(primary, fg, 0.35),
    )
    near_bg = [
        c for c, _ in merged if 3 < contrast(c) < 30 and colors.saturation(c) < 0.35
    ]
    surface = near_bg[0] if near_bg else colors.mix(bg, fg, 0.06)
    return {
        "bg": bg,
        "surface": tuple(surface),
        "fg": tuple(fg),
        "muted": colors.mix(fg, bg, 0.45),
        "primary": tuple(primary),
        "accent": tuple(accent),
    }
