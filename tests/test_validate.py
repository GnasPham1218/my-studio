from __future__ import annotations

import copy

from pipeline import validate

from .conftest import make_script


def errors_for(script, fmt="short", project_id="demo-project"):
    return validate.validate(script, fmt=fmt, project_id=project_id)


def test_minimal_script_is_valid():
    assert errors_for(make_script()) == []


def test_wrong_project_id_is_reported():
    assert any("projectId" in e for e in errors_for(make_script("other")))


def test_first_scene_must_be_hook_for_short():
    script = make_script()
    script["scenes"][0]["type"] = "punch"
    assert any("scene đầu phải là 'hook'" in e for e in errors_for(script))


def test_scene_ids_must_be_sequential():
    script = make_script()
    script["scenes"][2]["id"] = "s09"
    assert any("id phải là 's03'" in e for e in errors_for(script))


def test_too_many_words_in_one_scene():
    script = make_script()
    script["scenes"][1]["narration"] = " ".join(["từ"] * 30)
    assert any("vượt giới hạn" in e for e in errors_for(script))


def test_too_few_scenes():
    script = make_script()
    script["scenes"] = script["scenes"][:3]
    script["scenes"][-1]["type"] = "outro"
    assert any("số scene" in e for e in errors_for(script))


def test_scene_type_not_allowed_for_format():
    script = make_script()
    script["scenes"][1]["type"] = "chapter"  # chỉ có ở long
    assert any("không được dùng cho short" in e for e in errors_for(script))


def test_bullet_limit_comes_from_format_rules():
    script = make_script()
    script["scenes"][5]["type"] = "bullets"
    script["scenes"][5]["bullets"] = ["a", "b", "c", "d"]
    assert any("bullet" in e for e in errors_for(script))
    script["scenes"][5]["bullets"] = ["a", "b", "c"]
    assert errors_for(script) == []


def test_stat_scene_needs_a_value():
    script = make_script()
    del script["scenes"][3]["stat"]
    assert any("stat.value" in e for e in errors_for(script))


def test_claim_must_point_to_an_existing_source():
    script = make_script()
    script["scenes"][3]["claims"][0]["source"] = 5
    assert any("meta.sources chỉ có 1 nguồn" in e for e in errors_for(script))


def test_unknown_visual_kind_is_rejected():
    script = make_script()
    script["scenes"][1]["visual"] = {"kind": "hologram"}
    assert any("hologram" in e for e in errors_for(script))


def test_visual_data_is_checked_against_catalog():
    script = make_script()
    script["scenes"][1]["visual"] = {"kind": "decline", "data": {"values": "x"}}
    assert any("visual.data" in e for e in errors_for(script))


def test_valid_visual_data_passes():
    script = make_script()
    script["scenes"][1]["visual"] = {
        "kind": "storage",
        "data": {"reductionPct": 50, "afterLabel": "8-bit"},
    }
    assert errors_for(script) == []


def test_removed_fastcut_type_is_rejected_by_schema():
    script = make_script()
    script["scenes"][1]["type"] = "fastCut"
    assert errors_for(script)


def test_validation_does_not_mutate_input():
    script = make_script()
    snapshot = copy.deepcopy(script)
    errors_for(script)
    assert script == snapshot


def test_claim_issues_flag_numbers_without_claims_but_ignore_handles():
    script = make_script()
    del script["scenes"][3]["claims"]
    script["scenes"][1]["onScreenText"] = "Theo dõi @DiveCode1218"
    issues = validate.claim_issues(script)
    assert any("[s04]" in i for i in issues)
    assert not any("[s02]" in i for i in issues)


def test_outro_never_needs_claims():
    script = make_script()
    script["scenes"][-1]["onScreenText"] = "Hẹn gặp lại 2026"
    assert not any("[s08]" in i for i in validate.claim_issues(script))


def test_content_visuals_require_their_own_data():
    script = make_script()
    script["scenes"][1]["visual"] = {"kind": "loop"}
    assert any("cần visual.data" in e for e in errors_for(script))
    script["scenes"][1]["visual"] = {
        "kind": "loop",
        "data": {"nodes": [{"title": "1", "sub": "x"}, {"title": "2", "sub": "y"}]},
    }
    assert errors_for(script) == []


def test_visuals_without_content_do_not_need_data():
    script = make_script()
    script["scenes"][1]["visual"] = {"kind": "phone", "label": "2020"}
    assert errors_for(script) == []
    script["scenes"][2]["visual"] = {"kind": "stick", "label": "hello", "pose": "wave"}
    assert errors_for(script) == []
