"""Từ số đo (``analysis``) suy ra template theo schemas/template.schema.json.

Hàm thuần, chỉ làm việc trên dict: sửa quy tắc suy luận ở đây rồi chạy lại
``pipeline.analyze infer`` mà không cần đọc lại video hay chạy lại OCR.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .. import config
from . import colors, frames

# Một đặc điểm chỉ được ghi vào template khi xuất hiện ở ít nhất từng này số frame caption.
FEATURE_MIN_SHARE = 0.3


def _different(a: str | None, b: str | None, threshold: float = 12.0) -> bool:
    if not a or not b:
        return False
    return colors.delta_e(colors.from_hex(a), colors.from_hex(b)) > threshold


def infer_background(measure: dict[str, Any], notes: list[str]) -> dict[str, Any]:
    bg = measure["background"]
    if bg["kind"] == "glow":
        notes.append(
            "Nền có quầng sáng cục bộ: dùng nền 'tech' có sẵn (nền tối + quầng sáng + lưới). "
            "Nếu video mẫu khác hẳn, đổi background.kind sang solid/gradient/paper."
        )
        return {"kind": "tech"}
    if bg["kind"] == "gradient" and bg.get("stops"):
        return {
            "kind": "gradient",
            "gradient": {"angle": bg["angle"] or 180, "stops": bg["stops"]},
        }
    return {"kind": "solid"}


def infer_caption(measure: dict[str, Any], palette: dict[str, str], notes: list[str]) -> dict[str, Any]:
    cap = measure.get("caption")
    if not cap:
        notes.append(
            "Không tìm thấy phụ đề trong video (hoặc chưa chạy OCR): caption dùng mặc định "
            "của _base.json. Cài OCR: uv pip install -r requirements-analyze.txt"
        )
        return {}

    result: dict[str, Any] = {
        "uppercase": bool(cap["uppercase"]),
        "fontSizeRel": cap["fontSizeRel"],
        "bottomRel": cap["bottomRel"],
        "maxWidthRel": cap["maxWidthRel"],
    }
    if _different(cap.get("textColor"), palette["fg"]):
        result["textColor"] = cap["textColor"]

    highlight = cap["highlightColor"] if cap["highlightShare"] >= FEATURE_MIN_SHARE else None
    result["highlight"] = {"color": highlight, "underline": None}

    outlined = cap["outlineColor"] and cap["outlineShare"] >= FEATURE_MIN_SHARE
    if outlined:
        px = max(2, round(cap["fontSizeRel"] * 1080 * 0.07))
        result["stroke"] = {"px": px, "color": cap["outlineColor"]}

    carded = cap["cardColor"] and cap["cardShare"] >= FEATURE_MIN_SHARE
    if carded:
        result["card"] = {
            "background": cap["cardColor"],
            "backgroundAlpha": 1,
            "borderAlpha": 0,
            "radius": 12,
        }
        notes.append("Phát hiện thẻ nền sau phụ đề; viền thẻ và bo góc để mặc định, hãy xem lại.")
    result["textShadow"] = not (outlined or carded)
    if cap["scrimShare"] < 0.5:
        result["scrim"] = []
    if cap["confidence"] < 0.5:
        notes.append(
            f"Độ tin cậy phụ đề thấp ({cap['confidence']}): chỉ thấy phụ đề ở "
            f"{cap['presence']:.0%} số frame."
        )
    return result


def infer_chrome(measure: dict[str, Any], notes: list[str]) -> dict[str, Any]:
    chrome = measure.get("chrome") or {}
    watermark = chrome.get("watermark")
    scene_index = chrome.get("sceneIndex")
    result: dict[str, Any] = {
        "sceneIndex": scene_index is not None,
        "progress": False,
        "watermark": {"enabled": watermark is not None},
    }
    if watermark is not None:
        result["watermark"]["uppercase"] = bool(watermark["uppercase"])
        if watermark["x"] < 0.35:
            notes.append(
                "Watermark của video mẫu nằm bên trái; layout hiện đặt watermark ở góc phải "
                "(config/aspects.json → chrome.watermark)."
            )
    if scene_index is not None and scene_index["x"] > 0.5:
        notes.append("Số scene của video mẫu nằm bên phải; layout đặt ở góc trái.")
    return result


def infer_template(
    measure: dict[str, Any],
    template_id: str,
    *,
    source_name: str,
    now: datetime | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Trả về (template, ghi chú cần người xem lại). Template đã kiểm schema."""
    notes: list[str] = [
        "Font không nhận diện được từ video: template dùng font của brand. Nếu cần đổi, "
        "thêm @fontsource/<tên> (video/src/index.ts) rồi điền template.fonts.",
        "Cỡ chữ tiêu đề và bố cục từng scene lấy theo config/aspects.json, không sao chép "
        "từ video mẫu.",
    ]
    # Chọn lại từ nguyên liệu nếu có: sửa pick_palette rồi `infer` không cần đọc lại video.
    palette = (
        frames.palette_from_sources(measure["colorSources"])
        if "colorSources" in measure
        else measure["palette"]
    )
    measure = {**measure, "palette": palette}
    video = measure["video"]
    template: dict[str, Any] = {
        "schemaVersion": 1,
        "id": template_id,
        "label": template_id.replace("-", " ").title(),
        "description": f"Suy ra tự động từ video mẫu {source_name}.",
        "colors": dict(palette),
        "background": infer_background(measure, notes),
        "caption": infer_caption(measure, palette, notes),
        "chrome": infer_chrome(measure, notes),
        "pacing": measure.get("pacing") or {},
        "audio": {
            key: measure["audio"].get(key)
            for key in ("loudnessDbfs", "hasMusicBed", "tempoBpm")
        },
        "source": {
            "file": source_name,
            "analyzedAt": (now or datetime.now()).isoformat(timespec="seconds"),
            "aspect": video["aspect"],
            "resolution": [video["width"], video["height"]],
            "fps": video["fps"],
            "ocrUsed": measure.get("ocrUsed", False),
            "captionConfidence": (measure.get("caption") or {}).get("confidence"),
        },
    }
    if measure["background"]["kind"] == "gradient":
        notes.append(
            f"Nền được xấp xỉ bằng gradient {measure['background']['angle']}° "
            "(có thể là nền có quầng sáng/hoạ tiết); xem contact_sheet.png để xác nhận."
        )
    if measure["audio"].get("hasMusicBed"):
        notes.append(
            "Video mẫu có dấu hiệu nhạc nền (sàn nhiễu cao). Bật brand.music nếu muốn "
            "nhạc nền; template không điều khiển âm thanh."
        )

    errors = config.template_errors(template)
    if errors:
        raise ValueError("Template suy ra không hợp lệ (lỗi code):\n  - " + "\n  - ".join(errors))
    return template, notes
