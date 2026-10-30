"""Logic suy ra phụ đề/chrome/màu chữ: dùng box OCR giả và ảnh vẽ bằng PIL."""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from pipeline.analyze import colors, text
from pipeline.analyze.text import Block, FrameText, TextBox

W, H = 540, 960
BG = (7, 12, 17)


def box(text_value, y0, y1, x0=0.1, x1=0.9):
    return TextBox(x0, y0, x1, y1, text_value)


def caption_frame(t, words, bottom=0.84, lines=2):
    """Caption căn giữa neo đáy: `lines` dòng, mỗi dòng cao 0,034."""
    boxes = []
    for i in range(lines):
        y1 = bottom - (lines - 1 - i) * 0.032
        boxes.append(box(f"{words} {i}", y1 - 0.030, y1, 0.08, 0.92))
    return FrameText(t, boxes)


def test_group_blocks_joins_adjacent_lines_only():
    blocks = text.group_blocks(
        [box("a", 0.80, 0.83), box("b", 0.84, 0.87), box("c", 0.20, 0.25)]
    )
    assert [len(b.lines) for b in sorted(blocks, key=lambda b: b.y0)] == [1, 2]


def test_block_pitch_is_none_for_single_line():
    assert Block([box("a", 0.1, 0.13)]).pitch is None
    assert Block([box("a", 0.1, 0.13), box("b", 0.14, 0.17)]).pitch == pytest.approx(0.04)


def test_find_caption_picks_the_band_that_stays_and_changes():
    frames = []
    for i in range(20):
        frame = caption_frame(i * 0.5, f"câu số {i}")
        # headline đổi vị trí theo scene, watermark cố định
        frame.boxes.append(box(f"tiêu đề {i // 5}", 0.20 + 0.01 * (i // 5), 0.26 + 0.01 * (i // 5)))
        frame.boxes.append(TextBox(0.70, 0.06, 0.95, 0.08, "DIVECODE1218"))
        frames.append(frame)
    caption = text.find_caption(frames, W, H)
    assert caption is not None
    assert caption.bottom == pytest.approx(0.84, abs=0.01)
    assert caption.presence > 0.9
    assert caption.lines_per_card == pytest.approx(2.0)
    assert caption.confidence > 0.7


def test_caption_font_size_comes_from_line_pitch_relative_to_short_side():
    frames = [caption_frame(i * 0.5, f"câu {i}") for i in range(10)]
    caption = text.find_caption(frames, 1080, 1920)
    # pitch 0,032 * 1920 px / 1,22 = 50,4px; cạnh ngắn 1080
    assert caption.font_px_rel == pytest.approx(0.032 * 1920 / text.LINE_HEIGHT / 1080, rel=0.02)


def test_static_text_that_never_changes_is_not_a_caption():
    frames = [FrameText(i * 0.5, [box("CỐ ĐỊNH", 0.80, 0.84)]) for i in range(10)]
    caption = text.find_caption(frames, W, H)
    assert caption is None or caption.change < 0.2


def test_no_text_means_no_caption():
    assert text.find_caption([FrameText(0.0, [])], W, H) is None
    assert text.find_caption([], W, H) is None


def test_uppercase_captions_are_flagged():
    frames = [
        FrameText(i * 0.5, [box(f"XIN CHÀO SỐ {i}", 0.80, 0.84, 0.1, 0.9)]) for i in range(10)
    ]
    assert text.find_caption(frames, W, H).uppercase is True


def test_find_chrome_detects_watermark_and_scene_index():
    frames = []
    for i in range(10):
        frame = caption_frame(i * 0.5, f"câu {i}")
        frame.boxes += [
            TextBox(0.75, 0.065, 0.95, 0.08, "·DIVECODE1218"),
            TextBox(0.02, 0.06, 0.12, 0.075, f"{i + 1:02d} / 13"),
        ]
        frames.append(frame)
    caption = text.find_caption(frames, W, H)
    chrome = text.find_chrome(frames, caption)
    assert chrome["watermark"]["uppercase"] is True
    assert chrome["watermark"]["x"] > 0.7
    assert chrome["sceneIndex"]["x"] < 0.2


def test_chrome_ignores_text_that_is_not_persistent():
    frames = [FrameText(i * 0.5, [box("tiêu đề", 0.2, 0.25)] if i < 2 else []) for i in range(10)]
    assert text.find_chrome(frames, None) == {"watermark": None, "sceneIndex": None}


CAPTION_TEXT = "Máy hay cloud thẳng"


def render_caption(card=None, highlight=False, size=44):
    """Ảnh phụ đề giả + khối chữ khớp đúng hộp chữ đã vẽ (như OCR thật)."""
    image = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=size)
    x0, y0, x1, y1 = draw.textbbox((70, 785), CAPTION_TEXT, font=font)
    if card:
        draw.rectangle((x0 - 30, y0 - 15, x1 + 30, y1 + 15), fill=card)
    draw.text((70, 785), CAPTION_TEXT, font=font, fill=(240, 244, 250))
    if highlight:
        draw.text((x1 + 12, 785), "AI", font=font, fill=(34, 211, 238))
        x1 = draw.textbbox((x1 + 12, 785), "AI", font=font)[2]
    block = Block([TextBox(x0 / W, y0 / H, x1 / W, y1 / H, CAPTION_TEXT)])
    return np.asarray(image), block


def test_read_ink_finds_text_colour_and_dark_background():
    image, block = render_caption()
    reading = text.read_ink(image, block)
    assert reading is not None
    assert colors.delta_e(reading.text, (240, 244, 250)) < 12
    assert colors.delta_e(reading.background, BG) < 6
    assert reading.outline is None


def test_read_ink_finds_highlight_colour():
    image, block = render_caption(highlight=True)
    reading = text.read_ink(image, block)
    assert any(
        share >= 0.02 and colors.delta_e(c, (34, 211, 238)) < 25 for c, share in reading.secondary
    )


def test_card_behind_caption_is_detected():
    image, block = render_caption(card=(16, 24, 39))
    card = text.detect_card(image, block)
    assert card is not None and colors.delta_e(card, (16, 24, 39)) < 8


def test_no_card_on_plain_background():
    image, block = render_caption()
    assert text.detect_card(image, block) is None


def test_scrim_detected_only_when_bottom_differs_from_middle():
    flat = np.full((H, W, 3), BG, dtype=np.uint8)
    assert text.has_scrim(flat) is False
    shaded = flat.copy()
    shaded[int(0.9 * H) :] = (0, 0, 0)
    shaded[: int(0.5 * H)] = (60, 70, 90)
    shaded[int(0.45 * H) : int(0.6 * H)] = (60, 70, 90)
    assert text.has_scrim(shaded) is True


def test_textbox_json_round_trip():
    original = FrameText(1.5, [box("xin chào", 0.1, 0.2)])
    restored = FrameText.from_json(original.to_json())
    assert restored.t == 1.5 and restored.boxes[0].text == "xin chào"
    assert restored.boxes[0].x1 == pytest.approx(0.9)
