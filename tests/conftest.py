"""Shared pytest configuration: auto-qualify tests by directory."""

from __future__ import annotations

from pathlib import Path

import pytest

_TESTS_ROOT = Path(__file__).resolve().parent


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        try:
            rel = Path(str(item.fspath)).relative_to(_TESTS_ROOT)
        except ValueError:
            continue
        parts = rel.parts
        if (parts and parts[0] == "unit") or rel.name == "test_tools.py":
            item.add_marker(pytest.mark.unit)
