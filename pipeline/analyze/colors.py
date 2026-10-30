"""Phép tính màu thuần (numpy), dùng chung cho các bước phân tích."""

from __future__ import annotations

import colorsys

import numpy as np

RGB = tuple[int, int, int]


def to_hex(rgb: RGB | np.ndarray) -> str:
    r, g, b = (int(round(float(v))) for v in rgb)
    return f"#{max(0, min(255, r)):02X}{max(0, min(255, g)):02X}{max(0, min(255, b)):02X}"


def from_hex(value: str) -> RGB:
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def luminance(rgb: RGB | np.ndarray) -> float:
    """Độ sáng tương đối 0..1 (WCAG)."""

    def channel(v: float) -> float:
        v = v / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(float(v)) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def saturation(rgb: RGB | np.ndarray) -> float:
    r, g, b = (float(v) / 255.0 for v in rgb)
    _, s, v = colorsys.rgb_to_hsv(r, g, b)
    return s * v  # trọng số theo độ sáng: màu rất tối không được coi là "rực"


def hue_degrees(rgb: RGB | np.ndarray) -> float:
    r, g, b = (float(v) / 255.0 for v in rgb)
    return colorsys.rgb_to_hsv(r, g, b)[0] * 360.0


def hue_distance(a: RGB, b: RGB) -> float:
    d = abs(hue_degrees(a) - hue_degrees(b))
    return min(d, 360.0 - d)


def mix(a: RGB, b: RGB, amount: float) -> RGB:
    """Trộn a→b; amount=0 là a, 1 là b."""
    return tuple(  # type: ignore[return-value]
        int(round(x + (y - x) * amount)) for x, y in zip(a, b)
    )


def to_lab(rgb: RGB | np.ndarray) -> np.ndarray:
    """sRGB → CIE Lab (D65)."""
    arr = np.asarray(rgb, dtype=np.float64).reshape(-1, 3) / 255.0
    arr = np.where(arr <= 0.04045, arr / 12.92, ((arr + 0.055) / 1.055) ** 2.4)
    matrix = np.array(
        [[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]
    )
    xyz = arr @ matrix.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16.0 / 116.0)
    lab = np.stack(
        [116.0 * f[:, 1] - 16.0, 500.0 * (f[:, 0] - f[:, 1]), 200.0 * (f[:, 1] - f[:, 2])],
        axis=1,
    )
    return lab


def delta_e(a: RGB | np.ndarray, b: RGB | np.ndarray) -> float:
    """Khoảng cách màu ΔE76: <2 không phân biệt được, <10 rất gần, >30 khác hẳn."""
    return float(np.linalg.norm(to_lab(a)[0] - to_lab(b)[0]))
