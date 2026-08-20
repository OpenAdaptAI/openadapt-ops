"""Run the browser lifecycle contract tests in the normal pytest gate."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_browser_lifecycle_contract() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.fail("Node.js is required for the public lifecycle browser contract")
    completed = subprocess.run(
        [node, "--test", "tests/js/production_lifecycle.test.cjs"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
