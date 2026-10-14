"""Keep uv.lock off urllib3 and AnyIO builds with known advisories.

CI and the docs deploy install from `uv.lock`, so the locked version is the
version that runs. urllib3 is a declared dependency, so pyproject.toml also
carries a floor that stops a later relock from falling back. AnyIO arrives
only through the `dev` and `llm` extras (httpx, anthropic), so the lock check
is the guard for it.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# package -> (first patched release, advisories it fixes)
PATCHED = {
    "urllib3": (
        (2, 8, 0),
        "GHSA-8988-9cw3-xx77, GHSA-vxq7-64xx-v4gw, GHSA-gh4c-6fx4-qh6g",
    ),
    "anyio": ((4, 14, 2), "GHSA-82r6-8w77-94w6, GHSA-5p39-cfhj-2xmp"),
}


def _release(version: str) -> tuple[int, ...]:
    match = re.match(r"\d+(?:\.\d+)*", version)
    assert match, f"unparseable version: {version!r}"
    return tuple(int(part) for part in match.group(0).split("."))


def _assert_locked_version_includes_the_fix(name: str) -> None:
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    versions = [pkg["version"] for pkg in lock["package"] if pkg["name"] == name]
    assert versions, f"{name} is not in uv.lock"
    fixed, advisories = PATCHED[name]
    for locked in versions:
        assert _release(locked) >= fixed, (
            f"uv.lock pins {name} {locked}; {'.'.join(map(str, fixed))} or later "
            f"is required ({advisories}). Run `uv lock --upgrade-package {name}`."
        )


def test_locked_urllib3_includes_the_fix() -> None:
    _assert_locked_version_includes_the_fix("urllib3")


def test_locked_anyio_includes_the_fix() -> None:
    _assert_locked_version_includes_the_fix("anyio")


def test_declared_urllib3_floor_blocks_a_vulnerable_relock() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    floors = [
        match.group(1)
        for requirement in project["project"]["dependencies"]
        if (match := re.fullmatch(r"urllib3\s*>=\s*([0-9.]+)", requirement.strip()))
    ]
    assert floors, "pyproject.toml has no `urllib3>=` floor"
    assert _release(floors[0]) >= PATCHED["urllib3"][0], (
        f"pyproject.toml allows urllib3>={floors[0]}; raise the floor to 2.8.0"
    )
