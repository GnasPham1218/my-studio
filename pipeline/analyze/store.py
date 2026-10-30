"""Nơi lưu kết quả phân tích: ``references/<id>/`` (không commit, sinh lại được)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .. import config

REFERENCES = config.ROOT / "references"


def reference_dir(template_id: str) -> Path:
    return REFERENCES / template_id


def analysis_path(template_id: str) -> Path:
    return reference_dir(template_id) / "analysis.json"


def contact_sheet_path(template_id: str) -> Path:
    return reference_dir(template_id) / "contact_sheet.png"


def save_analysis(template_id: str, analysis: dict[str, Any]) -> Path:
    path = analysis_path(template_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_analysis(template_id: str) -> dict[str, Any]:
    path = analysis_path(template_id)
    if not path.exists():
        raise SystemExit(
            f"Chưa có phân tích cho '{template_id}'. Chạy: "
            f"python -m pipeline.analyze run <video> --id {template_id}"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def contact_sheet(
    images: list[np.ndarray],
    path: Path,
    *,
    columns: int = 6,
    cell_width: int = 240,
    labels: list[str] | None = None,
) -> Path:
    """Lưới ảnh nhỏ để xem nhanh (người hoặc agent có khả năng đọc ảnh)."""
    from PIL import ImageDraw

    if not images:
        raise ValueError("Không có ảnh để ghép")
    thumbs = []
    for image in images:
        pil = Image.fromarray(image)
        scale = cell_width / pil.width
        thumbs.append(pil.resize((cell_width, max(1, int(pil.height * scale)))))
    cell_height = max(t.height for t in thumbs)
    rows = (len(thumbs) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_width, rows * cell_height), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    for index, thumb in enumerate(thumbs):
        x, y = (index % columns) * cell_width, (index // columns) * cell_height
        sheet.paste(thumb, (x, y))
        if labels:
            draw.text((x + 4, y + 4), labels[index], fill=(255, 220, 0))
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    return path
