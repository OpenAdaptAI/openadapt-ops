"""Keep the docs site off Material for MkDocs builds with a known advisory.

GHSA-xvg9-69gf-fjrf: Material for MkDocs before 9.7.7 lets a crafted `q`
query parameter run script through the search suggestions. The site turns on
`search.suggest`, and CI and the deploy both build from `uv.lock`, so the
locked version is the version the public site ships.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXED_MATERIAL = (9, 7, 7)


def _release(version: str) -> tuple[int, ...]:
    match = re.match(r"\d+(?:\.\d+)*", version)
    assert match, f"unparseable version: {version!r}"
    return tuple(int(part) for part in match.group(0).split("."))


def _locked_version(name: str) -> str:
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    versions = [pkg["version"] for pkg in lock["package"] if pkg["name"] == name]
    assert versions, f"{name} is not in uv.lock"
    return versions[0]


def _declared_floor(name: str) -> str:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    for requirement in project["project"]["dependencies"]:
        match = re.fullmatch(rf"{re.escape(name)}\s*>=\s*([0-9.]+)", requirement.strip())
        if match:
            return match.group(1)
    raise AssertionError(f"pyproject.toml has no `{name}>=` floor")


def test_site_enables_search_suggestions() -> None:
    # The advisory only bites when suggestions are on. If this fails because
    # the feature was removed, the version floor below is still worth keeping.
    assert "search.suggest" in (ROOT / "mkdocs.yml").read_text(encoding="utf-8")


def test_locked_material_includes_the_search_suggestion_fix() -> None:
    locked = _locked_version("mkdocs-material")
    assert _release(locked) >= FIXED_MATERIAL, (
        f"uv.lock pins mkdocs-material {locked}; 9.7.7 or later is required "
        "(GHSA-xvg9-69gf-fjrf). Run `uv lock --upgrade-package mkdocs-material`."
    )


def test_override_generator_tag_names_the_locked_material_version() -> None:
    # overrides/main.html replaces Material's `site_meta` block, so the
    # generator tag is a copied literal. Left stale, the live site announces an
    # older (vulnerable) release than the one it runs, and the post-deploy
    # version check reads the wrong number.
    template = (ROOT / "overrides/main.html").read_text(encoding="utf-8")
    announced = re.findall(r"mkdocs-material-([0-9][0-9.]*)", template)
    assert announced == [_locked_version("mkdocs-material")]


def test_declared_material_floor_blocks_a_vulnerable_relock() -> None:
    floor = _declared_floor("mkdocs-material")
    assert _release(floor) >= FIXED_MATERIAL, (
        f"pyproject.toml allows mkdocs-material>={floor}; raise the floor to 9.7.7"
    )
