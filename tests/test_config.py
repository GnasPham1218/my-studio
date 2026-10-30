"""Ràng buộc cấu trúc của config: lỗi ở đây sẽ làm Remotion hỏng lúc render."""

from __future__ import annotations

import pytest

from pipeline import config, visuals


def key_paths(node, prefix=""):
    """Tập đường dẫn khoá của một dict lồng nhau (bỏ qua giá trị)."""
    if not isinstance(node, dict):
        return {prefix}
    paths = set()
    for key, value in node.items():
        paths |= key_paths(value, f"{prefix}.{key}" if prefix else key)
    return paths


def test_every_format_points_to_an_existing_aspect():
    for fmt in config.format_ids():
        assert config.default_aspect(fmt) in config.aspect_ids()


def test_all_aspects_share_the_same_structure():
    """Thêm khung hình mới phải đủ khoá như khung hình đang chạy được."""
    reference = key_paths(config.aspect("vertical"))
    optional = {"status"}  # nhãn không phải token layout
    for aspect_id in config.aspect_ids():
        keys = key_paths(config.aspect(aspect_id))
        assert keys - optional == reference - optional, aspect_id


def test_aspects_have_sane_geometry():
    for aspect_id in config.aspect_ids():
        cfg = config.aspect(aspect_id)
        assert cfg["width"] > 0 and cfg["height"] > 0
        pad = cfg["padding"]
        assert pad["top"] + pad["bottom"] < cfg["height"], aspect_id
        assert pad["left"] + pad["right"] < cfg["width"], aspect_id
        caption = cfg["caption"]
        assert caption["maxWidth"] + 2 * caption["sideMargin"] <= cfg["width"], aspect_id
        assert 0 < cfg["visualScale"] <= 1


def test_layout_adds_aspect_id_without_mutating_config():
    layout = config.layout("vertical")
    assert layout["aspect"] == "vertical"
    layout["width"] = 1
    assert config.aspect("vertical")["width"] == 1080


def test_unknown_aspect_and_format_fail_with_clear_message():
    with pytest.raises(SystemExit, match="Khung hình không hợp lệ"):
        config.aspect("diagonal")
    with pytest.raises(SystemExit, match="Format không hợp lệ"):
        config.format_rules("medium")


def test_every_template_is_valid_against_schema():
    for template_id in config.template_ids():
        merged = config.template(template_id)  # tự kiểm schema, lỗi thì SystemExit
        assert merged["id"] == template_id
        assert isinstance(merged["caption"]["scrim"], list)  # [] hợp lệ = không có scrim


def test_template_overrides_base_but_keeps_other_defaults():
    whiteboard = config.template("whiteboard")
    assert whiteboard["background"]["kind"] == "paper"
    assert whiteboard["caption"]["card"]["radius"] == 12
    # Khoá không khai báo trong whiteboard.json lấy từ _base.json.
    assert whiteboard["motion"]["enterSec"] == 0.5
    assert whiteboard["chrome"]["watermark"]["enabled"] is True


def test_template_schema_rejects_unknown_and_malformed_fields():
    assert config.template_errors({"schemaVersion": 1, "id": "ok"}) == []
    assert config.template_errors({"schemaVersion": 1, "id": "ok", "colour": {}})
    assert config.template_errors(
        {"schemaVersion": 1, "id": "ok", "colors": {"bg": "red"}}
    )


def test_deep_merge_replaces_lists_and_merges_dicts():
    merged = config.deep_merge(
        {"a": {"x": 1, "y": [1, 2]}, "b": 1}, {"a": {"y": [9]}, "c": None}
    )
    assert merged == {"a": {"x": 1, "y": [9]}, "b": 1, "c": None}


def test_deep_merge_does_not_alias_inputs():
    base = {"a": {"x": [1]}}
    merged = config.deep_merge(base, {})
    merged["a"]["x"].append(2)
    assert base["a"]["x"] == [1]


def test_visual_defaults_satisfy_their_own_schema():
    """Default trong catalog phải hợp lệ, nếu không build sinh props sai."""
    for kind in visuals.kinds():
        assert visuals.data_errors({"kind": kind, "data": visuals.defaults(kind)}) == [], kind


def test_catalog_declares_requiredata_for_every_kind():
    for kind, entry in visuals.catalog()["kinds"].items():
        assert isinstance(entry.get("requireData"), bool), kind
