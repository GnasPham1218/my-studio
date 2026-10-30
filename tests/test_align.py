from __future__ import annotations

from types import SimpleNamespace

import pytest

from pipeline import align


def asr(word: str, start: float, end: float):
    return SimpleNamespace(word=word, start=start, end=end)


def test_exact_match_uses_asr_times_but_script_spelling():
    mapped, matched = align.map_words(
        ["Xin", "chào", "AI"],
        [asr("xin", 0.0, 0.3), asr("chào", 0.3, 0.6), asr("ai", 0.6, 0.9)],
        1.0,
    )
    assert matched == 3
    assert [item["w"] for item in mapped] == ["Xin", "chào", "AI"]
    assert mapped[2]["start"] == 0.6


def test_unmatched_words_are_interpolated_between_neighbours():
    mapped, matched = align.map_words(
        ["một", "hai", "ba"],
        [asr("một", 0.0, 0.5), asr("ba", 1.5, 2.0)],
        2.0,
    )
    assert matched == 2
    assert mapped[0]["end"] <= mapped[1]["start"] + 1e-6
    assert 0.5 <= mapped[1]["start"] < mapped[1]["end"] <= 1.5


def test_asr_misreading_still_aligns_surrounding_words():
    # ASR đọc "69" thành "sáu mươi chín": từ lạ ở giữa không làm lệch hai đầu.
    mapped, _ = align.map_words(
        ["giảm", "69", "dung", "lượng"],
        [asr("giảm", 0.0, 0.3), asr("sáu", 0.3, 0.5), asr("mươi", 0.5, 0.7),
         asr("chín", 0.7, 0.9), asr("dung", 0.9, 1.2), asr("lượng", 1.2, 1.6)],
        1.6,
    )
    assert mapped[0]["start"] == 0.0
    assert mapped[2]["start"] == 0.9 and mapped[3]["end"] == 1.6


def test_times_are_monotonic_even_if_asr_overlaps():
    mapped, _ = align.map_words(
        ["a", "b"], [asr("a", 0.0, 1.0), asr("b", 0.5, 0.8)], 1.0
    )
    assert mapped[1]["start"] >= mapped[0]["start"]
    assert all(item["end"] > item["start"] for item in mapped)


def test_no_asr_output_spreads_words_over_the_scene():
    mapped, matched = align.map_words(["a", "b", "c", "d"], [], 2.0)
    assert matched == 0
    assert mapped[0]["start"] == 0.0
    assert mapped[-1]["end"] == pytest.approx(2.0, abs=0.06)


def test_punctuation_and_case_are_ignored_when_matching():
    assert align.clean_token("Chào,") == "chào"
    assert align.clean_token("69%") == "69"
