from __future__ import annotations

import copy

import pytest

from pipeline import config
from pipeline.analyze import compare, infer, measure


def fake_measure(**overrides):
    base = {
        "video": {
            "file": "mau.mp4", "width": 1080, "height": 1920, "fps": 30.0,
            "durationSec": 57.0, "aspect": "vertical", "hasAudio": True,
        },
        "cuts": [4.0, 9.0],
        "pacing": {"durationSec": 57.0, "avgSceneSec": 4.4, "medianSceneSec": 4.3, "cutsPerMinute": 12.6},
        "background": {"kind": "solid", "color": "#070B12", "angle": None, "stops": None, "spread": 1.0},
        "palette": {
            "bg": "#070B12", "surface": "#101827", "fg": "#F4F7FB",
            "muted": "#8A97AB", "primary": "#22D3EE", "accent": "#F59E0B",
        },
        "caption": {
            "bottom": 0.844, "bottomRel": 0.156, "fontSizeRel": 0.049, "maxWidthRel": 0.85,
            "uppercase": False, "linesPerCard": 1.6, "presence": 0.8, "change": 0.6, "confidence": 0.9,
            "framesAnalyzed": 40, "textColor": "#F2F5FA",
            "highlightColor": "#22D3EE", "highlightShare": 0.4,
            "outlineColor": None, "outlineShare": 0.0,
            "cardColor": None, "cardShare": 0.0, "scrimShare": 0.9,
        },
        "chrome": {"watermark": {"x": 0.85, "y": 0.07, "text": "DIVE", "uppercase": True, "presence": 1.0},
                   "sceneIndex": {"x": 0.08, "y": 0.07}},
        "audio": {"loudnessDbfs": -14.0, "floorDbfs": -70.0, "hasMusicBed": False, "tempoBpm": None},
        "ocrUsed": True,
    }
    base = copy.deepcopy(base)
    for key, value in overrides.items():
        base[key] = value
    return base


def infer_for(**overrides):
    return infer.infer_template(fake_measure(**overrides), "mau-thu", source_name="mau.mp4")


def test_inferred_template_is_valid_and_resolvable():
    template, _ = infer_for()
    assert config.template_errors(template) == []
    assert template["id"] == "mau-thu"
    assert template["colors"]["primary"] == "#22D3EE"
    assert template["caption"]["bottomRel"] == 0.156
    assert template["source"]["aspect"] == "vertical"


def test_flat_background_becomes_solid_and_gradient_keeps_angle_and_stops():
    solid, _ = infer_for()
    assert solid["background"] == {"kind": "solid"}
    gradient, notes = infer_for(
        background={"kind": "gradient", "color": "#070B12", "angle": 180,
                    "stops": ["#05060A", "#101827"], "spread": 14.0}
    )
    assert gradient["background"]["kind"] == "gradient"
    assert gradient["background"]["gradient"] == {"angle": 180, "stops": ["#05060A", "#101827"]}
    assert any("gradient" in n for n in notes)


def test_rare_features_are_not_written_to_the_template():
    caption = fake_measure()["caption"]
    caption.update(outlineColor="#000000", outlineShare=0.05, cardColor="#202020", cardShare=0.1,
                   highlightShare=0.05)
    template, _ = infer_for(caption=caption)
    assert "stroke" not in template["caption"]
    assert "card" not in template["caption"]
    assert template["caption"]["highlight"]["color"] is None


def test_outline_and_card_replace_text_shadow():
    caption = fake_measure()["caption"]
    caption.update(outlineColor="#000000", outlineShare=0.8)
    outlined, _ = infer_for(caption=caption)
    assert outlined["caption"]["stroke"]["color"] == "#000000"
    assert outlined["caption"]["textShadow"] is False

    caption.update(outlineColor=None, outlineShare=0.0, cardColor="#202020", cardShare=0.9)
    carded, notes = infer_for(caption=caption)
    assert carded["caption"]["card"]["background"] == "#202020"
    assert carded["caption"]["card"]["borderAlpha"] == 0
    assert any("thẻ nền" in n for n in notes)


def test_scrim_is_removed_when_not_seen():
    caption = fake_measure()["caption"]
    caption["scrimShare"] = 0.1
    template, _ = infer_for(caption=caption)
    assert template["caption"]["scrim"] == []


def test_missing_caption_falls_back_to_defaults_with_a_warning():
    template, notes = infer_for(caption=None, ocrUsed=False)
    assert "fontSizeRel" not in template["caption"]
    assert any("OCR" in n for n in notes)


