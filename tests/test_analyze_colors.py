from __future__ import annotations

import pytest

from pipeline.analyze import colors


def test_hex_round_trip_and_clamping():
    assert colors.to_hex((34, 211, 238)) == "#22D3EE"
    assert colors.from_hex("#22D3EE") == (34, 211, 238)
    assert colors.to_hex((300, -5, 0)) == "#FF0000"


def test_delta_e_is_zero_for_same_and_grows_with_difference():
    assert colors.delta_e((10, 20, 30), (10, 20, 30)) == 0
    near = colors.delta_e((10, 20, 30), (12, 22, 32))
    far = colors.delta_e((10, 20, 30), (200, 20, 30))
    assert near < 3 < 30 < far


def test_luminance_orders_black_grey_white():
    assert colors.luminance((0, 0, 0)) < colors.luminance((128, 128, 128)) < colors.luminance((255, 255, 255))
    assert colors.luminance((255, 255, 255)) == pytest.approx(1.0, abs=1e-3)


def test_saturation_ignores_dark_and_grey():
    assert colors.saturation((120, 120, 120)) == 0
    assert colors.saturation((2, 8, 10)) < 0.05  # rất tối nên không "rực"
    assert colors.saturation((34, 211, 238)) > 0.5


def test_hue_distance_wraps_around():
    assert colors.hue_distance((255, 0, 0), (255, 0, 40)) < 20
    assert colors.hue_distance((255, 0, 0), (0, 255, 255)) == pytest.approx(180, abs=1)


def test_mix_endpoints():
    assert colors.mix((0, 0, 0), (200, 100, 50), 0) == (0, 0, 0)
    assert colors.mix((0, 0, 0), (200, 100, 50), 1) == (200, 100, 50)
    assert colors.mix((0, 0, 0), (200, 100, 50), 0.5) == (100, 50, 25)
