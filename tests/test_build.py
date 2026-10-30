"""build.py đầu-cuối trên dữ liệu giả: audio/timing tổng hợp, không cần model."""

from __future__ import annotations

import json

import pytest

from pipeline import build, paths, visuals

SCENE_SEC = 3.4


def write_audio_artifacts(pid: str, script: dict) -> float:
    """Ghi manifest + words.json giả khớp script, trả về tổng thời lượng."""
    manifest = {"scenes": {}}
    scenes = []
    cursor = 0.0
    for scene in script["scenes"]:
        manifest["scenes"][scene["id"]] = {"durationSec": SCENE_SEC, "hash": scene["id"]}
        tokens = scene["narration"].split()
        step = (SCENE_SEC - 0.4) / len(tokens)
        words = [
            {
                "w": token,
                "start": round(cursor + 0.15 + i * step, 3),
                "end": round(cursor + 0.15 + (i + 1) * step, 3),
            }
            for i, token in enumerate(tokens)
        ]
        scenes.append(
            {
                "id": scene["id"],
                "type": scene["type"],
                "start": round(cursor, 3),
                "end": round(cursor + SCENE_SEC, 3),
                "words": words,
            }
        )
        cursor += SCENE_SEC
    manifest["totalSec"] = round(cursor, 2)

    paths.manifest_path(pid, "short").parent.mkdir(parents=True, exist_ok=True)
    paths.manifest_path(pid, "short").write_text(json.dumps(manifest), encoding="utf-8")
    paths.words_path(pid, "short").parent.mkdir(parents=True, exist_ok=True)
    paths.words_path(pid, "short").write_text(
        json.dumps({"totalSec": round(cursor, 3), "scenes": scenes}), encoding="utf-8"
    )
    return cursor


@pytest.fixture
def built_inputs(project):
    script = json.loads(paths.script_path(project, "short").read_text(encoding="utf-8"))
    script["scenes"][1]["visual"] = {"kind": "storage", "data": {"reductionPct": 40}}
    paths.script_path(project, "short").write_text(
        json.dumps(script, ensure_ascii=False), encoding="utf-8"
    )
    total = write_audio_artifacts(project, script)
    return project, total


def run_build(pid: str, aspect: str | None = None) -> dict:
    args = ["--project-id", pid, "--format", "short", "--unapproved"]
    if aspect:
        args += ["--aspect", aspect]
    assert build.main(args) == 0
    aspect_id = paths.resolve_aspect(pid, "short", aspect)
    return json.loads(paths.props_path(pid, "short", aspect_id).read_text(encoding="utf-8"))


def test_build_writes_layout_and_template_for_the_chosen_aspect(built_inputs):
    pid, total = built_inputs
    props = run_build(pid, "horizontal")
    assert props["aspect"] == "horizontal"
    assert (props["width"], props["height"]) == (1920, 1080)
    assert props["layout"]["aspect"] == "horizontal"
    assert props["layout"]["caption"]["maxChars"] == 84
    assert props["template"]["id"] == "tech-explainer"
    assert props["totalSec"] == pytest.approx(total, abs=0.01)
    assert "safeArea" not in props and "styleId" not in props


def test_default_aspect_follows_format(built_inputs):
    pid, _ = built_inputs
    assert run_build(pid)["aspect"] == "vertical"


def test_project_aspect_overrides_format_default(built_inputs):
    pid, _ = built_inputs
    paths.update_project(pid, aspect="square")
    assert run_build(pid)["aspect"] == "square"
    assert run_build(pid, "vertical")["aspect"] == "vertical"  # CLI thắng project.json


def test_visual_defaults_are_merged_into_props(built_inputs):
    pid, _ = built_inputs
    visual = run_build(pid)["scenes"][1]["visual"]
    assert visual["data"]["reductionPct"] == 40  # giá trị người viết
    assert visual["data"]["title"] == visuals.defaults("storage")["title"]  # default từ catalog


def test_each_aspect_gets_its_own_files(built_inputs):
    pid, _ = built_inputs
    run_build(pid, "vertical")
    run_build(pid, "square")
    for aspect in ("vertical", "square"):
        assert paths.props_path(pid, "short", aspect).exists()
        assert (paths.cards_dir(pid, "short", aspect) / "captions.srt").exists()
        assert (paths.cards_dir(pid, "short", aspect) / "captions.ass").exists()


def test_card_splitting_depends_on_aspect(built_inputs):
    pid, _ = built_inputs
    scene_words = {w["w"] for w in run_build(pid, "vertical")["scenes"][0]["words"]}
    assert scene_words  # có từ
    narrow = len(run_build(pid, "vertical")["captions"])
    wide = len(run_build(pid, "horizontal")["captions"])
    assert wide <= narrow


def test_template_color_override_reaches_brand(built_inputs):
    pid, _ = built_inputs
    paths.update_project(pid, style="whiteboard")
    props = run_build(pid)
    assert props["template"]["background"]["kind"] == "paper"
    assert props["template"]["caption"]["holdGapSec"] == 0.85


def test_build_refuses_unapproved_script_without_flag(built_inputs):
    pid, _ = built_inputs
    with pytest.raises(SystemExit):
        build.main(["--project-id", pid, "--format", "short"])


def test_timing_mismatch_is_reported(built_inputs):
    pid, _ = built_inputs
    words = json.loads(paths.words_path(pid, "short").read_text(encoding="utf-8"))
    words["scenes"][2]["start"] += 1.0
    paths.words_path(pid, "short").write_text(json.dumps(words), encoding="utf-8")
    with pytest.raises(SystemExit, match="Lệch timeline"):
        run_build(pid)
