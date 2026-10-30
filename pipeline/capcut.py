"""Xuất video sang CapCut, theo hai cách.

1. Bộ file (chắc chắn dùng được): ``out/<id>/06-capcut/<format>-<aspect>/``
   - ``scenes/s01.mp4 …``: mỗi cảnh một clip không tiếng, không caption, không chuyển cảnh
   - ``audio.wav``: giọng + SFX gộp, khớp từ giây 0
   - ``audio/voice/*.wav``, ``audio/sfx/*``: từng file riêng (draft dùng)
   - ``captions.srt``: nhập vào CapCut bằng Văn bản → Nhập phụ đề

2. Draft CapCut (không chính thức): ghi thẳng một dự án nháp vào thư mục draft
   của CapCut desktop, mở CapCut là thấy sẵn timeline. Định dạng draft không có
   tài liệu; khuôn ở ``config/capcut/draft-template.json`` trích từ CapCut 9.5.
   CapCut đổi định dạng thì trích lại khuôn từ một draft mới.

Draft trỏ tới file trong bộ file theo đường dẫn tuyệt đối, nên đừng xoá
``out/<id>/06-capcut`` khi còn dùng draft.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import sys
import time
import uuid
import wave
from pathlib import Path
from typing import Any, Callable

from . import config, paths, render
from .fontmetrics import FontMetrics

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(  # type: ignore[attr-defined]
            encoding="utf-8", errors="replace", line_buffering=True
        )
    except (AttributeError, ValueError):
        pass

TEMPLATE_PATH = paths.ROOT / "config" / "capcut" / "draft-template.json"
# File phụ CapCut tạo cho mọi draft trống (chép nguyên từ CapCut 9.7).
SKELETON_DIR = paths.ROOT / "config" / "capcut" / "skeleton"
# Kiểu phụ đề học từ CapCut (--learn-style); không có thì draft không kèm phụ đề.
CAPTION_STYLE_PATH = paths.ROOT / "config" / "capcut" / "caption-style.json"
# Đánh dấu draft do pipeline tạo: chỉ những thư mục có file này mới bị ghi đè.
MARKER = ".my-studio"
US = 1_000_000  # CapCut tính thời gian bằng micro giây.

README = """Mở bằng CapCut
==============

Cách 1: kéo thả (luôn dùng được)
  1. Tạo dự án mới, tỉ lệ {ratio}.
  2. Kéo các file trong scenes/ vào timeline theo thứ tự s01, s02, …
  3. Kéo audio.wav vào track âm thanh, đặt ở giây 0.
  4. Văn bản → Nhập phụ đề → chọn captions.srt.
  5. Thêm chuyển cảnh, hiệu ứng của CapCut giữa các clip.

Cách 2: draft có sẵn
  Mở CapCut, dự án "{name}" nằm trong danh sách dự án.
  Draft trỏ tới file trong thư mục này, đừng di chuyển hay xoá nó.
  Phụ đề đã có sẵn theo kiểu học bằng --learn-style (nếu chưa học thì
  nhập captions.srt như bước 4).
