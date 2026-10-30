"""Giao diện duyệt: bản xem trước, lưu kịch bản, duyệt, và server HTTP thật."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from pipeline import motion, paths, preview, review, ui


def test_draft_props_estimate_timeline_without_audio(project):
    props = preview.draft_props(project, "short")
    assert props["silent"] is True
    assert "sfxDir" not in props  # bản xem trước không phát âm thanh
    scenes = props["scenes"]
    assert scenes[0]["startSec"] == 0
    for prev, nxt in zip(scenes, scenes[1:]):
        assert nxt["startSec"] == pytest.approx(prev["startSec"] + prev["durationSec"], abs=0.01)
    assert props["totalSec"] == pytest.approx(sum(s["durationSec"] for s in scenes), abs=0.01)
    assert props["captions"], "phụ đề vẫn có để xem trước"


def approve(pid):
    state = review.collect(pid, "short", links=False)
    assert review.approve(pid, "short", state, note="", skip_factcheck=True, force=False) == 0


def test_animation_locked_until_approved(project):
    with pytest.raises(ui.ApiError) as exc:
        ui.draft(project, "short", None)
    assert exc.value.status == 403
    approve(project)
    assert ui.draft(project, "short", None)["props"]["silent"] is True


def test_review_state_lists_sources(project):
    path = paths.script_path(project, "short")
    script = json.loads(path.read_text(encoding="utf-8"))
    script["meta"]["sources"] = [{"title": "Nguồn A", "url": "https://example.com/a"}]
    script["meta"]["assumptions"] = ["Số liệu ước tính"]
    path.write_text(json.dumps(script, ensure_ascii=False), encoding="utf-8")

    state = ui.review_state(project, "short")
    assert state["sources"] == [{"index": 1, "title": "Nguồn A", "url": "https://example.com/a"}]
    assert state["assumptions"] == ["Số liệu ước tính"]
    assert state["hasResearch"] is False


def test_checked_rejects_unknown_project_and_format(project):
    assert ui.checked(project, "short") == (project, "short")
    with pytest.raises(ui.ApiError):
        ui.checked("../config", "short")
    with pytest.raises(ui.ApiError):
        ui.checked(project, "huge")


def test_save_invalidates_previous_approval(project):
    approve(project)
    assert review.approval_problem(project, "short") is None

    script = json.loads(paths.script_path(project, "short").read_text(encoding="utf-8"))
    script["scenes"][1]["onScreenText"] = "Đã sửa sau khi duyệt"
    result = ui.save_script(project, "short", script)
    assert "đã bị sửa sau khi duyệt" in result["approvalProblem"]
    # Sửa xong là animation khoá lại cho tới khi duyệt lại.
    with pytest.raises(ui.ApiError):
        ui.draft(project, "short", None)


@pytest.fixture
def server(project):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), ui.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def request(url: str, body: dict | None = None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_http_review_flow(server, project):
    status, projects = request(f"{server}/api/projects")
    assert status == 200 and projects[0]["id"] == project

    status, state = request(f"{server}/api/review?project={project}&format=short")
    assert status == 200 and state["approvalProblem"]

    # Chưa duyệt: không dựng animation.
    status, result = request(f"{server}/api/preview", {"project": project, "format": "short"})
    assert status == 403

    # Kiểm lỗi bản đang sửa (chưa lưu).
    broken = {**state["script"], "scenes": state["script"]["scenes"][:1]}
    status, result = request(
        f"{server}/api/check", {"project": project, "format": "short", "script": broken}
    )
    assert status == 200 and result["errors"]

    status, result = request(
        f"{server}/api/approve",
        {"project": project, "format": "short", "note": "ok", "skipFactcheck": True},
    )
    assert status == 200 and result["ok"] and result["state"]["approvalProblem"] is None

    status, result = request(f"{server}/api/preview", {"project": project, "format": "short"})
    assert status == 200 and result["props"]["silent"]

    status, result = request(f"{server}/api/reject", {"project": project, "format": "short"})
    assert status == 400  # từ chối phải có lý do


def test_http_blocks_path_traversal(server):
    status, result = request(f"{server}/../../config/brand.json")
    assert status == 404
    status, result = request(f"{server}/api/review?project=..&format=short")
    assert status == 404


def test_motion_described_for_every_scene(project):
    state = ui.review_state(project, "short")
    scene_ids = [scene["id"] for scene in state["script"]["scenes"]]
    assert list(state["motion"]) == scene_ids
    first, second = state["motion"][scene_ids[0]], state["motion"][scene_ids[1]]
    assert first[0].startswith("Mở đầu video")
    assert second[0].startswith("Chuyển cảnh vào")
    assert any("hiện" in line for line in second)


def test_animation_notes_saved_apart_from_script(project):
    approve(project)
    before = paths.script_hash(project, "short")
    saved = motion.save_notes(
        project, "short", {"s01": "  số đếm chậm hơn  ", "s02": "", "s99": "không có cảnh này"},
        ["s01", "s02"],
    )
    assert saved == {"s01": "số đếm chậm hơn"}
    assert motion.load_notes(project, "short") == saved
    # Ghi chú không đụng kịch bản nên vẫn còn phê duyệt.
    assert paths.script_hash(project, "short") == before
    assert review.approval_problem(project, "short") is None


@pytest.mark.parametrize(
    ("output", "flags"),
    [("video", []), ("capcut", ["--capcut-only"]), ("both", ["--capcut"])],
)
def test_make_job_flags_per_output(project, monkeypatch, output, flags):
    started = {}
    monkeypatch.setattr(ui.JOBS, "start", lambda title, args: started.update(args=args) or {})
    ui.start_job({"kind": "make", "project": project, "format": "short", "output": output})
    args = started["args"]
    assert args[0] == "pipeline.make"
    assert [a for a in args if a.startswith("--capcut")] == flags


def test_make_job_rejects_unknown_output(project):
    with pytest.raises(ui.ApiError):
        ui.start_job({"kind": "make", "project": project, "format": "short", "output": "gif"})
