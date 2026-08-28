"""Offline guards on the canonical design tokens the docs site consumes.

docs.openadapt.ai kept a retired warm palette for weeks after openadapt-web,
openadapt-cloud, and openadapt-desktop had all moved to the canonical cool one,
and nothing failed while they diverged. Three things made it invisible:

1. The palette was a private copy of hex literals, so no token search found it.
2. A retired value also sat in an SVG fill, where a stylesheet search misses it.
3. Seven shipped screenshots carried the warm ground in their pixels, where no
   text search of any kind reaches.

These tests fail instead. They need no network and no image library:
``scripts/vendor_design_tokens.py --check`` is the online half, and
``scripts/measure_asset_palette.py`` writes the measurements enforced here.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[1]
VENDOR_DIR = REPO / "docs" / "stylesheets" / "vendor" / "openadapt-web"
BRAND_CSS = REPO / "docs" / "stylesheets" / "brand.css"
PALETTE_LEDGER = REPO / "docs" / "assets" / "visual-palette.json"

PROVENANCE = json.loads((VENDOR_DIR / "provenance.json").read_text(encoding="utf-8"))
CANONICAL = json.loads((VENDOR_DIR / "tokens.json").read_text(encoding="utf-8"))

# Every retired warm value, from the palette openadapt-cloud retired in its PR
# #325 and from the two older grounds that preceded it. Kept as literals on
# purpose: a token name search is exactly what missed these.
RETIRED_VALUES = (
    # Grounds and panels. #f2f1ed is one digit from #f2f1ec and was found in
    # the wild, so near-misses are listed too.
    "#f2f1ec",
    "#f2f1ed",
    "#f4f3ef",
    "#f4f3ed",
    "#fbfaf6",
    "#fdfcf9",
    "#fffef9",
    "#eae8e0",
    "#eeede5",
    "#e0ded4",
    "#dddcd2",
    "#d6d8ce",
    "#c9ccc2",
    "#c9cdc2",
    "#eef0ea",
    # warm inks
    "#1a1e17",
    "#23281f",
    "#252a22",
    "#4c523f",
    "#5a6050",
    "#687066",
    "#3a4133",
    # retired accents
    "#3e6b4f",
    "#4f8a66",
    "#2f513c",
    "#2f7154",
    "#76512f",
    "#a74612",
    "#86d9a8",
    "#a8e8bf",
    "#e0b27f",
    "#ffd166",
    "#9d8bd5",
)

# Every text file the built site serves that can carry a colour. mkdocs copies
# docs/ verbatim and renders overrides/ into every page, so a literal in any of
# them reaches a visitor.
SHIPPED_TEXT_GLOBS = (
    "docs/**/*.css",
    "docs/**/*.svg",
    "docs/**/*.js",
    "docs/**/*.html",
    "overrides/**/*.html",
    "mkdocs.yml",
)


def shipped_text_files() -> list[Path]:
    files: list[Path] = []
    for pattern in SHIPPED_TEXT_GLOBS:
        files.extend(sorted(REPO.glob(pattern)))
    # The vendored canonical copies are byte-identical upstream files. They are
    # covered by the digest test above, not by a content search.
    return [path for path in files if VENDOR_DIR not in path.parents]


def test_vendored_tokens_are_byte_identical_to_the_pinned_copies() -> None:
    for name, entry in PROVENANCE["files"].items():
        digest = hashlib.sha256((VENDOR_DIR / name).read_bytes()).hexdigest()
        assert digest == entry["sha256"], (
            f"{name} was hand-edited. Vendored tokens are byte-identical copies "
            f"of {PROVENANCE['canonical_repository']}:{entry['canonical_path']}. "
            f"Change the value there, then run: "
            f"python scripts/vendor_design_tokens.py --write"
        )


def test_the_canonical_tokens_name_this_repository_as_a_consumer() -> None:
    consumers = " ".join(CANONICAL["$consumers"])
    assert "openadapt-ops" in consumers, (
        "styles/tokens.json in openadapt-web no longer lists this repository in "
        "$consumers. Either the vendored copy is stale or the convention "
        "changed upstream."
    )


def test_brand_css_never_redefines_a_canonical_colour_token() -> None:
    # Colour is the thing that must not fork. A second definition of --surface
    # or --accent-verified is exactly how the docs and the marketing site end
    # up looking like different products. Derive with var() or color-mix().
    css = BRAND_CSS.read_text(encoding="utf-8")
    redefined = [
        token
        for token in CANONICAL["color"]
        if re.search(rf"^\s*{re.escape(token)}\s*:", css, re.MULTILINE)
    ]
    assert redefined == [], (
        f"docs/stylesheets/brand.css redefines canonical colour tokens: "
        f"{redefined}. Derive from them instead."
    )


def test_brand_css_carries_no_literal_colour_at_all() -> None:
    css = BRAND_CSS.read_text(encoding="utf-8")
    literals = re.findall(r"#[0-9a-fA-F]{3,8}\b", css)
    assert literals == [], (
        f"docs/stylesheets/brand.css carries literal colours: {literals}. Every "
        f"colour on this site must be reachable from a canonical token."
    )


@pytest.mark.parametrize(
    "path", shipped_text_files(), ids=lambda path: str(path.relative_to(REPO))
)
def test_no_retired_warm_value_in_a_shipped_text_asset(path: Path) -> None:
    text = path.read_text(encoding="utf-8").lower()
    found = sorted({value for value in RETIRED_VALUES if value in text})
    assert found == [], (
        f"{path.relative_to(REPO)} still carries retired palette values: "
        f"{found}. The canonical replacements are in "
        f"docs/stylesheets/vendor/openadapt-web/tokens.css."
    )


def _ledger() -> dict:
    return json.loads(PALETTE_LEDGER.read_text(encoding="utf-8"))


def test_every_shipped_image_is_recorded_in_the_visual_palette_ledger() -> None:
    suffixes = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".ico"}
    asset_root = REPO / "docs" / "assets"
    on_disk = {
        str(path.relative_to(asset_root))
        for path in asset_root.rglob("*")
        if path.is_file() and path.suffix.lower() in suffixes
    }
    recorded = set(_ledger()["assets"])
    assert on_disk == recorded, (
        "docs/assets/visual-palette.json does not describe the images on disk. "
        "Unrecorded: "
        f"{sorted(on_disk - recorded)}. Recorded but missing: "
        f"{sorted(recorded - on_disk)}. Re-run: uv run --with pillow python "
        "scripts/measure_asset_palette.py --write"
    )


def test_recorded_image_measurements_still_describe_the_bytes_on_disk() -> None:
    asset_root = REPO / "docs" / "assets"
    for name, entry in _ledger()["assets"].items():
        digest = hashlib.sha256((asset_root / name).read_bytes()).hexdigest()
        assert digest == entry["sha256"], (
            f"{name} changed but its recorded measurement did not. Re-run: "
            f"uv run --with pillow python scripts/measure_asset_palette.py "
            f"--write"
        )


def test_no_shipped_image_has_a_warm_ground() -> None:
    # See "$cool_rule" in the ledger. The dominant colour is the ground, and no
    # warm ground can satisfy blue >= red.
    warm = {}
    for name, entry in _ledger()["assets"].items():
        dominant = entry["dominant_colors"][0]["hex"]
        red = int(dominant[1:3], 16)
        blue = int(dominant[5:7], 16)
        if blue < red:
            warm[name] = dominant
    assert warm == {}, (
        f"These images have a warm ground: {warm}. Every capture the docs ship "
        f"must come from a surface already on the canonical cool palette. "
        f"Re-vendor it from OpenAdaptAI/openadapt-web rather than re-shooting "
        f"it here."
    )


def test_no_image_ground_is_an_exact_retired_value() -> None:
    """A narrower, louder restatement of the rule above.

    Both tests read the dominant colour and no further. A warm colour below the
    ground is usually --accent-halt tinting a halt card, which is a canonical
    token behaving correctly, not a retired palette.
    """
    offenders = {
        name: entry["dominant_colors"][0]["hex"]
        for name, entry in _ledger()["assets"].items()
        if entry["dominant_colors"][0]["hex"] in RETIRED_VALUES
    }
    assert offenders == {}, (
        f"These images are shot on a retired palette ground: {offenders}."
    )
