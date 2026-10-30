"""Kiểm tra template suy ra có giống video mẫu không (vòng khứ hồi).

Video mẫu và project của ta khác nội dung nên không so từng pixel được. Thay vào
đó: render project mẫu bằng template cần kiểm, chạy CHÍNH bộ đo đã dùng cho video
mẫu (``measure.measure_images``), rồi so các đại lượng đo được: màu, nền, vị trí và
cỡ phụ đề, chrome. Lệch ở đại lượng nào thì sửa đúng phần đó trong template.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .. import build, config, paths
from . import colors, measure, store, text

ROOT = config.ROOT
# Đại lượng màu: ΔE tối đa để coi là "giống".
COLOR_TOLERANCE = 14.0


def pick_frames(scenes: list[dict[str, Any]], fps: int, total_frames: int, limit: int) -> list[int]:
    """Frame giữa mỗi scene (đã có phụ đề), trải đều tối đa `limit` scene."""
    chosen = scenes
    if len(scenes) > limit:
        indexes = np.linspace(0, len(scenes) - 1, limit).round().astype(int)
        chosen = [scenes[i] for i in sorted(set(indexes.tolist()))]
    frames = []
    for scene in chosen:
        offset = min(1.8, scene["durationSec"] * 0.55)
        frames.append(min(total_frames - 1, max(0, round((scene["startSec"] + offset) * fps))))
    return frames


def render_stills(props_file: Path, public_dir: Path, outdir: Path, frames: list[int]) -> list[Path]:
    node = shutil.which("node")
    if not node:
        raise SystemExit("Không tìm thấy node trong PATH.")
    props = json.loads(props_file.read_text(encoding="utf-8"))
    # Cạnh ngắn ≈ 540px: đủ cho OCR mà vẫn nhanh, giống kích thước mẫu của video gốc.
    scale = round(min(1.0, 540 / min(props["width"], props["height"])), 4)
    outdir.mkdir(parents=True, exist_ok=True)
    command = [
        node,
        str(ROOT / "video" / "stills.mjs"),
        str(public_dir),
        "--props",
        str(props_file),
        "--outdir",
        str(outdir),
        "--frames",
        ",".join(str(f) for f in frames),
        "--scale",
        str(scale),
    ]
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        raise SystemExit(f"Render ảnh mẫu thất bại:\n{proc.stdout[-600:]}\n{proc.stderr[-600:]}")
    return [outdir / f"frame-{f:06d}.png" for f in frames]


# ---------------------------------------------------------------- so sánh


def _metric(name: str, ref: Any, ours: Any, ok: bool, weight: float = 1.0, note: str = "") -> dict[str, Any]:
    return {"name": name, "reference": ref, "ours": ours, "ok": ok, "weight": weight, "note": note}


def _color_metric(role: str, ref: str | None, ours: str | None, weight: float = 1.0) -> dict[str, Any]:
    if not ref or not ours:
        return _metric(f"màu {role}", ref, ours, False, weight, "thiếu dữ liệu")
    distance = colors.delta_e(colors.from_hex(ref), colors.from_hex(ours))
    return _metric(
        f"màu {role}", ref, ours, distance <= COLOR_TOLERANCE, weight, f"ΔE {distance:.1f}"
    )


def _accent_metric(ref: str, ours: str) -> dict[str, Any]:
    """Màu nhấn thứ hai chỉ xuất hiện ở vài scene: ít frame mẫu thì không đo được.

    Khi một bên không có màu rực nào thì không tính điểm (weight 0) để khỏi phạt oan.
    """
    # Cam tối sẫm thường là quầng sáng/bóng của màu nhấn, không phải chính màu nhấn.
    vivid = all(
        colors.saturation(colors.from_hex(c)) >= 0.35 and colors.luminance(colors.from_hex(c)) >= 0.12
        for c in (ref, ours)
    )
    metric = _color_metric("accent", ref, ours, 0.5)
    if not vivid:
        metric.update(ok=True, weight=0.0, note="không thấy màu nhấn trong các frame mẫu")
    return metric


def compare_measures(reference: dict[str, Any], ours: dict[str, Any]) -> dict[str, Any]:
    """So hai bộ số đo cùng cấu trúc (xem measure.measure_images)."""
    metrics: list[dict[str, Any]] = []
    for role, weight in (("bg", 2.0), ("fg", 1.5), ("primary", 1.5)):
        metrics.append(_color_metric(role, reference["palette"][role], ours["palette"][role], weight))
    metrics.append(_accent_metric(reference["palette"]["accent"], ours["palette"]["accent"]))

    ref_bg, our_bg = reference["background"], ours["background"]
    metrics.append(
        _metric("loại nền", ref_bg["kind"], our_bg["kind"], ref_bg["kind"] == our_bg["kind"], 1.0)
    )

    ref_cap, our_cap = reference.get("caption"), ours.get("caption")
    if ref_cap:
        if not our_cap:
            metrics.append(_metric("phụ đề", "có", "không thấy", False, 3.0))
        else:
            metrics += [
                _metric("đáy phụ đề (tỉ lệ cao)", ref_cap["bottomRel"], our_cap["bottomRel"],
                        abs(ref_cap["bottomRel"] - our_cap["bottomRel"]) <= 0.02, 2.0),
                _metric("cỡ chữ phụ đề (tỉ lệ cạnh ngắn)", ref_cap["fontSizeRel"], our_cap["fontSizeRel"],
                        abs(ref_cap["fontSizeRel"] / our_cap["fontSizeRel"] - 1) <= 0.15, 2.0),
                _metric("bề rộng phụ đề", ref_cap["maxWidthRel"], our_cap["maxWidthRel"],
                        abs(ref_cap["maxWidthRel"] - our_cap["maxWidthRel"]) <= 0.12, 1.0,
                        "phụ thuộc độ dài câu nên dung sai rộng"),
                _metric("chữ in hoa", ref_cap["uppercase"], our_cap["uppercase"],
                        ref_cap["uppercase"] == our_cap["uppercase"], 0.5),
                _metric("màu từ đang đọc", ref_cap["highlightColor"], our_cap["highlightColor"],
                        (ref_cap["highlightShare"] >= 0.3) == (our_cap["highlightShare"] >= 0.3), 1.0),
                _metric("thẻ nền phụ đề", ref_cap["cardShare"] >= 0.3, our_cap["cardShare"] >= 0.3,
                        (ref_cap["cardShare"] >= 0.3) == (our_cap["cardShare"] >= 0.3), 1.0),
                _metric("viền chữ", ref_cap["outlineShare"] >= 0.3, our_cap["outlineShare"] >= 0.3,
                        (ref_cap["outlineShare"] >= 0.3) == (our_cap["outlineShare"] >= 0.3), 1.0),
            ]
    for key, label in (("sceneIndex", "số scene"), ("watermark", "watermark")):
        ref_has = reference["chrome"].get(key) is not None
        our_has = ours["chrome"].get(key) is not None
        metrics.append(_metric(label, ref_has, our_has, ref_has == our_has, 0.5))

    total = sum(m["weight"] for m in metrics)
    earned = sum(m["weight"] for m in metrics if m["ok"])
    return {"score": round(100 * earned / total, 1) if total else 0.0, "metrics": metrics}


def run_compare(
    template_id: str,
    project_id: str,
    *,
    fmt: str | None = None,
    aspect: str | None = None,
    max_frames: int = 8,
    use_ocr: bool = True,
) -> dict[str, Any]:
    reference = store.load_analysis(template_id)
    fmt = fmt or paths.detect_format(project_id) or "short"
    aspect = aspect or reference["video"]["aspect"]

    built = build.compose(project_id, fmt, aspect, template_id)
    workdir = store.reference_dir(template_id) / "compare"
    workdir.mkdir(parents=True, exist_ok=True)
    props_file = workdir / "props.json"
    props_file.write_text(json.dumps(built.props, ensure_ascii=False), encoding="utf-8")

    props = built.props
    total_frames = round(props["totalSec"] * props["fps"])
    frames = pick_frames(props["scenes"], props["fps"], total_frames, max_frames)
    files = render_stills(props_file, paths.out_dir(project_id), workdir / "frames", frames)

    samples = [
        (frame / props["fps"], np.asarray(Image.open(path).convert("RGB"))) for frame, path in zip(frames, files)
    ]
    engine = text.OcrEngine() if use_ocr and text.ocr_available() else None
    ours = measure.measure_images(samples, engine=engine, max_ocr=len(samples))
    report = compare_measures(reference, ours)
    report.update({"template": template_id, "project": project_id, "aspect": aspect, "frames": frames})

    keyframes = sorted((store.reference_dir(template_id) / "frames").glob("kf-*.png"))[:6]
    ref_images = [np.asarray(Image.open(p).convert("RGB")) for p in keyframes]
    images = ref_images + [image for _, image in samples[:6]]
    labels = ["VIDEO MAU"] * len(ref_images) + ["TEMPLATE"] * len(samples[:6])
    if ref_images:
        store.contact_sheet(
            images, workdir / "compare_sheet.png", columns=max(1, len(ref_images)), labels=labels
        )
    (workdir / "compare.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
