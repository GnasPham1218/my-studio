from __future__ import annotations

from pipeline import visuals


def test_resolve_fills_defaults_and_keeps_overrides():
    resolved = visuals.resolve({"kind": "storage", "data": {"reductionPct": 40}})
    assert resolved["data"]["reductionPct"] == 40
    assert resolved["data"]["beforeLabel"] == visuals.defaults("storage")["beforeLabel"]


def test_resolve_replaces_lists_instead_of_merging_items():
    rows = [{"label": "A", "value": 0.5}]
    resolved = visuals.resolve({"kind": "limits", "data": {"rows": rows}})
    assert resolved["data"]["rows"] == rows
    assert resolved["data"]["badge"] == visuals.defaults("limits")["badge"]


def test_resolve_leaves_passthrough_and_empty_visuals_alone():
    assert visuals.resolve(None) is None
    assert visuals.resolve({"kind": "none"}) == {"kind": "none"}


def test_resolve_does_not_mutate_catalog_defaults():
    resolved = visuals.resolve({"kind": "award"})
    resolved["data"]["rows"].append({"label": "x"})
    assert len(visuals.defaults("award")["rows"]) == 3


def test_unknown_kind_is_reported_with_available_kinds():
    errors = visuals.data_errors({"kind": "hologram"})
    assert errors and "hologram" in errors[0] and "phone" in errors[0]


def test_data_is_validated_against_the_kind_schema():
    bad_type = visuals.data_errors({"kind": "shrink", "data": {"rows": "nope"}})
    assert bad_type
    out_of_range = visuals.data_errors(
        {"kind": "decline", "data": {"values": [10, 20, 130]}}
    )
    assert out_of_range
    extra_key = visuals.data_errors({"kind": "phone", "data": {"colour": "red"}})
    assert extra_key


def test_passthrough_kind_rejects_data():
    assert visuals.data_errors({"kind": "image", "data": {"a": 1}})


def test_listing_mentions_every_kind():
    listing = visuals.render_listing()
    for kind in visuals.kinds():
        assert f"## {kind}" in listing
