"""Chia từ đã căn thời gian thành card phụ đề, ghi SRT/ASS.

Căn thời gian (``align``) không phụ thuộc khung hình, còn cách chia card thì
có: màn dọc hẹp nên card ngắn, màn ngang rộng cho card dài. Vì vậy việc chia
card chạy ở bước build theo ``layout.caption`` của khung hình được chọn.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

Word = dict[str, Any]
Card = list[Word]

# Khi gộp card cụt được vượt nhẹ ngưỡng, nếu không sẽ để lại card nhấp nháy.
CARD_MERGE_CHAR_SLACK = 12
CARD_MERGE_WORD_SLACK = 4

UNIT_WORDS = {
    "tỷ",
    "triệu",
    "nghìn",
    "%",
    "bit",
    "bits",
    "tops",
    "gb",
    "tb",
    "mb",
    "ms",
    "mili",
    "giây",
    "phút",
    "năm",
    "lần",
}


@dataclass(frozen=True)
class CardRules:
    """Giới hạn chia card, lấy từ ``layout.caption`` của khung hình."""

    max_words: int
    max_chars: int
    min_sec: float

    @classmethod
    def from_layout(cls, layout: dict[str, Any]) -> "CardRules":
        caption = layout["caption"]
        return cls(
            max_words=int(caption["maxWordsPerCard"]),
            max_chars=int(caption["maxChars"]),
            min_sec=float(caption["minCardSec"]),
        )


def ends_thought(word: str) -> bool:
    return word.rstrip("\"'”’)").endswith((".", "!", "?", ":", ";"))


def is_number(word: str) -> bool:
    return bool(re.fullmatch(r"\d+(?:[.,]\d+)?", word.strip(".,;:!?%")))


def glued_pair(current: Card, nxt: Word | None) -> bool:
    """Không cắt giữa số và đơn vị (3 tỷ, 40 TOPS, 69%)."""
    if nxt is None or not current:
        return False
    tail = current[-1]["w"].strip(".,;:!?")
    head = nxt["w"].strip(".,;:!?")
    if is_number(tail) and (is_number(head) or head.lower() in UNIT_WORDS):
        return True
    return tail.lower() in ("bản", "phiên") and is_number(head)


def card_chars(card: Card) -> int:
    return len(" ".join(word["w"] for word in card))


def merge_short_cards(cards: list[Card], rules: CardRules) -> list[Card]:
    """Gộp card ngắn hơn ``min_sec`` vào card bên cạnh nếu chưa chốt ý."""
    merged = [list(card) for card in cards]
    char_limit = rules.max_chars + CARD_MERGE_CHAR_SLACK
    word_limit = rules.max_words + CARD_MERGE_WORD_SLACK
    changed = True
    while changed:
        changed = False
        for index, card in enumerate(merged):
            if card[-1]["end"] - card[0]["start"] >= rules.min_sec:
                continue
            if index + 1 < len(merged):
                nxt = merged[index + 1]
                can_merge = (
                    not ends_thought(card[-1]["w"])
                    and card_chars(card + nxt) <= char_limit
                    and len(card) + len(nxt) <= word_limit
                )
                if can_merge:
                    merged[index : index + 2] = [card + nxt]
                    changed = True
                    break
            if index > 0:
                prev = merged[index - 1]
                can_merge = (
                    not ends_thought(prev[-1]["w"])
                    and card_chars(prev + card) <= char_limit
                    and len(prev) + len(card) <= word_limit
                )
                if can_merge:
                    merged[index - 1 : index + 1] = [prev + card]
                    changed = True
                    break
    return merged


def build_cards(words: list[Word], rules: CardRules) -> list[Card]:
    """Chia phụ đề theo mệnh đề và độ dài hiển thị, không theo số từ."""
    cards: list[Card] = []
    current: Card = []

    for word in words:
        candidate = card_chars(current + [word]) if current else len(word["w"])
        if current and candidate > rules.max_chars and not glued_pair(current, word):
            cards.append(current)
            current = []

        current.append(word)
        # Dấu câu mạnh luôn kết thúc cụm; dấu phẩy chỉ tách khi đã đủ 3 từ.
        if ends_thought(word["w"]) or (
            word["w"].endswith(",") and len(current) >= 3
        ):
            cards.append(current)
            current = []

    if current:
        cards.append(current)
    return merge_short_cards(cards, rules)


def cards_to_json(cards: list[Card]) -> list[dict[str, Any]]:
    """Dạng ghi vào ``props.captions`` cho Remotion."""
    return [
        {"start": card[0]["start"], "end": card[-1]["end"], "words": card}
        for card in cards
    ]


# ---------------------------------------------------------------- SRT / ASS


def srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(path: Path, cards: list[Card], uppercase: bool) -> None:
    lines: list[str] = []
    for number, card in enumerate(cards, start=1):
        text = " ".join(word["w"] for word in card)
        if uppercase:
            text = text.upper()
        lines += [
            str(number),
            f"{srt_time(card[0]['start'])} --> {srt_time(card[-1]['end'])}",
            text,
            "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")


def ass_time(seconds: float) -> str:
    cs = int(round(seconds * 100))
    h, cs = divmod(cs, 360_000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _ass_color(hex_color: str) -> str:
    """#RRGGBB -> &H00BBGGRR (ASS dùng thứ tự BGR)."""
    fg = hex_color.lstrip("#")
    return f"&H00{fg[4:6]}{fg[2:4]}{fg[0:2]}"


def write_ass(
    path: Path,
    cards: list[Card],
    *,
    layout: dict[str, Any],
    colors: dict[str, str],
    font: str,
    uppercase: bool,
) -> None:
    caption = layout["caption"]
    safe = layout["safeArea"]
    primary = _ass_color(colors["fg"])

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {layout['width']}
PlayResY: {layout['height']}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{font},{caption['fontSize']},{primary},{primary},&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{caption['strokePx']},0,2,{safe['left']},{safe['right']},{safe['bottom']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    lines: list[str] = []
    for card in cards:
        text = ""
        for word in card:
            centis = max(1, int(round((word["end"] - word["start"]) * 100)))
            label = word["w"].replace("{", "").replace("}", "")
            if uppercase:
                label = label.upper()
            text += f"{{\\k{centis}}}{label} "
        lines.append(
            f"Dialogue: 0,{ass_time(card[0]['start'])},{ass_time(card[-1]['end'])},"
            f"Caption,,0,0,0,,{text.strip()}"
        )

    path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