def test_chrome_flags_follow_detection_and_warn_about_side():
    template, notes = infer_for()
    assert template["chrome"]["sceneIndex"] is True
    assert template["chrome"]["watermark"] == {"enabled": True, "uppercase": True}

    left = {"watermark": {"x": 0.1, "y": 0.07, "text": "X", "uppercase": False, "presence": 1},
            "sceneIndex": None}
    template, notes = infer_for(chrome=left)
    assert template["chrome"]["sceneIndex"] is False
    assert any("bên trái" in n for n in notes)


def test_palette_is_repicked_from_sources_when_present():
    sources = {
        "background": "#070B12",
        "ink": [["#F4F7FB", 0.6]],
        "vivid": [["#FF3366", 0.002]],
        "clusters": [["#070B12", 0.9]],
    }
    template, _ = infer_for(colorSources=sources)
    assert template["colors"]["primary"] == "#FF3366"  # lấy từ nguyên liệu, không từ palette cũ


def test_music_bed_adds_a_note():
    audio = fake_measure()["audio"]
    audio["hasMusicBed"] = True
    _, notes = infer_for(audio=audio)
    assert any("nhạc nền" in n for n in notes)


def test_aspect_for_picks_closest_ratio():
    assert measure.aspect_for(1080, 1920) == "vertical"
    assert measure.aspect_for(1920, 1080) == "horizontal"
    assert measure.aspect_for(1080, 1080) == "square"
    assert measure.aspect_for(1080, 1350) == "square"  # 4:5 gần 1:1 hơn 9:16


# ---------------------------------------------------------------- compare


def test_identical_measures_score_100():
    report = compare.compare_measures(fake_measure(), fake_measure())
    assert report["score"] == 100.0
    assert all(m["ok"] for m in report["metrics"])


def test_wrong_colors_and_caption_position_lower_the_score():
    ours = fake_measure()
    ours["palette"]["primary"] = "#FF0000"
    ours["caption"]["bottomRel"] = 0.30
    report = compare.compare_measures(fake_measure(), ours)
    failed = {m["name"] for m in report["metrics"] if not m["ok"]}
    assert {"màu primary", "đáy phụ đề (tỉ lệ cao)"} <= failed
    assert report["score"] < 90


def test_missing_caption_in_render_is_a_heavy_miss():
    ours = fake_measure(caption=None)
    report = compare.compare_measures(fake_measure(), ours)
    assert any(m["name"] == "phụ đề" and not m["ok"] for m in report["metrics"])


def test_pick_frames_spreads_over_scenes_and_stays_in_range():
    scenes = [{"startSec": i * 4.0, "durationSec": 4.0} for i in range(12)]
    picks = compare.pick_frames(scenes, 30, 12 * 4 * 30, 5)
    assert len(picks) == 5
    assert picks == sorted(picks)
    assert all(0 <= p < 12 * 4 * 30 for p in picks)
    assert compare.pick_frames(scenes[:2], 30, 240, 5) == [round(1.8 * 30), round((4.0 + 1.8) * 30)]


def test_pick_frames_clamps_to_last_frame():
    assert compare.pick_frames([{"startSec": 9.9, "durationSec": 0.2}], 30, 300, 3) == [299]


@pytest.mark.parametrize("bad", ["Ab", "1abc", "has space", "-x"])
def test_template_id_pattern_rejects_bad_ids(bad):
    errors = config.template_errors({"schemaVersion": 1, "id": bad})
    assert errors


def test_glow_background_maps_to_the_builtin_tech_background():
    glow = {"kind": "glow", "color": "#070B12", "angle": None, "stops": None,
            "spread": 10.0, "residual": 0.3}
    template, notes = infer_for(background=glow)
    assert template["background"] == {"kind": "tech"}
    assert any("tech" in n for n in notes)
    assert config.template_errors(template) == []


def test_missing_accent_in_render_is_not_penalised():
    ours = fake_measure()
    ours["palette"]["accent"] = "#7A6E66"  # màu xám: không có màu nhấn trong frame mẫu
    report = compare.compare_measures(fake_measure(), ours)
    accent = next(m for m in report["metrics"] if m["name"] == "màu accent")
    assert accent["ok"] and accent["weight"] == 0
    assert report["score"] == 100.0


def test_dim_glow_colour_is_not_compared_as_an_accent():
    ours = fake_measure()
    ours["palette"]["accent"] = "#783518"  # cam tối sẫm: quầng sáng chứ không phải màu nhấn
    accent = next(m for m in compare.compare_measures(fake_measure(), ours)["metrics"]
                  if m["name"] == "màu accent")
    assert accent["weight"] == 0
