"""Mô tả chuyển động của từng cảnh + ghi chú animation của người duyệt.

Mô tả viết lại bằng lời những gì component Remotion làm (video/src/scenes,
video/src/visuals, components), để người duyệt đọc và ghi yêu cầu chỉnh. Khi đổi
chuyển động trong component, cập nhật bảng ở đây cho khớp.

Ghi chú lưu ở ``projects/<id>/review/animation-<format>.json`` ({sceneId: note}),
tách khỏi kịch bản nên ghi chú không làm mất phê duyệt. Agent ``motion-sfx`` đọc
file này khi được giao chỉnh animation.
"""

from __future__ import annotations

import json
from typing import Any

from . import config, paths

FPS = 30


def _sec(frames: int) -> str:
    return f"{frames / FPS:.1f}s".replace(".", ",")


# Trình tự xuất hiện theo loại cảnh (delay tính bằng frame, khớp component).
# Mọi phần tử "hiện" = mờ → rõ và nhích lên vài px trong ~0,5s.
SCENE_MOTION: dict[str, list[str]] = {
    "hook": [
        f"{_sec(0)} nhãn kicker hiện ở giữa",
        f"{_sec(3)} tiêu đề lớn hiện, từ nhấn đổi màu chính",
        f"{_sec(10)} gạch chân màu chính kéo dài từ giữa ra",
        f"{_sec(14)} dòng giới thiệu kênh hiện",
    ],
    "punch": [
        f"{_sec(0)} nhãn kicker hiện",
        f"{_sec(3)} câu chốt hiện, từ nhấn đổi màu chính",
        f"{_sec(10)} gạch chân kéo dài từ trái sang",
    ],
    "stat": [
        f"{_sec(0)} nhãn kicker hiện",
        f"{_sec(3)} con số đếm từ 0 lên giá trị thật trong ~0,9s",
        f"{_sec(9)} nhãn giải thích hiện",
        f"{_sec(13)} ghi chú nhỏ hiện",
    ],
    "list": [
        f"{_sec(0)} nhãn kicker hiện",
        f"{_sec(2)} tiêu đề hiện",
        f"{_sec(7)} từng ý hiện lần lượt, cách nhau {_sec(4)}",
    ],
    "chart": [
        f"{_sec(0)} nhãn kicker hiện",
        f"{_sec(2)} tiêu đề hiện",
        "các cột biểu đồ mọc từ đáy lên lần lượt (lò xo, không nảy)",
    ],
    "compare": [
        f"{_sec(0)} nhãn kicker hiện",
        f"{_sec(2)} tiêu đề hiện",
        f"{_sec(7)} từng thanh so sánh dài ra theo tỉ lệ trong ~0,7s, cách nhau {_sec(6)}",
        f"{_sec(20)} ghi chú hiện",
    ],
    "timeline": [
        f"{_sec(0)} nhãn kicker hiện",
        f"{_sec(2)} tiêu đề hiện",
        f"{_sec(6)} từng mốc thời gian hiện lần lượt, cách nhau {_sec(5)}; mốc đang nói được tô sáng",
    ],
    "outro": [
        f"{_sec(0)} nhãn kicker hiện ở giữa",
        f"{_sec(3)} lời kêu gọi hiện",
        f"{_sec(10)} gạch chân kéo dài",
        f"{_sec(14)} nút/handle kênh hiện",
    ],
}

# Chuyển động của hình minh hoạ (visual.kind).
VISUAL_MOTION: dict[str, str] = {
    "phone": "điện thoại có chip AI; chip phát sáng nhịp thở liên tục",
    "award": "thẻ bảng xếp hạng hiện lên, một mục được tô nổi bật",
    "loop": "hai nút hiện, hai cung vòng lặp được vẽ dần trong ~0,9s",
    "shrink": "các thanh dài ra tới tỉ lệ trong ~0,9s, thanh chính màu nổi",
    "decline": "đường biểu đồ được vẽ dần trong ~1,1s, vùng dưới đường hiện mờ dần, điểm cuối gắn nhãn",
    "storage": "hai thanh dung lượng; thanh 'sau khi nén' co lại theo % giảm trong ~1,2s",
    "limits": "các thanh tiến độ dài ra trong ~0,8s, phần còn thiếu ghi chú cần cloud",
    "question": "hai khung trượt vào từ hai bên (trái trước, phải sau ~0,1s), dấu hỏi ở giữa",
    "stick": "nhân vật que nhún nhẹ, tay vẫy/chỉ/viết theo pose, bong bóng thoại hiện",
}

