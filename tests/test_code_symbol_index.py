"""Behavior tests for the public API of code_symbol_index."""

from __future__ import annotations

import pytest

import code_symbol_index


def test_normalize_trims_and_lowercases() -> None:
    assert code_symbol_index.normalize("  Hello World ") == "hello world"


@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_normalize_rejects_blank_input(value: str) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        code_symbol_index.normalize(value)


def test_version_is_semver() -> None:
    parts = code_symbol_index.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
