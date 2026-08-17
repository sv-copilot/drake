from __future__ import annotations

from scripts.content_slice import (
    DEFAULT_KIND,
    SLICE_KINDS,
    content_acceptance_checks,
    route_acceptance,
    slice_kind,
    validate_content_brief,
    validate_content_slice,
)

VALID_BRIEF = {
    "scene_id": "scene-1",
    "beats": ["cold open", "climax"],
    "pov": "third-limited",
    "characters": ["Mara", "Jonas"],
    "setting": "orbital station",
    "continuity_constraints": ["Mara has a scar on her left hand"],
    "voice_profile": "terse, literary",
}


# --- (a) valid content brief validates -------------------------------------------


def test_valid_content_brief_validates() -> None:
    assert validate_content_brief(VALID_BRIEF) == []


def test_valid_content_slice_validates() -> None:
    row = {"slice_id": "S1", "kind": "content", "content_brief": VALID_BRIEF}
    assert validate_content_slice(row) == []


# --- (b) content slice with missing brief rejected --------------------------------


def test_content_slice_missing_brief_rejected() -> None:
    row = {"slice_id": "S1", "kind": "content"}
    errors = validate_content_slice(row)
    assert any("content_brief" in e for e in errors)


# --- (c) product slices unchanged -------------------------------------------------


def test_absent_kind_defaults_to_product() -> None:
    row = {"slice_id": "S1"}
    assert slice_kind(row) == DEFAULT_KIND
    assert validate_content_slice(row) == []
    assert route_acceptance(row) == "tests"


def test_explicit_product_slice_unchanged() -> None:
    row = {"slice_id": "S1", "kind": "product"}
    assert validate_content_slice(row) == []
    assert route_acceptance(row) == "tests"


# --- kind + brief field validation -------------------------------------------------


def test_invalid_kind_rejected() -> None:
    row = {"slice_id": "S1", "kind": "video"}
    assert any("kind" in e for e in validate_content_slice(row))


def test_missing_brief_fields_reported() -> None:
    errors = validate_content_brief({"scene_id": "s1"})
    assert any("pov" in e for e in errors)
    assert any("beats" in e for e in errors)


def test_list_fields_must_be_lists() -> None:
    bad = dict(VALID_BRIEF, beats="not a list")
    assert any("beats" in e for e in validate_content_brief(bad))


# --- acceptance routing -----------------------------------------------------------


def test_route_acceptance_content() -> None:
    row = {"kind": "content", "content_brief": VALID_BRIEF}
    assert route_acceptance(row) == "saimon"


def test_content_acceptance_checks_shape() -> None:
    checks = content_acceptance_checks(VALID_BRIEF)
    assert checks["verify"].startswith("scene scene-1")
    assert checks["evaluate"]["criteria"] == ["consistency"]


def test_kinds_are_product_and_content() -> None:
    assert set(SLICE_KINDS) == {"product", "content"}
