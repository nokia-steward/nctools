"""Enforce the netconf-tools tool contract for every module in src/."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def _dist_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return data["project"]["version"]


def _tool_modules() -> list[Path]:
    return sorted(SRC.glob("*.py"))


def test_every_tool_has_pep723_and_version():
    version = _dist_version()
    for path in _tool_modules():
        text = path.read_text(encoding="utf-8")
        assert "# /// script" in text, f"{path.name}: missing PEP 723 block"
        assert "SPDX-License-Identifier: BSD-3-Clause" in text, f"{path.name}: missing SPDX"
        spec = importlib.util.spec_from_file_location(path.stem, path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[path.stem] = mod
        spec.loader.exec_module(mod)
        assert getattr(mod, "__version__", None) == version, f"{path.name}: __version__ mismatch"
        assert callable(getattr(mod, "main", None)), f"{path.name}: missing main()"


def test_every_tool_help_exits_zero():
    for path in _tool_modules():
        proc = subprocess.run(  # noqa: S603
            [sys.executable, str(path), "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, f"{path.name} --help failed: {proc.stderr}"