TRANSITION_TEXT: dict[str, str] = {
    "none": "cắt thẳng",
    "fade": "mờ dần sang cảnh mới",
    "slide": "cảnh mới trượt vào từ phải, cảnh cũ lùi và tối đi",
    "push": "cảnh mới đẩy cảnh cũ sang trái",
    "wipe": "quét từ trái sang phải",
    "zoom": "cảnh mới thu nhỏ từ to về đúng cỡ và hiện rõ",
    "blur": "cảnh mới từ nhoè thành rõ",
}

BACKGROUND_TEXT: dict[str, str] = {
    "hero": "nền tối có quầng sáng mạnh, 'thở' chậm",
    "data": "nền tối lưới mờ, quầng sáng vừa",
    "calm": "nền tối dịu, quầng sáng nhẹ",
    "glitch": "nền tối có nhiễu kiểu glitch",
}


def describe_scene(
    scene: dict[str, Any],
    index: int,
    template: dict[str, Any],
) -> list[str]:
    """Các dòng mô tả chuyển động của một cảnh, theo thứ tự xảy ra."""
    lines: list[str] = []
    transition = template.get("transition") or {}
    if index == 0:
        lines.append("Mở đầu video: không có chuyển cảnh")
    else:
        kind = (transition.get("byType") or {}).get(scene["type"]) or transition.get("kind", "none")
        seconds = str(transition.get("sec", 0)).replace(".", ",")
        detail = TRANSITION_TEXT.get(kind, kind)
        lines.append(f"Chuyển cảnh vào: {kind} ({detail}, ~{seconds}s)")

    background = template.get("background") or {}
    if background.get("kind") == "tech":
        variant = (background.get("variants") or {}).get(scene["type"]) or background.get(
            "defaultVariant", "calm"
        )
        lines.append(f"Nền: {BACKGROUND_TEXT.get(variant, variant)}")
    elif background.get("kind"):
        lines.append(f"Nền: {background['kind']}")

    lines.extend(SCENE_MOTION.get(scene["type"], [f"cảnh '{scene['type']}' hiện theo mặc định"]))

    visual = (scene.get("visual") or {}).get("kind")
    if visual in VISUAL_MOTION:
        lines.append(f"Hình minh hoạ ({visual}): {VISUAL_MOTION[visual]}")

    sfx = scene.get("sfx")
    if sfx and sfx != "none":
        at = str(scene.get("sfxAtSec") or 0).replace(".", ",")
        lines.append(f"Âm thanh: '{sfx}' ở giây {at} của cảnh")

    lines.append("Phụ đề chạy theo giọng đọc, chữ đang đọc đổi màu")
    return lines


def describe(pid: str, fmt: str, script: dict[str, Any]) -> dict[str, list[str]]:
    template = config.template(paths.style_id(pid))
    return {
        scene["id"]: describe_scene(scene, index, template)
        for index, scene in enumerate(script["scenes"])
    }


# ---------------------------------------------------------------- ghi chú


def notes_path(pid: str, fmt: str):
    return paths.review_dir(pid) / f"animation-{fmt}.json"


def load_notes(pid: str, fmt: str) -> dict[str, str]:
    path = notes_path(pid, fmt)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(k): str(v) for k, v in (data.get("notes") or {}).items()}


def save_notes(pid: str, fmt: str, notes: dict[str, Any], scene_ids: list[str]) -> dict[str, str]:
    """Chỉ giữ ghi chú của cảnh có thật và không rỗng."""
    clean = {
        sid: str(notes[sid]).strip()
        for sid in scene_ids
        if sid in notes and str(notes[sid] or "").strip()
    }
    path = notes_path(pid, fmt)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"format": fmt, "notes": clean}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return clean
