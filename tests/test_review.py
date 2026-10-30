"""Cổng duyệt: phê duyệt gắn với hash nội dung script."""

from __future__ import annotations

import json

import pytest

from pipeline import paths, review


def edit_script(pid, mutate):
    path = paths.script_path(pid, "short")
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def approve(pid):
    paths.update_project(
        pid,
        review={
            "short": {
                "status": "approved",
                "scriptHash": paths.script_hash(pid, "short"),
                "approvedAt": "2026-01-01T00:00:00",
            }
        },
    )


def test_script_hash_ignores_key_order_and_whitespace(project):
    before = paths.script_hash(project, "short")
    path = paths.script_path(project, "short")
    data = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(
        json.dumps(dict(reversed(list(data.items()))), indent=4, ensure_ascii=False),
        encoding="utf-8",
    )
    assert paths.script_hash(project, "short") == before


def test_script_hash_changes_with_content(project):
    before = paths.script_hash(project, "short")
    edit_script(project, lambda d: d["scenes"][0].update(narration="khác hẳn"))
    assert paths.script_hash(project, "short") != before


def test_unapproved_script_is_blocked(project):
    assert "chưa được duyệt" in review.approval_problem(project, "short")
    with pytest.raises(SystemExit):
        review.require_approved(project, "short")


def test_bypass_lets_draft_runs_through(project, capsys):
    review.require_approved(project, "short", bypass=True)
    assert "--unapproved" in capsys.readouterr().out


def test_approved_script_passes(project):
    approve(project)
    assert review.approval_problem(project, "short") is None
    review.require_approved(project, "short")


def test_editing_after_approval_invalidates_it(project):
    approve(project)
    edit_script(project, lambda d: d["scenes"][0].update(narration="sửa sau khi duyệt"))
    assert "đã bị sửa sau khi duyệt" in review.approval_problem(project, "short")


def test_rejected_script_reports_the_reason(project):
    paths.update_project(
        project, review={"short": {"status": "rejected", "note": "hook yếu"}}
    )
    assert "hook yếu" in review.approval_problem(project, "short")


def test_factcheck_structure_errors():
    assert review.factcheck_errors({"items": [{"sceneId": "s01", "claim": "x", "verdict": "ok"}]}) == []
    assert review.factcheck_errors({}) == ["thiếu mảng 'items'"]
    errors = review.factcheck_errors({"items": [{"sceneId": "s01", "claim": "x", "verdict": "maybe"}]})
    assert any("verdict" in e for e in errors)


def test_verdict_counts_ignore_unknown_values():
    data = {"items": [{"verdict": "ok"}, {"verdict": "wrong"}, {"verdict": "ok"}, {"verdict": "?"}]}
    assert review.verdict_counts(data) == {"ok": 2, "doubtful": 0, "wrong": 1, "unsupported": 0}
    assert review.verdict_counts(None)["ok"] == 0


def test_approve_requires_factcheck_unless_skipped(project, capsys):
    state = review.collect(project, "short", links=False)
    code = review.approve(project, "short", state, note="", skip_factcheck=False, force=False)
    assert code == 1
    assert review.approval_problem(project, "short") is not None

    code = review.approve(project, "short", state, note="ok", skip_factcheck=True, force=False)
    assert code == 0
    assert review.approval_problem(project, "short") is None


def test_approve_blocks_wrong_verdict_unless_forced(project):
    factcheck = {
        "scriptHash": paths.script_hash(project, "short"),
        "items": [{"sceneId": "s01", "claim": "x", "verdict": "wrong"}],
    }
    target = paths.factcheck_path(project, "short")
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(factcheck), encoding="utf-8")

    state = review.collect(project, "short", links=False)
    assert review.approve(project, "short", state, note="", skip_factcheck=False, force=False) == 1
    assert review.approve(project, "short", state, note="đã kiểm tay", skip_factcheck=False, force=True) == 0
    assert approval_status(project)["factcheck"] == "forced"


def approval_status(pid):
    return review.approval(pid, "short")


def test_stale_factcheck_is_detected(project):
    factcheck = {"scriptHash": "0000", "items": []}
    target = paths.factcheck_path(project, "short")
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(factcheck), encoding="utf-8")
    state = review.collect(project, "short", links=False)
    assert state["factcheckStale"] is True


def test_report_lists_every_scene_and_factcheck_verdicts(project):
    factcheck = {
        "scriptHash": paths.script_hash(project, "short"),
        "items": [{"sceneId": "s04", "claim": "69%", "verdict": "doubtful", "fix": "ghi rõ nguồn"}],
    }
    target = paths.factcheck_path(project, "short")
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(factcheck), encoding="utf-8")
    state = review.collect(project, "short", links=False)
    report = review.render_report(project, "short", state)
    assert report.count("### s0") == 8
    assert "doubtful" in report and "ghi rõ nguồn" in report
