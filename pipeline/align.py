from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import soundfile as sf
import soxr

from . import paths
from .progress import Progress

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"
FORMATS = json.loads((ROOT / "config" / "formats.json").read_text(encoding="utf-8"))

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(  # type: ignore[attr-defined]
            encoding="utf-8", errors="replace", line_buffering=True
        )
    except (AttributeError, ValueError):
        pass


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------- mapping


def clean_token(token: str) -> str:
    return "".join(ch for ch in token.lower() if ch.isalnum())


def map_words(
    script_words: list[str],
    asr_words: list[Any],
    scene_duration: float,
) -> tuple[list[dict[str, Any]], int]:
    """Gán thời gian của ASR cho từng từ trong kịch bản gốc.

    ASR hay đổi chữ ("AI" → "ây ai", số → chữ). Vì vậy ta chỉ dùng ASR để
    lấy *thời gian*, còn chữ hiển thị vẫn là chữ trong kịch bản.
    """
    s_keys = [clean_token(w) for w in script_words]
    a_keys = [clean_token(w.word) for w in asr_words]

    s_pos = [i for i, key in enumerate(s_keys) if key]
    a_pos = [i for i, key in enumerate(a_keys) if key]
    s_seq = [s_keys[i] for i in s_pos]
    a_seq = [a_keys[i] for i in a_pos]

    times: list[tuple[float, float] | None] = [None] * len(script_words)
    matched = 0

    matcher = difflib.SequenceMatcher(None, a_seq, s_seq, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag not in ("equal", "replace"):
            continue
        count = min(i2 - i1, j2 - j1)
        for offset in range(count):
            word = asr_words[a_pos[i1 + offset]]
            index = s_pos[j1 + offset]
            times[index] = (float(word.start), float(word.end))
            matched += 1

    # Nội suy cho những từ không khớp.
    index = 0
    total = len(script_words)
    while index < total:
        if times[index] is not None:
            index += 1
            continue

        start_gap = index
        while index < total and times[index] is None:
            index += 1
        end_gap = index  # exclusive

        prev_end = times[start_gap - 1][1] if start_gap > 0 else 0.0
        next_start = times[end_gap][0] if end_gap < total else scene_duration
        span = max(next_start - prev_end, 0.05)
        step = span / (end_gap - start_gap)
        for offset in range(end_gap - start_gap):
            begin = prev_end + offset * step
            times[start_gap + offset] = (begin, begin + step)

    result: list[dict[str, Any]] = []
    cursor = 0.0
    for word, slot in zip(script_words, times):
        assert slot is not None
        start, end = slot
        start = max(start, cursor)
        end = max(end, start + 0.05)
        cursor = start
        result.append({"w": word, "start": round(start, 3), "end": round(end, 3)})
    return result, matched


# ---------------------------------------------------------------- captions


def srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# Card quá ngắn làm caption nhấp nháy; gộp lại thành cụm đọc được.
CARD_MIN_SEC = 0.9
# Một card tối đa ~62 ký tự: vừa 2 dòng ở cỡ chữ 58px.
CARD_MAX_CHARS = 62
# Khi gộp card cụt được vượt nhẹ ngưỡng ký tự.
CARD_MERGE_SLACK = 12
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


def ends_thought(word: str) -> bool:
    return word.rstrip("\"'”’)").endswith((".", "!", "?", ":", ";"))


def is_number(word: str) -> bool:
    return bool(re.fullmatch(r"\d+(?:[.,]\d+)?", word.strip(".,;:!?%")))


def glued_pair(current: list[dict[str, Any]], nxt: dict[str, Any] | None) -> bool:
    """Không cắt giữa số và đơn vị (3 tỷ, 40 TOPS, 69%)."""
    if nxt is None or not current:
        return False
    tail = current[-1]["w"].strip(".,;:!?")
    head = nxt["w"].strip(".,;:!?")
    if is_number(tail) and (is_number(head) or head.lower() in UNIT_WORDS):
        return True
    return tail.lower() in ("bản", "phiên") and is_number(head)


def card_chars(card: list[dict[str, Any]]) -> int:
    return len(" ".join(word["w"] for word in card))


def merge_short_cards(
    cards: list[list[dict[str, Any]]], max_words: int
) -> list[list[dict[str, Any]]]:
    merged = [list(card) for card in cards]
    char_limit = CARD_MAX_CHARS + CARD_MERGE_SLACK
    word_limit = max_words + 4
    changed = True
    while changed:
        changed = False
        for index, card in enumerate(merged):
            if card[-1]["end"] - card[0]["start"] >= CARD_MIN_SEC:
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


def build_cards(words: list[dict[str, Any]], max_words: int) -> list[list[dict[str, Any]]]:
    """Chia phụ đề theo mệnh đề và độ dài hiển thị (~2 dòng), không theo số từ."""
    cards: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []

    for word in words:
        candidate = card_chars(current + [word]) if current else len(word["w"])
        if current and candidate > CARD_MAX_CHARS and not glued_pair(current, word):
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
    return merge_short_cards(cards, max_words)


def write_srt(path: Path, cards: list[list[dict[str, Any]]], uppercase: bool) -> None:
    lines: list[str] = []
    for number, card in enumerate(cards, start=1):
        start = card[0]["start"]
        end = card[-1]["end"]
        text = " ".join(word["w"] for word in card)
        if uppercase:
            text = text.upper()
        lines += [str(number), f"{srt_time(start)} --> {srt_time(end)}", text, ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def ass_time(seconds: float) -> str:
    cs = int(round(seconds * 100))
    h, cs = divmod(cs, 360_000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def write_ass(
    path: Path,
    cards: list[list[dict[str, Any]]],
    *,
    fmt: str,
    brand: dict[str, Any],
) -> None:
    cfg = FORMATS["formats"][fmt]
    caption = cfg["caption"]
    fg = brand["colors"]["fg"].lstrip("#")
    bgr = fg[4:6] + fg[2:4] + fg[0:2]

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {cfg['width']}
PlayResY: {cfg['height']}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{brand['fonts']['body']},{caption['fontSizePx']},&H00{bgr},&H00{bgr},&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{caption['strokePx']},0,2,60,140,{cfg['safeArea']['bottom']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    lines: list[str] = []
    for card in cards:
        start = card[0]["start"]
        end = card[-1]["end"]
        text = ""
        for word in card:
            centis = max(1, int(round((word["end"] - word["start"]) * 100)))
            label = word["w"].replace("{", "").replace("}", "")
            if caption["uppercase"]:
                label = label.upper()
            text += f"{{\\k{centis}}}{label} "
        lines.append(
            f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Caption,,0,0,0,,{text.strip()}"
        )

    path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.align",
        description="Căn thời gian từng từ bằng faster-whisper và sinh phụ đề.",
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--format", choices=["short", "long"])
    parser.add_argument("--model", default="small", help="tiny/base/small/medium")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    pid = args.project_id
    fmt = args.format or paths.detect_format(pid)
    if not fmt:
        raise SystemExit(
            f"Không tìm thấy script trong {paths.rel(paths.script_dir(pid))}"
        )

    script = load_json(paths.script_path(pid, fmt))
    brand = paths.load_brand(pid)
    language = str(script.get("meta", {}).get("language") or "vi")
    manifest = load_json(paths.manifest_path(pid, fmt))
    entries = manifest["scenes"]

    align_dir = paths.captions_dir(pid, fmt)
    align_dir.mkdir(parents=True, exist_ok=True)
    words_path = align_dir / "words.json"

    if words_path.exists() and not args.force:
        cached = load_json(words_path)
        current_hashes = {
            sid: entry.get("hash") for sid, entry in entries.items()
        }
        if (
            cached.get("voice") == manifest.get("voice")
            and cached.get("voices") == manifest.get("voices")
            and cached.get("hashes") == current_hashes
        ):
            print(
                f"  · dùng lại {paths.rel(words_path)} (--force để làm lại)"
            )
            print(f"  · {cached['totalSec']:.1f}s · {len(cached['scenes'])} scene")
            return 0
        print("  · audio đã thay đổi (giọng/hash khác), căn lại thời gian…")

    from faster_whisper import WhisperModel

    MODELS.mkdir(exist_ok=True)
    print(f"Nạp faster-whisper '{args.model}' (CPU, int8)…")
    started = time.perf_counter()
    model = WhisperModel(
        args.model, device="cpu", compute_type="int8", download_root=str(MODELS)
    )
    print(f"Nạp xong sau {time.perf_counter() - started:.1f}s\n")

    cfg = FORMATS["formats"][fmt]
    max_words = cfg["caption"]["maxWordsPerCard"]

    scenes_out: list[dict[str, Any]] = []
    all_cards: list[list[dict[str, Any]]] = []
    cursor = 0.0
    total_matched = 0
    total_words = 0
    total_audio = sum(
        float(entries[scene["id"]]["durationSec"])
        for scene in script["scenes"]
        if scene["id"] in entries
    )

    bar = Progress(total_audio, "Align", unit="giây audio")
    done_audio = 0.0

    for index, scene in enumerate(script["scenes"], start=1):
        sid = scene["id"]
        entry = entries.get(sid)
        if not entry:
            raise SystemExit(f"Thiếu audio cho {sid}. Chạy pipeline.tts trước.")

        audio_path = ROOT / entry["file"]
        duration = float(entry["durationSec"])

        started = time.perf_counter()
        audio, sample_rate = sf.read(str(audio_path), dtype="float32", always_2d=False)
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if sample_rate != 16000:
            audio = soxr.resample(audio, sample_rate, 16000)

        entry_segments = entry.get("segments") or []
        matched = 0
        scene_word_count = 0
        words: list[dict[str, Any]] = []

        if entry_segments:
            # Scene trộn tiếng Việt/Anh: transcribe từng đoạn bằng đúng ngôn ngữ,
            # rồi cộng offset để caption vẫn chạy liền mạch.
            for segment in entry_segments:
                segment_text = str(segment.get("text") or "").strip()
                if not segment_text:
                    continue
                segment_start = float(segment.get("startSec") or 0.0)
                segment_duration = float(segment.get("durationSec") or 0.0)
                if segment_duration <= 0:
                    continue
                start_i = max(0, int(round(segment_start * 16000)))
                end_i = min(len(audio), start_i + int(round(segment_duration * 16000)))
                if end_i <= start_i:
                    continue
                segment_audio = audio[start_i:end_i]
                asr_segments, _ = model.transcribe(
                    segment_audio,
                    language=str(segment.get("language") or language),
                    word_timestamps=True,
                    beam_size=5,
                    vad_filter=False,
                    condition_on_previous_text=False,
                )
                asr_words = [
                    word for asr_segment in asr_segments for word in asr_segment.words
                ]
                script_words = segment_text.split()
                local, segment_matched = map_words(
                    script_words, asr_words, segment_duration
                )
                words.extend(
                    {
                        "w": item["w"],
                        "start": round(cursor + segment_start + item["start"], 3),
                        "end": round(cursor + segment_start + item["end"], 3),
                    }
                    for item in local
                )
                matched += segment_matched
                scene_word_count += len(script_words)
        else:
            scene_language = str(scene.get("language") or language)
            asr_segments, _ = model.transcribe(
                audio,
                language=scene_language,
                word_timestamps=True,
                beam_size=5,
                vad_filter=False,
                condition_on_previous_text=False,
            )
            asr_words = [
                word for asr_segment in asr_segments for word in asr_segment.words
            ]
            script_words = scene["narration"].split()
            local, matched = map_words(script_words, asr_words, duration)
            words = [
                {
                    "w": item["w"],
                    "start": round(cursor + item["start"], 3),
                    "end": round(cursor + item["end"], 3),
                }
                for item in local
            ]
            scene_word_count = len(script_words)

        words.sort(key=lambda word: word["start"])
        scenes_out.append(
            {
                "id": sid,
                "type": scene["type"],
                "start": round(cursor, 3),
                "end": round(cursor + duration, 3),
                "words": words,
            }
        )
        all_cards.extend(build_cards(words, max_words))

        total_matched += matched
        total_words += scene_word_count
        cursor += duration
        done_audio += duration

        ratio = matched / scene_word_count if scene_word_count else 0
        bar.set(
            done_audio,
            detail=(
                f"{sid} · khớp {ratio:5.1%} · {time.perf_counter() - started:4.1f}s "
                f"· {index}/{len(script['scenes'])} scene"
            ),
        )

    data = {
        "format": fmt,
        "fps": cfg["fps"],
        "totalSec": round(cursor, 3),
        "voice": manifest.get("voice"),
        "voices": manifest.get("voices"),
        "hashes": {sid: entry.get("hash") for sid, entry in entries.items()},
        "scenes": scenes_out,
    }
    write_json(words_path, data)

    write_srt(align_dir / "captions.srt", all_cards, cfg["caption"]["uppercase"])
    write_ass(align_dir / "captions.ass", all_cards, fmt=fmt, brand=brand)
    bar.close()

    ratio = total_matched / total_words if total_words else 0
    print(
        f"\n✓ {len(scenes_out)} scene · {cursor:.1f}s · khớp từ {ratio:.1%} · "
        f"{len(all_cards)} caption card"
    )
    for name in ("words.json", "captions.srt", "captions.ass"):
        print(f"  {paths.rel(align_dir)}/{name}")
    paths.update_status(
        pid,
        captions={fmt: {"scenes": len(scenes_out), "totalSec": round(cursor, 2)}},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
