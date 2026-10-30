from __future__ import annotations

from pipeline import captions
from pipeline.captions import CardRules

VERTICAL = CardRules(max_words=6, max_chars=62, min_sec=0.9)


def words(text: str, step: float = 0.4, start: float = 0.0):
    """Chuỗi từ cách đều nhau, mỗi từ dài `step` giây."""
    result = []
    cursor = start
    for token in text.split():
        result.append({"w": token, "start": round(cursor, 3), "end": round(cursor + step, 3)})
        cursor += step
    return result


def texts(cards):
    return [" ".join(word["w"] for word in card) for card in cards]


def test_sentence_end_closes_a_card():
    cards = captions.build_cards(words("Một hai ba bốn. Năm sáu bảy tám."), VERTICAL)
    assert texts(cards) == ["Một hai ba bốn.", "Năm sáu bảy tám."]


def test_comma_splits_only_after_three_words():
    cards = captions.build_cards(
        words("Một, hai ba bốn năm sáu bảy tám chín mười mười một"), VERTICAL
    )
    # "Một," chỉ 1 từ nên không tách; không có card nào bắt đầu bằng "hai" do dấu phẩy sớm.
    assert texts(cards)[0].startswith("Một, hai")


def test_number_and_unit_are_never_separated():
    long_prefix = "a" * 58
    cards = captions.build_cards(words(f"{long_prefix} 69 tỷ tham số."), VERTICAL)
    for card in cards:
        joined = " ".join(word["w"] for word in card)
        assert "69" not in joined or "tỷ" in joined


def test_card_respects_max_chars_for_the_aspect():
    sentence = " ".join(["từmột"] * 14)  # ~84 ký tự, không dấu câu
    narrow = captions.build_cards(words(sentence), VERTICAL)
    wide = captions.build_cards(words(sentence), CardRules(12, 120, 0.9))
    assert len(narrow) > 1
    assert len(wide) == 1


def test_short_cards_are_merged_when_idea_is_not_closed():
    merged = captions.build_cards(words("Này là một câu rất ngắn", step=0.1), VERTICAL)
    assert len(merged) == 1


def test_short_card_after_finished_sentence_stays_separate():
    cards = captions.build_cards(words("Xong rồi. Ừ.", step=0.1), VERTICAL)
    assert texts(cards) == ["Xong rồi.", "Ừ."]


def test_empty_input_gives_no_cards():
    assert captions.build_cards([], VERTICAL) == []


def test_rules_come_from_layout():
    rules = CardRules.from_layout(
        {"caption": {"maxWordsPerCard": 7, "maxChars": 70, "minCardSec": 1.1}}
    )
    assert (rules.max_words, rules.max_chars, rules.min_sec) == (7, 70, 1.1)


def test_cards_to_json_uses_first_and_last_word_times():
    card = words("Một hai ba")
    assert captions.cards_to_json([card]) == [{"start": 0.0, "end": 1.2, "words": card}]


def test_srt_and_ass_time_formats():
    assert captions.srt_time(3661.5) == "01:01:01,500"
    assert captions.ass_time(3661.5) == "1:01:01.50"


def test_write_srt_numbers_cards_and_supports_uppercase(tmp_path):
    cards = [words("xin chào"), words("tạm biệt", start=2.0)]
    target = tmp_path / "out.srt"
    captions.write_srt(target, cards, uppercase=True)
    content = target.read_text(encoding="utf-8")
    assert content.startswith("1\n00:00:00,000 --> 00:00:00,800\nXIN CHÀO")
    assert "\n2\n00:00:02,000" in content


def test_write_ass_uses_layout_geometry_and_brand_colour(tmp_path):
    layout = {
        "width": 1080,
        "height": 1920,
        "safeArea": {"left": 60, "right": 140, "bottom": 380, "top": 220},
        "caption": {"fontSize": 52, "strokePx": 6},
    }
    target = tmp_path / "out.ass"
    captions.write_ass(
        target,
        [words("xin chào")],
        layout=layout,
        colors={"fg": "#112233"},
        font="Be Vietnam Pro",
        uppercase=False,
    )
    content = target.read_text(encoding="utf-8")
    assert "PlayResX: 1080" in content and "PlayResY: 1920" in content
    assert "&H00332211" in content  # #RRGGBB -> BGR
    assert "Be Vietnam Pro,52" in content
    assert ",60,140,380," in content
