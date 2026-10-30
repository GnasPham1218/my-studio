"""Fixture và helper dùng chung cho test.

Test không chạm vào ``projects/`` hay ``out/`` thật: mọi thứ dựng trong thư mục
tạm, nên chạy được trên CI mà không cần model, GPU hay dữ liệu dự án.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pipeline import paths


def make_script(project_id: str = "demo-project", fmt: str = "short") -> dict[str, Any]:
    """Kịch bản short tối thiểu nhưng hợp lệ với schema + luật format."""
    types = ["hook", "punch", "punch", "stat", "punch", "list", "punch", "outro"]
    scenes: list[dict[str, Any]] = []
    for index, scene_type in enumerate(types, start=1):
        scene: dict[str, Any] = {
            "id": f"s{index:02d}",
            "type": scene_type,
            "narration": "Một hai ba bốn năm sáu bảy tám chín mười",
            "onScreenText": "Tiêu đề ngắn",
        }
        if scene_type == "stat":
            scene["stat"] = {"value": "69", "unit": "%"}
            scene["claims"] = [{"text": "Giảm 69 phần trăm dung lượng", "source": 1}]
        if scene_type == "list":
            scene["bullets"] = ["một", "hai"]
        scenes.append(scene)
    return {
        "schemaVersion": 1,
        "format": fmt,
        "meta": {
            "projectId": project_id,
            "title": "Video thử",
            "language": "vi",
            "topic": "Chủ đề thử nghiệm",
            "sources": [{"title": "Nguồn một", "url": "https://example.com/a"}],
        },
        "scenes": scenes,
    }


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Project tạm: trỏ ``paths.PROJECTS``/``OUT`` vào thư mục tạm."""
    monkeypatch.setattr(paths, "PROJECTS", tmp_path / "projects")
    monkeypatch.setattr(paths, "OUT", tmp_path / "out")
    pid = "demo-project"
    script_file = paths.script_path(pid, "short")
    script_file.parent.mkdir(parents=True)
    script_file.write_text(
        json.dumps(make_script(pid), ensure_ascii=False), encoding="utf-8"
    )
    paths.project_config_path(pid).write_text(
        json.dumps({"projectId": pid, "style": "tech-explainer"}), encoding="utf-8"
    )
    return pid