"""


def new_id() -> str:
    return str(uuid.uuid4()).upper()


def to_us(seconds: float) -> int:
    return int(round(seconds * US))


def frames_us(frames: int, fps: int) -> int:
    return int(round(frames * US / fps))


def wav_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / float(handle.getframerate())


def drafts_root() -> Path | None:
    """Thư mục draft của CapCut desktop; đặt CAPCUT_DRAFTS để ghi đè."""
    env = os.environ.get("CAPCUT_DRAFTS")
    if env:
        return Path(env)
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        return None
    root = Path(local) / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
    return root if root.is_dir() else None


def posix(path: Path) -> str:
    return path.resolve().as_posix()


# ---------------------------------------------------------------- bộ file


def collect_audio(props: dict[str, Any], kit: Path) -> None:
    """Copy giọng từng cảnh và SFX vào bộ file để draft không phụ thuộc 02-audio."""
    project_dir = paths.out_dir(props["projectId"])
    voice_dir = kit / "audio" / "voice"
    voice_dir.mkdir(parents=True, exist_ok=True)
    for scene in props["scenes"]:
        shutil.copy2(
            project_dir / props["audioDir"] / f"{scene['id']}.wav",
            voice_dir / f"{scene['id']}.wav",
        )
    if props.get("sfxDir"):
        sfx_dir = kit / "audio" / "sfx"
        sfx_dir.mkdir(parents=True, exist_ok=True)
        for item in props["sfxCatalog"].values():
            source = project_dir / props["sfxDir"] / item["file"]
            if source.exists():
                shutil.copy2(source, sfx_dir / item["file"])


# ---------------------------------------------------------------- draft


class Draft:
    """Dựng draft_content.json bằng cách nhân bản segment mẫu trong khuôn."""

    def __init__(self, template: dict[str, Any], props: dict[str, Any]) -> None:
        self.template = template
        self.fps = int(props["fps"])
        self.content = copy.deepcopy(template["content"])
        self.content["id"] = new_id()
        self.content["fps"] = float(self.fps)
        self.content["canvas_config"].update(
            width=int(props["width"]), height=int(props["height"]), ratio="original"
        )
        now = int(time.time())
        self.content["create_time"] = now
        self.content["update_time"] = now
        self.materials: dict[str, list[Any]] = self.content["materials"]
        self.tracks: list[dict[str, Any]] = self.content["tracks"]

    def _track(self, kind: str) -> dict[str, Any]:
        track = copy.deepcopy(self.template[kind]["track"])
        track["id"] = new_id()
        track["segments"] = []
        self.tracks.append(track)
        return track

    def _segment(
        self,
        kind: str,
        track: dict[str, Any],
        material: dict[str, Any],
        start_us: int,
        duration_us: int,
        volume: float = 1.0,
    ) -> None:
        part = self.template[kind]
        self.materials.setdefault(part["materialKind"], []).append(material)
        refs = []
        for extra_kind, extra in part["extra"]:
            item = copy.deepcopy(extra)
            item["id"] = new_id()
            self.materials.setdefault(extra_kind, []).append(item)
            refs.append(item["id"])

        segment = copy.deepcopy(part["segment"])
        segment.update(
            id=new_id(),
            material_id=material["id"],
            extra_material_refs=refs,
            source_timerange={"start": 0, "duration": duration_us},
            target_timerange={"start": start_us, "duration": duration_us},
            volume=volume,
            last_nonzero_volume=volume,
            track_render_index=self.tracks.index(track),
            render_index=0,
        )
        track["segments"].append(segment)

    def add_video(self, track: dict[str, Any], path: Path, start_us: int, duration_us: int,
                  width: int, height: int) -> None:
        material = copy.deepcopy(self.template["video"]["material"])
        material.update(
            id=new_id(),
            unique_id=uuid.uuid4().hex,
            local_material_id=str(uuid.uuid4()),
            path=posix(path),
            material_name=path.name,
            duration=duration_us,
            width=width,
            height=height,
            has_audio=False,
        )
        self._segment("video", track, material, start_us, duration_us)

    def add_audio(self, track: dict[str, Any], path: Path, start_us: int, duration_us: int,
                  volume: float = 1.0) -> None:
        material = copy.deepcopy(self.template["audio"]["material"])
        material.update(
            id=new_id(),
            unique_id=uuid.uuid4().hex,
            local_material_id=str(uuid.uuid4()),
            music_id=str(uuid.uuid4()),
            path=posix(path),
            name=path.name,
            duration=duration_us,
        )
        self._segment("audio", track, material, start_us, duration_us, volume)

    def finish(self) -> dict[str, Any]:
        self.content["duration"] = max(
            (
                seg["target_timerange"]["start"] + seg["target_timerange"]["duration"]
                for track in self.tracks
                for seg in track["segments"]
            ),
            default=0,
        )
        return self.content


# ---------------------------------------------------------------- phụ đề
#
# Kiểu phụ đề học từ một draft CapCut người dùng đã chỉnh tay (--learn-style):
# segment chữ đầu tiên cùng material và phụ kiện của nó được lưu làm khuôn,
# mỗi card phụ đề nhân bản khuôn đó với id mới, chữ và thời gian của card.
# Đường dẫn cache font/hiệu ứng của CapCut lưu dạng {CAPCUT_DATA} để không
# dính tên người dùng.


def capcut_data() -> Path | None:
    root = drafts_root()
    return root.parent.parent if root else None


def remap_ids(value: Any, mapping: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {k: remap_ids(v, mapping) for k, v in value.items()}
    if isinstance(value, list):
        return [remap_ids(v, mapping) for v in value]
    if isinstance(value, str) and value in mapping:
        return mapping[value]
    return value


def utf16_len(text: str) -> int:
    """CapCut đo range của style theo đơn vị UTF-16."""
    return len(text.encode("utf-16-le")) // 2


def set_text(material: dict[str, Any], text: str, words: list[dict[str, Any]], start: float) -> None:
    """Thay chữ trong material text, giữ nguyên style; words tính theo ms từ đầu card."""
    content = json.loads(material["content"])
    content["text"] = text
    for item in content.get("styles", []):
        item["range"] = [0, utf16_len(text)]
    material["content"] = json.dumps(content, ensure_ascii=False, separators=(",", ":"))
    for font in material.get("fonts", []):
        font["id"] = new_id()
    if material.get("words", {}).get("text"):
        starts: list[int] = []
        ends: list[int] = []
        tokens: list[str] = []
        for index, word in enumerate(words):
            begin = int(round((word["start"] - start) * 1000))
            end = int(round((word["end"] - start) * 1000))
            starts.append(begin)
            ends.append(end)
            tokens.append(word["w"])
            if index + 1 < len(words):  # khoảng trắng dài 0 ở cuối mỗi chữ, như CapCut
                starts.append(end)
                ends.append(end)
                tokens.append(" ")
        material["words"] = {"start_time": starts, "end_time": ends, "text": tokens}


NO_WRAP_WIDTH = 3.0  # line_max_width (tỉ lệ màn hình) đủ lớn để template không tự xuống dòng

LOOK_KEYS = ("text_color", "font_path", "font_resource_id", "font_title", "font_name", "fonts")


def read_look(material: dict[str, Any]) -> dict[str, Any]:
    """Màu + font của một material chữ, tách khỏi template/hoạt ảnh."""
    style = json.loads(material["content"])["styles"][0]
    look = {key: material[key] for key in LOOK_KEYS if key in material}
    look["fill"] = style.get("fill")
    look["font"] = style.get("font")
    return look


def apply_look(material: dict[str, Any], look: dict[str, Any]) -> None:
    content = json.loads(material["content"])
    for style in content.get("styles", []):
        if look.get("fill"):
            style["fill"] = look["fill"]
        if look.get("font"):
            style["font"] = look["font"]
    material["content"] = json.dumps(content, ensure_ascii=False, separators=(",", ":"))
    for key in LOOK_KEYS:
        if key in look:
            material[key] = copy.deepcopy(look[key])


def load_caption_style() -> dict[str, Any] | None:
    if not CAPTION_STYLE_PATH.exists():
        return None
    raw = CAPTION_STYLE_PATH.read_text(encoding="utf-8")
    data = capcut_data()
    if data:
        raw = raw.replace("{CAPCUT_DATA}", data.as_posix())
    return json.loads(raw)


def line_fits(style: dict[str, Any], canvas_width: int) -> Callable[[str], bool] | None:
    """Hàm kiểm một đoạn chữ có vừa một dòng không; None = không đủ dữ liệu để chia."""
    scale = style.get("emPerSize")
    text = (style.get("inner") or style["material"])[1]
    first = json.loads(text["content"])["styles"][0]
    look_font = (style.get("look") or {}).get("font") or first.get("font") or {}
    font_path = Path(look_font.get("path", ""))
    if not scale or not font_path.is_file() or not first.get("size"):
        return None
    font = FontMetrics(font_path)
    em_px = scale * float(first["size"])
    # Chừa 10% cho viền chữ, kerning và hoạt ảnh phóng to của template.
    limit = float(text.get("line_max_width") or 0.82) * canvas_width * 0.9
    # Nhiều template tự viết HOA: đo bản rộng hơn trong hai bản.
    return lambda value: max(font.width_em(value), font.width_em(value.upper())) * em_px <= limit


def split_cards(
    cards: list[dict[str, Any]], fits: Callable[[str], bool]
) -> list[dict[str, Any]]:
    """Chia card dài thành nhiều card ngắn vừa một dòng, giữ thời gian từng chữ."""
    result: list[dict[str, Any]] = []
    for card in cards:
        groups: list[list[dict[str, Any]]] = [[]]
        for word in card["words"]:
            current = groups[-1]
            candidate = " ".join(w["w"] for w in [*current, word])
            if current and not fits(candidate):
                groups.append([word])
            else:
                current.append(word)
        # Cụm cuối quá ngắn (1 chữ) thì cân lại với cụm trước cho đỡ cụt.
        if len(groups) > 1 and len(groups[-1]) == 1 and len(groups[-2]) > 2:
            moved = groups[-2][-1]
            if fits(" ".join(w["w"] for w in [moved, *groups[-1]])):
                groups[-2].pop()
                groups[-1].insert(0, moved)
        for index, words in enumerate(groups):
            if not words:
                continue
            start = card["start"] if index == 0 else words[0]["start"]
            end = card["end"] if index == len(groups) - 1 else groups[index + 1][0]["start"]
            result.append({"start": start, "end": max(end, start + 0.05), "words": words})
    return result


def karaoke_pieces(card: dict[str, Any], mode: str) -> list[dict[str, Any]]:
    """Một card thành nhiều đoạn liền nhau, mỗi đoạn ứng với một chữ đang đọc.

    ``active`` là khoảng (UTF-16) được tô màu chữ chạy, phần còn lại giữ màu nền:
    - ``current``: chỉ chữ đang đọc (kiểu template 逐词高亮 của CapCut);
    - ``spoken``: mọi chữ đã đọc tính tới chữ đang đọc.
    """
    words = card["words"]
    pieces = []
    offset = 0
    for index, word in enumerate(words):
        begin = offset + (1 if index else 0)
        offset = begin + utf16_len(word["w"])
        start = card["start"] if index == 0 else word["start"]
        end = card["end"] if index == len(words) - 1 else words[index + 1]["start"]
        if end - start < 0.02 and index < len(words) - 1:  # chữ quá sát: gộp vào đoạn sau
            continue
        active = [begin, offset] if mode == "current" else [0, offset]
        pieces.append({"start": start, "end": end, "words": words, "active": active})
    if pieces:
        pieces[0]["start"] = card["start"]
        pieces[-1]["end"] = card["end"]
        for prev, nxt in zip(pieces, pieces[1:]):
            prev["end"] = nxt["start"]
    return pieces or [card]


def hex_rgb(value: str) -> list[float]:
    value = value.lstrip("#")[:6]
    return [int(value[i : i + 2], 16) / 255 for i in (0, 2, 4)]


def solid(color: str) -> dict[str, Any]:
    return {"content": {"render_type": "solid", "solid": {"color": hex_rgb(color)}}}


def color_active(material: dict[str, Any], active: list[int], highlight: dict[str, Any]) -> None:
    """Tô khoảng ``active`` bằng màu chữ chạy (màu trong look), phần còn lại màu nền.

    Kèm cỡ chữ và viền theo ``wordHighlight`` để bắt chước template đã chọn.
    """
    content = json.loads(material["content"])
    base = copy.deepcopy(content["styles"][0])
    if highlight.get("size"):
        base["size"] = highlight["size"]
        material["font_size"] = float(highlight["size"])
    stroke = highlight.get("stroke")
    if stroke:
        base["strokes"] = [{**solid(stroke["color"]), "width": stroke["width"], "mode": 0}]
        material["border_color"] = stroke["color"]
        material["border_width"] = stroke["width"]
    total = utf16_len(content["text"])
    start, end = max(0, active[0]), min(total, active[1])
    rest = {**copy.deepcopy(base), "fill": solid(highlight["base"])}
    styles = []
    if start > 0:
        styles.append({**copy.deepcopy(rest), "range": [0, start]})
    if end > start:
        styles.append({**copy.deepcopy(base), "range": [start, end]})
    if end < total:
        styles.append({**copy.deepcopy(rest), "range": [end, total]})
    content["styles"] = styles
    material["content"] = json.dumps(content, ensure_ascii=False, separators=(",", ":"))


def add_captions(draft: "Draft", style: dict[str, Any], cards: list[dict[str, Any]]) -> None:
    highlight = style.get("wordHighlight") if not style.get("inner") else None
    fits = line_fits(style, int(draft.content["canvas_config"]["width"]))
    per_page = (highlight or {}).get("wordsPerPage")
    if per_page:
        # Trang tối đa N chữ như template, và vẫn phải vừa một dòng.
        line = fits
        fits = lambda value: len(value.split()) <= per_page and (line is None or line(value))
    if fits:
        cards = split_cards(cards, fits)
    track = copy.deepcopy(style["track"])
    track["id"] = new_id()
    track["segments"] = []
    draft.tracks.append(track)
    index = draft.tracks.index(track)

    pieces: list[dict[str, Any]] = []
    for card in cards:
        pieces.extend(karaoke_pieces(card, highlight.get("mode", "current")) if highlight else [card])

    ids = [style["material"][1]["id"], *(item["id"] for _, item in style["extra"])]
    if style.get("inner"):
        ids.append(style["inner"][1]["id"])
    for order, card in enumerate(pieces):
        mapping = {old: new_id() for old in ids}
        start_us = to_us(card["start"])
        duration_us = max(1, to_us(card["end"]) - start_us)
        text = " ".join(word["w"] for word in card["words"])

        kind, material = remap_ids(copy.deepcopy(style["material"]), mapping)
        extra = remap_ids(copy.deepcopy(style["extra"]), mapping)
        if style.get("inner"):
            inner_kind, inner = remap_ids(copy.deepcopy(style["inner"]), mapping)
            if style.get("look"):
                apply_look(inner, style["look"])
            if fits:
                # Template tự ngắt dòng theo khung hẹp của nó (vd. "MƯỜI NĂM / TRƯỚC");
                # câu đã được chia vừa một dòng nên nới khung để nó không ngắt nữa.
                inner["line_max_width"] = NO_WRAP_WIDTH
            set_text(inner, text, card["words"], card["start"])
            draft.materials.setdefault(inner_kind, []).append(inner)
            for resource in material.get("text_info_resources", []):
                resource["id"] = new_id()
                resource["attach_info"]["duration"] = duration_us
        else:
            if style.get("look"):
                apply_look(material, style["look"])
            set_text(material, text, card["words"], card["start"])
            if highlight and "active" in card:
                color_active(material, card["active"], highlight)
        for extra_kind, item in extra:
            for animation in item.get("animations", []):
                if animation.get("type") == "caption":
                    animation["duration"] = duration_us
            draft.materials.setdefault(extra_kind, []).append(item)
        draft.materials.setdefault(kind, []).append(material)

        segment = remap_ids(copy.deepcopy(style["segment"]), mapping)
        segment.update(
            id=new_id(),
            target_timerange={"start": start_us, "duration": duration_us},
            track_render_index=index,
            render_index=style["segment"].get("render_index", 14000) + order,
        )
        track["segments"].append(segment)


def learn_style(draft_name: str, look_only: bool = False, plain: bool = False) -> int:
    """Lưu kiểu phụ đề từ một draft CapCut làm khuôn cho các lần xuất sau.

    Ưu tiên segment có caption template (text_templates); không có thì lấy
    phụ đề thường (texts type subtitle). Hai phần lưu riêng:
    - template (hoạt ảnh, hiệu ứng): ``look_only=False``, giữ look đã lưu;
    - look (màu + font): ``look_only=True``, giữ template đã lưu.
    ``plain=True`` bỏ qua caption template, chỉ học phụ đề thường.
    """
    root = drafts_root()
    if root is None:
        raise SystemExit("Không tìm thấy thư mục draft của CapCut.")
    path = root / draft_name / "draft_content.json"
    if not path.exists():
        raise SystemExit(f"Không thấy draft '{draft_name}' trong {root}.")
    content = json.loads(path.read_text(encoding="utf-8"))
    by_id = {
        item["id"]: (kind, item)
        for kind, items in content["materials"].items()
        if isinstance(items, list)
        for item in items
        if isinstance(item, dict) and "id" in item
    }

    found: dict[str, Any] | None = None
    for wanted in ("texts",) if plain else ("text_templates", "texts"):
        for track in content["tracks"]:
            if track["type"] != "text":
                continue
            for segment in track["segments"]:
                kind, material = by_id.get(segment["material_id"], ("", {}))
                if kind == wanted:
                    found = {"track": track, "segment": segment, "material": [kind, material]}
                    break
            if found:
                break
        if found:
            break
    if not found:
        raise SystemExit(f"Draft '{draft_name}' không có phụ đề/chữ nào để học.")

    segment = found["segment"]
    material = found["material"][1]
    style: dict[str, Any] = {
        "_comment": f"Kiểu phụ đề học từ draft '{draft_name}' (python -m pipeline.capcut --learn-style).",
        "track": {k: v for k, v in found["track"].items() if k != "segments"},
        "segment": segment,
        "material": found["material"],
        "extra": [list(by_id[ref]) for ref in segment["extra_material_refs"] if ref in by_id],
    }
    resources = material.get("text_info_resources") or []
    if resources:
        style["inner"] = list(by_id[resources[0]["text_material_id"]])
    text_material = style["inner"][1] if resources else material
    # Tỉ lệ px/em trên mỗi đơn vị cỡ chữ của CapCut, đo từ chữ mẫu của template
    # (CapCut lưu bề rộng gốc khi áp template) và file font của chính nó.
    if resources:
        first = json.loads(text_material["content"])["styles"][0]
        sample = json.loads(text_material["content"])["text"]
        width = resources[0]["attach_info"].get("original_size_width") or 0
        font_path = Path(first.get("font", {}).get("path", ""))
        if sample and width and font_path.is_file() and first.get("size"):
            em = FontMetrics(font_path).width_em(sample)
            style["emPerSize"] = width / em / float(first["size"])

    saved = load_caption_style()
    if look_only:
        if not saved:
            raise SystemExit("Chưa có template phụ đề: chạy --learn-style trước.")
        saved["look"] = read_look(text_material)
        style = saved
        label = "màu + font"
    else:
        if saved and saved.get("look"):
            style["look"] = saved["look"]
        if saved and saved.get("wordHighlight"):
            style["wordHighlight"] = saved["wordHighlight"]
        if saved and "emPerSize" not in style and saved.get("emPerSize"):
            style["emPerSize"] = saved["emPerSize"]  # phụ đề thường không tự đo được
        label = material.get("name") or material.get("type")

    raw = json.dumps(style, ensure_ascii=False, indent=1)
    data = capcut_data()
    if data:
        raw = raw.replace(data.as_posix(), "{CAPCUT_DATA}")
    CAPTION_STYLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CAPTION_STYLE_PATH.write_text(raw, encoding="utf-8")
    kept = " (giữ màu + font đã lưu)" if not look_only and style.get("look") else ""
    print(f"✓ Đã học {label}{kept} → {paths.rel(CAPTION_STYLE_PATH)}")
    return 0


def build_draft(props: dict[str, Any], kit: Path) -> dict[str, Any]:
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    draft = Draft(template, props)
    fps = draft.fps
    width, height = int(props["width"]), int(props["height"])

    video = draft._track("video")
    style = load_caption_style()
    if style and props.get("captions"):
        add_captions(draft, style, props["captions"])
    voice = draft._track("audio")
    starts = [int(round(scene["startSec"] * fps)) for scene in props["scenes"]]
    for index, scene in enumerate(props["scenes"]):
        start = starts[index]
        end = start + max(1, int(round(scene["durationSec"] * fps)))
        if index + 1 < len(starts):
            end = min(end, starts[index + 1])  # làm tròn không được đè cảnh sau
        frames = end - start
        # Tính theo mốc frame tuyệt đối để các clip nối khít, không lệch 1µs.
        draft.add_video(
            video,
            kit / "scenes" / f"{scene['id']}.mp4",
            frames_us(start, fps),
            frames_us(end, fps) - frames_us(start, fps),
            width,
            height,
        )
        wav = kit / "audio" / "voice" / f"{scene['id']}.wav"
        # Giọng không được tràn sang cảnh sau.
        draft.add_audio(
            voice,
            wav,
            to_us(scene["startSec"]),
            min(to_us(wav_seconds(wav)), frames_us(frames, fps)),
        )

    sfx_track = None
    for scene in props["scenes"]:
        name = scene.get("sfx")
        item = props["sfxCatalog"].get(name or "")
        if not item or not props.get("sfxDir"):
            continue
        path = kit / "audio" / "sfx" / item["file"]
        if not path.exists():
            continue
        if sfx_track is None:
            sfx_track = draft._track("audio")
        draft.add_audio(
            sfx_track,
            path,
            to_us(scene["startSec"] + float(scene.get("sfxAtSec") or 0)),
            to_us(float(item["durationSec"])),
            float(scene.get("sfxVolume") or item["defaultVolume"]),
        )
    return draft.finish()


def media_entries(content: dict[str, Any], now: int) -> list[dict[str, Any]]:
    """Danh sách file đã "nhập" (bảng Media của CapCut), mỗi file một lần."""
    entries: dict[str, dict[str, Any]] = {}
    for kind, metetype in (("videos", "video"), ("audios", "music")):
        for material in content["materials"].get(kind, []):
            if material["path"] in entries:
                continue
            entries[material["path"]] = {
                "ai_group_type": "",
                "create_time": now,
                "duration": material["duration"],
                "enter_from": 0,
                "extra_info": Path(material["path"]).name,
                "file_Path": material["path"],
                "height": material.get("height", 0),
                "id": material["local_material_id"],
                "import_time": now,
                "import_time_ms": now * US,
                "item_source": 1,
                "material_color_tag": "",
                "md5": "",
                "metetype": metetype,
                "roughcut_time_range": {"duration": material["duration"], "start": 0},
                "sub_time_range": {"duration": -1, "start": -1},
                "type": 0,
                "width": material.get("width", 0),
            }
    return list(entries.values())


def write_draft(
    content: dict[str, Any], folder: Path, name: str, root: Path
) -> None:
    """Ghi đủ các file CapCut 9.x cần để nhận ra một draft.

    Thiếu ``Timelines/project.json`` (timeline chính) là CapCut 9.7 crash khi mở,
    nên ngoài draft_content còn chép bộ khung trong ``config/capcut/skeleton``.
    """
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    if folder.exists():
        shutil.rmtree(folder)
    timeline = folder / "Timelines" / content["id"]
    timeline.mkdir(parents=True)

    def dump(path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )

    # Bộ khung: file chung ở gốc, phần attachment lặp lại trong thư mục timeline.
    shutil.copytree(SKELETON_DIR, folder, dirs_exist_ok=True)
    for item in ("attachment_editing.json", "attachment_pc_common.json", "common_attachment"):
        source = SKELETON_DIR / item
        if source.is_dir():
            shutil.copytree(source, timeline / item)
        else:
            shutil.copy2(source, timeline / item)

    for empty in (
        "adjust_mask", "matting", "qr_upload", "smart_crop", "subdraft",
        "Resources/audioAlg", "Resources/videoAlg", "Resources/digitalHuman/audio",
        "Resources/digitalHuman/bsinfo", "Resources/digitalHuman/video",
    ):
        (folder / empty).mkdir(parents=True, exist_ok=True)

    now = int(time.time())
    now_us = int(time.time() * US)
    project = {
        "config": {
            "color_space": -1,
            "hdr_vivid": False,
            "mixed_track_mode_on": False,
            "render_index_track_mode_on": False,
            "use_float_render": False,
        },
        "create_time": now_us,
        "id": new_id(),
        "main_timeline_id": content["id"],
        "timelines": [
            {
                "create_time": now_us,
                "id": content["id"],
                "is_marked_delete": False,
                "name": "Timeline 01",
                "update_time": now_us,
            }
        ],
        "update_time": now_us,
        "version": 0,
    }
    dump(folder / "Timelines" / "project.json", project)
    dump(folder / "Timelines" / "project.json.bak", project)

    media = media_entries(content, now)
    dump(
        folder / "draft_virtual_store.json",
        {
            "draft_materials": [],
            "draft_virtual_store": [
                {
                    "type": 0,
                    "value": [
                        {
                            "creation_time": 0,
                            "display_name": "",
                            "filter_type": 0,
                            "id": "",
                            "import_time": 0,
                            "import_time_us": 0,
                            "material_color_tag": "",
                            "sort_sub_type": 0,
                            "sort_type": 0,
                            "subdraft_filter_type": 0,
                        }
                    ],
                },
                {"type": 1, "value": [{"child_id": m["id"], "parent_id": ""} for m in media]},
                {"type": 2, "value": []},
            ],
        },
    )

    dump(folder / "draft_content.json", content)
    dump(timeline / "draft_content.json", content)
    dump(
        folder / "timeline_layout.json",
        {
            "dockItems": [
                {
                    "dockIndex": 0,
                    "ratio": 1,
                    "timelineIds": [content["id"]],
                    "timelineNames": ["Timeline 01"],
                }
            ],
            "layoutOrientation": 1,
        },
    )
    meta = copy.deepcopy(template["meta"])
    for group in meta["draft_materials"]:
        if group["type"] == 0:
            group["value"] = media
    meta.update(
        draft_fold_path=posix(folder),
        draft_id=new_id(),
        draft_name=name,
        draft_root_path=str(root.resolve()),
        tm_draft_create=now_us,
        tm_draft_modified=now_us,
        tm_duration=content["duration"],
    )
    dump(folder / "draft_meta_info.json", meta)
    (folder / MARKER).write_text("Tạo bởi pipeline.capcut\n", encoding="utf-8")


def install_folder(root: Path, name: str) -> Path:
    """Thư mục đích trong CapCut: ghi đè draft cũ của pipeline, không đụng draft khác."""
    folder = root / name
    index = 2
    while folder.exists() and not (folder / MARKER).exists():
        folder = root / f"{name} ({index})"
        index += 1
    return folder


# ---------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.capcut",
        description="Xuất bộ file + draft để mở và chỉnh tiếp trong CapCut.",
    )
    parser.add_argument("--project-id")
    parser.add_argument("--format", choices=config.format_ids())
    parser.add_argument("--aspect", choices=config.aspect_ids())
    parser.add_argument("--name", help="Tên dự án trong CapCut (mặc định <id>-<format>-<aspect>)")
    parser.add_argument(
        "--learn-style",
        metavar="DRAFT",
        help="Học template phụ đề (hoạt ảnh) từ một dự án CapCut, giữ màu + font đã lưu",
    )
    parser.add_argument(
        "--plain",
        action="store_true",
        help="Với --learn-style: bỏ caption template, học phụ đề thường (luôn 1 dòng, không hiệu ứng)",
    )
    parser.add_argument(
        "--learn-look",
        metavar="DRAFT",
        help="Chỉ học màu + font phụ đề từ một dự án CapCut",
    )
    parser.add_argument("--skip-render", action="store_true", help="Dùng lại clip đã render")
    parser.add_argument("--no-install", action="store_true", help="Không ghi draft vào CapCut")
    parser.add_argument("--unapproved", action="store_true")
    args = parser.parse_args(argv)

    if args.learn_style:
        return learn_style(args.learn_style, plain=args.plain)
    if args.learn_look:
        return learn_style(args.learn_look, look_only=True)
    if not args.project_id:
        parser.error("cần --project-id (hoặc --learn-style / --learn-look)")

    pid = args.project_id
    fmt = args.format or paths.detect_format(pid)
    if not fmt:
        raise SystemExit(
            f"Không xác định được format: truyền --format {'|'.join(config.format_ids())}"
        )
    aspect_id = paths.resolve_aspect(pid, fmt, args.aspect)
    kit = paths.capcut_dir(pid, fmt, aspect_id)

    if not args.skip_render:
        # Dùng props hiện có (pipeline.make đã build); thiếu thì render tự build.
        code = render.main(
            ["--project-id", pid, "--format", fmt, "--aspect", aspect_id, "--capcut"]
            + (["--unapproved"] if args.unapproved else [])
        )
        if code != 0:
            return code

    props = json.loads(paths.props_path(pid, fmt, aspect_id).read_text(encoding="utf-8"))
    missing = [s["id"] for s in props["scenes"] if not (kit / "scenes" / f"{s['id']}.mp4").exists()]
    if missing:
        raise SystemExit(f"Thiếu clip {', '.join(missing)} trong {paths.rel(kit)}. Bỏ --skip-render.")

    collect_audio(props, kit)
    srt = paths.cards_dir(pid, fmt, aspect_id) / "captions.srt"
    if srt.exists():
        shutil.copy2(srt, kit / "captions.srt")

    name = args.name or f"{pid}-{fmt}-{aspect_id}"
    content = build_draft(props, kit)
    root = drafts_root()
    local = kit / "draft" / name
    write_draft(content, local, name, root or local.parent)

    ratio = config.aspect(aspect_id).get("ratio") or f"{props['width']}x{props['height']}"
    (kit / "README.txt").write_text(README.format(ratio=ratio, name=name), encoding="utf-8")

    print(f"\n✓ Bộ file CapCut: {paths.rel(kit)}")
    if args.no_install:
        print(f"  Draft (chưa cài): {paths.rel(local)}")
    elif root is None:
        print("  Không tìm thấy CapCut desktop; draft chỉ nằm trong bộ file.")
    else:
        target = install_folder(root, name)
        write_draft(content, target, target.name, root)
        print(f"  Draft CapCut: {target}")
        print("  Mở (hoặc khởi động lại) CapCut để thấy dự án trong danh sách.")
    paths.update_status(
        pid, capcut={f"{fmt}-{aspect_id}": {"dir": paths.rel(kit), "draft": name}}
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
