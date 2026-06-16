"""Tests for the component registry."""

from __future__ import annotations

import pytest

from statskills.core.registry import ComponentRegistry


def test_register_and_get():
    reg = ComponentRegistry()

    @reg.register("verifier", "numeric")
    class NumericVerifier:
        pass

    assert reg.get("verifier", "numeric") is NumericVerifier
    assert reg.is_registered("verifier", "numeric")
    assert not reg.is_registered("verifier", "regex")


def test_duplicate_registration_raises():
    reg = ComponentRegistry()

    @reg.register("verifier", "numeric")
    class A:
        pass

    with pytest.raises(ValueError, match="Duplicate registration"):

        @reg.register("verifier", "numeric")
        class B:
            pass


def test_get_unknown_raises_keyerror_listing_available():
    reg = ComponentRegistry()

    @reg.register("verifier", "numeric")
    class A:
        pass

    with pytest.raises(KeyError) as exc:
        reg.get("verifier", "regex")
    # The error names the category's available types to aid debugging.
    assert "numeric" in str(exc.value)


def test_list_category_and_registered():
    reg = ComponentRegistry()

    @reg.register("verifier", "numeric")
    class A:
        pass

    @reg.register("verifier", "regex")
    class B:
        pass

    @reg.register("router", "forced")
    class C:
        pass

    assert sorted(reg.list_category("verifier")) == ["numeric", "regex"]
    assert reg.list_category("router") == ["forced"]
    assert reg.list_category("missing") == []
    assert reg.registered() == [
        ("router", "forced"),
        ("verifier", "numeric"),
        ("verifier", "regex"),
    ]


def test_clear():
    reg = ComponentRegistry()

    @reg.register("verifier", "numeric")
    class A:
        pass

    reg.clear()
    assert reg.list_category("verifier") == []
