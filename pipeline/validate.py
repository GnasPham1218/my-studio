from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schemas" / "script.schema.json"
FORMATS_PATH = ROOT / "config" / "formats.json"

SCHEMA: dict[str, Any] = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
FORMATS: dict[str, Any] = json.loads(FORMATS_PATH.read_text(encoding="utf-8"))
WORDS_PER_SECOND: float = FORMATS["wordsPerSecond"]

# Scene trình bày số liệu: luôn phải có claim kèm nguồn.
FACT_SCENE_TYPES = {"stat", "chart", "compare", "timeline"}
_DIGIT = re.compile(r"\d")
# Handle kênh (@DiveCode1218) chứa số nhưng không phải dữ kiện.
_HANDLE = re.compile(r"@\S+")


def _words(text: str) -> int:
    return len(text.split())


def _scene_text(scene: dict[str, Any]) -> str:
    """Text dùng để đếm từ: ưu tiên segments nếu có."""
    segments = scene.get("segments") or []
    if segments:
        return " ".join(str(segment.get("text", "")) for segment in segments)
    return str(scene.get("narration", ""))


def _scene_seconds(scene: dict[str, Any]) -> float:
    explicit = scene.get("durationTargetSec")
    if isinstance(explicit, (int, float)) and explicit > 0:
        return float(explicit)
    return _words(_scene_text(scene)) / WORDS_PER_SECOND


def _structural(script: dict[str, Any]) -> list[str]:
    try:
        import jsonschema
    except ImportError:
        return [
            "[schema] thiếu package 'jsonschema'. Chạy: pip install -r requirements.txt"
        ]

    validator = jsonschema.Draft202012Validator(SCHEMA)
    errors: list[str] = []
    for err in sorted(validator.iter_errors(script), key=lambda e: list(e.path)):
        path = "/".join(str(p) for p in err.path) or "<root>"
        errors.append(f"[schema] {path}: {err.message}")
    return errors


