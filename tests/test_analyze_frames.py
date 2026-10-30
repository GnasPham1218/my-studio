from __future__ import annotations

import numpy as np
import pytest

from pipeline.analyze import colors, frames


def timeline(seconds=20.0, fps=30):
    return [round(i / fps, 4) for i in range(int(seconds * fps))]


def with_events(times, events):
    """Diff nền ~0 cộng các sự kiện {thời điểm: độ lớn}."""
    diffs = [1e-6] * len(times)
    for when, size in events.items():
        diffs[min(range(len(times)), key=lambda i: abs(times[i] - when))] = size
    return diffs


def test_dark_video_cuts_are_separated_from_in_scene_motion():
    """Số liệu thật từ video tối: cắt cảnh 0,017–0,042; đổi card phụ đề 0,0075–0,011."""
    times = timeline(30)
    cuts = {4.0: 0.042, 9.0: 0.0247, 14.0: 0.0185, 19.0: 0.0301, 24.0: 0.0168}
    captions = {2.0: 0.0075, 6.5: 0.0113, 11.5: 0.0095, 16.5: 0.0099, 21.5: 0.0102, 27.0: 0.0078}
    found = frames.detect_cuts(times, with_events(times, {**cuts, **captions}))
    assert len(found) == 5
    assert all(any(abs(f - c) < 0.1 for f in found) for c in cuts)


def test_hard_cuts_on_bright_video_are_all_found():
    times = timeline(12)
    events = {2.0: 0.3, 4.0: 0.25, 6.0: 0.4, 8.0: 0.28, 10.0: 0.35}
    assert len(frames.detect_cuts(times, with_events(times, events))) == 5


def test_static_video_has_no_cuts():
    times = timeline(10)
    assert frames.detect_cuts(times, [1e-6] * len(times)) == []


def test_cuts_closer_than_min_scene_keep_the_stronger_one():
    times = timeline(10)
    found = frames.detect_cuts(times, with_events(times, {3.0: 0.2, 3.3: 0.4, 7.0: 0.3}))
    assert len(found) == 2
    assert any(abs(f - 3.3) < 0.05 for f in found)


def test_pacing_from_cuts():
    result = frames.pacing([4.0, 8.0], 12.0)
    assert result["avgSceneSec"] == 4.0
    assert result["cutsPerMinute"] == 10.0
    assert frames.pacing([], 0) == {}


def test_otsu_splits_two_clusters():
    cut, gap = frames.otsu_threshold(np.log(np.array([0.008, 0.009, 0.01, 0.03, 0.035, 0.04])))
    assert 0.01 < np.exp(cut) < 0.03
    assert gap > np.log(1.6)


def solid(rgb, size=(120, 80)):
    return np.full((size[1], size[0], 3), rgb, dtype=np.uint8)


def gradient_image(top, bottom, size=(120, 90)):
    h, w = size[1], size[0]
    ramp = np.linspace(0, 1, h)[:, None, None]
    return (np.array(top) * (1 - ramp) + np.array(bottom) * ramp).astype(np.uint8).repeat(w, axis=1)


def test_flat_background_is_solid():
    background = frames.analyze_background([solid((10, 20, 30)), solid((11, 21, 29))])
    assert background.kind == "solid"
    assert colors.delta_e(background.color, (10, 20, 30)) < 3


def test_vertical_gradient_is_detected_with_css_angle():
    # tối ở trên, sáng ở dưới -> hướng "xuống" = 180deg
    background = frames.analyze_background([gradient_image((5, 5, 20), (60, 90, 140))])
    assert background.kind == "gradient"
    assert background.angle == pytest.approx(180, abs=15)
    low, high = background.stops
    assert colors.luminance(low) < colors.luminance(high)


def test_gradient_direction_follows_brightness_left_to_right():
    image = gradient_image((5, 5, 20), (60, 90, 140)).transpose(1, 0, 2)
    background = frames.analyze_background([image])
    assert background.angle == pytest.approx(90, abs=15)


def test_vivid_pixels_are_found_even_when_tiny():
    image = solid((7, 11, 18), (200, 200))
    image[10:16, 10:60] = (34, 211, 238)  # thanh cyan ~0,4% diện tích
    found = frames.vivid_clusters([image])
    assert found and colors.delta_e(found[0][0], (34, 211, 238)) < 8


def test_no_vivid_pixels_in_a_grey_frame():
    assert frames.vivid_clusters([solid((90, 90, 90))]) == []


def test_palette_roles_from_ink_and_vivid():
    bg = (7, 11, 18)
    ink = [((240, 244, 250), 0.6), ((34, 211, 238), 0.2)]
    vivid = [((34, 211, 238), 0.002), ((245, 158, 11), 0.001)]
    palette = frames.pick_palette(bg, ink + vivid, [(bg, 0.9), ((16, 24, 39), 0.05)])
    assert colors.delta_e(palette["fg"], (240, 244, 250)) < 8
    assert colors.delta_e(palette["primary"], (34, 211, 238)) < 8
    assert colors.delta_e(palette["accent"], (245, 158, 11)) < 8
    assert colors.hue_distance(palette["primary"], palette["accent"]) >= 35


def test_palette_survives_sources_round_trip():
    sources = frames.pack_sources(
        (7, 11, 18),
        [((240, 244, 250), 0.6)],
        [((34, 211, 238), 0.002)],
        [((7, 11, 18), 0.9)],
    )
    palette = frames.palette_from_sources(sources)
    assert set(palette) == {"bg", "surface", "fg", "muted", "primary", "accent"}
    assert all(value.startswith("#") and len(value) == 7 for value in palette.values())


def glow_image(size=(120, 160)):
    """Nền tối với quầng sáng ở góc trên trái, như nền 'tech'."""
    h, w = size[1], size[0]
    ys, xs = np.mgrid[0:h, 0:w]
    blob = np.exp(-(((xs - 0.2 * w) / (0.35 * w)) ** 2 + ((ys - 0.15 * h) / (0.2 * h)) ** 2))
    base = np.array([7, 11, 18], dtype=np.float64)
    glow = np.array([30, 80, 95], dtype=np.float64)
    return (base + blob[..., None] * glow).astype(np.uint8)


def test_local_glow_is_not_mistaken_for_a_linear_gradient():
    background = frames.analyze_background([glow_image()])
    assert background.kind == "glow"
    assert background.residual > frames.GLOW_RESIDUAL


def test_planar_residual_is_zero_for_a_plane_and_large_for_a_bump():
    plane = np.array([[1.0, 2.0, 3.0], [2.0, 3.0, 4.0], [3.0, 4.0, 5.0]])
    assert frames.planar_residual(plane) == pytest.approx(0, abs=1e-9)
    bump = np.array([[0.0, 0.0, 0.0], [0.0, 5.0, 0.0], [0.0, 0.0, 0.0]])
    assert frames.planar_residual(bump) > 0.3
    assert frames.planar_residual(np.ones((3, 3))) == 0.0