def validate(
    script: dict[str, Any],
    *,
    fmt: str,
    project_id: str | None = None,
) -> list[str]:
    """Trả về danh sách lỗi. Rỗng = hợp lệ."""
    if fmt not in FORMATS["formats"]:
        return [f"[config] format không hợp lệ: {fmt!r}"]

    errors = _structural(script)
    if errors:
        # Lỗi cấu trúc có thể làm các kiểm tra dưới đây crash; dừng sớm.
        return errors

    cfg = FORMATS["formats"][fmt]
    meta = script.get("meta") or {}
    scenes: list[dict[str, Any]] = script.get("scenes") or []

    if script.get("format") != fmt:
        errors.append(
            f"[format] script.format='{script.get('format')}' nhưng yêu cầu '{fmt}'"
        )

    if project_id and meta.get("projectId") != project_id:
        errors.append(
            f"[meta] projectId='{meta.get('projectId')}' khác yêu cầu '{project_id}'"
        )

    sources = meta.get("sources") or []
    if len(sources) < 1:
        errors.append("[meta] sources rỗng: phải trích ít nhất 1 nguồn từ research")

    allowed = set(cfg["sceneTypes"])

    # id: đúng mẫu, không trùng, liên tục
    seen: set[str] = set()
    for index, scene in enumerate(scenes, start=1):
        sid = scene.get("id", "?")
        if sid in seen:
            errors.append(f"[{sid}] id bị trùng")
        seen.add(sid)
        if sid != f"s{index:02d}":
            errors.append(f"[{sid}] id phải là 's{index:02d}' theo thứ tự")

    if scenes:
        first = scenes[0].get("type")
        if first != cfg["firstSceneType"]:
            errors.append(
                f"[{scenes[0].get('id')}] scene đầu phải là '{cfg['firstSceneType']}', "
                f"không phải '{first}'"
            )

    present = {scene.get("type") for scene in scenes}
    for required in cfg.get("requiredSceneTypes", []):
        if required not in present:
            errors.append(f"[format] thiếu scene bắt buộc: '{required}'")

    if "minChapterScenes" in cfg:
        chapter_count = sum(1 for s in scenes if s.get("type") == "chapter")
        if chapter_count < cfg["minChapterScenes"]:
            errors.append(
                f"[format] cần ít nhất {cfg['minChapterScenes']} scene 'chapter', "
                f"hiện có {chapter_count}"
            )

    min_scenes, max_scenes = cfg["sceneCount"]
    if not (min_scenes <= len(scenes) <= max_scenes):
        errors.append(
            f"[format] số scene phải trong khoảng {min_scenes}–{max_scenes}, "
            f"hiện có {len(scenes)}"
        )

    min_word_limit = cfg["maxWordsPerScene"]
    scene_min, scene_max = cfg["sceneDurationSec"]

    for scene in scenes:
        sid = scene.get("id", "?")
        stype = scene.get("type")
        if stype not in allowed:
            errors.append(
                f"[{sid}] type '{stype}' không được dùng cho {fmt}. "
                f"Chỉ dùng: {', '.join(sorted(allowed))}"
            )

        narration = _scene_text(scene)
        words = _words(narration)
        if words > min_word_limit:
            errors.append(
                f"[{sid}] narration {words} từ, vượt giới hạn {min_word_limit} từ của {fmt}"
            )

        seconds = _scene_seconds(scene)
        if seconds < scene_min * 0.8 or seconds > scene_max * 1.2:
            errors.append(
                f"[{sid}] thời lượng ~{seconds:.1f}s nằm ngoài khoảng "
                f"{scene_min}–{scene_max}s của {fmt}"
            )

        if stype == "bullets":
            bullets = scene.get("bullets") or []
            if not bullets:
                errors.append(f"[{sid}] scene 'bullets' phải có mảng bullets")
            elif len(bullets) > cfg["typography"]["maxLines"]:
                errors.append(
                    f"[{sid}] có {len(bullets)} bullet, tối đa "
                    f"{cfg['typography']['maxLines']} dòng"
                )

        if stype == "chart" and (scene.get("visual") or {}).get("kind") != "chart":
            errors.append(f"[{sid}] scene 'chart' phải có visual.kind='chart'")

        if stype == "stat" and not (scene.get("stat") or {}).get("value"):
            errors.append(f"[{sid}] scene 'stat' phải có stat.value")

        if stype == "timeline" and not scene.get("timeline"):
            errors.append(f"[{sid}] scene 'timeline' phải có mảng timeline")

        if stype == "compare" and not (scene.get("compare") or {}).get("items"):
            errors.append(f"[{sid}] scene 'compare' phải có compare.items")

        for claim in scene.get("claims") or []:
            if claim["source"] > len(sources):
                errors.append(
                    f"[{sid}] claim trỏ tới nguồn {claim['source']} nhưng "
                    f"meta.sources chỉ có {len(sources)} nguồn"
                )

    total = sum(_scene_seconds(scene) for scene in scenes)
    target_min, target_max = cfg["targetDurationSec"]
    if not (target_min * 0.9 <= total <= target_max * 1.1):
        errors.append(
            f"[format] tổng thời lượng ~{total:.0f}s nằm ngoài khoảng "
            f"{target_min}–{target_max}s của {fmt}"
        )

    return errors


def needs_claims(scene: dict[str, Any]) -> bool:
    """Scene có số liệu hiển thị (hoặc là scene số liệu) thì nên có claim.

    Heuristic theo chữ số nên có thể bắt nhầm ("3 mẹo"); kicker là nhãn
    ("English in 30 seconds") nên không xét.
    """
    if scene.get("type") == "outro":
        return False
    if scene.get("type") in FACT_SCENE_TYPES:
        return True
    texts = [scene.get("onScreenText") or "", *(scene.get("bullets") or [])]
    return any(_DIGIT.search(_HANDLE.sub("", text)) for text in texts)


def claim_issues(script: dict[str, Any]) -> list[str]:
    """Scene có số liệu nhưng chưa khai báo claim + nguồn.

    Chỉ là cảnh báo (in khi viết script và trong báo cáo review), không chặn
    duyệt. Agent factchecker vẫn kiểm mọi khẳng định dù có claim hay không.
    """
    return [
        f"[{scene.get('id', '?')}] có số liệu nhưng thiếu 'claims' "
        "(mỗi khẳng định kèm số thứ tự nguồn trong meta.sources)"
        for scene in script.get("scenes") or []
        if needs_claims(scene) and not scene.get("claims")
    ]


def as_repair_prompt(errors: list[str]) -> str:
    lines = ["Kịch bản JSON vừa trả về KHÔNG hợp lệ. Dưới đây là danh sách lỗi:", ""]
    lines += [f"{i}. {err}" for i, err in enumerate(errors, start=1)]
    lines += [
        "",
        "Hãy sửa TẤT CẢ lỗi trên và trả về lại TOÀN BỘ object JSON hợp lệ.",
        "Không giải thích, không markdown, không code fence.",
    ]
    return "\n".join(lines)
