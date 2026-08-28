from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path


REPO = Path(__file__).parents[1]
CSS = (REPO / "docs/stylesheets/brand.css").read_text(encoding="utf-8")
MKDOCS = (REPO / "mkdocs.yml").read_text(encoding="utf-8")
LOGO = (REPO / "docs/assets/logo.svg").read_text(encoding="utf-8")
TOKENS = json.loads(
    (REPO / "docs/stylesheets/vendor/openadapt-web/tokens.json").read_text(
        encoding="utf-8"
    )
)
COLOR = TOKENS["color"]


def _luminance(hex_color: str) -> float:
    channels = [int(hex_color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _mix(foreground: str, background: str, percent: float) -> str:
    """Reproduce `color-mix(in srgb, foreground <percent>, background)`."""
    channels = []
    for index in (1, 3, 5):
        front = int(foreground[index : index + 2], 16)
        back = int(background[index : index + 2], 16)
        channels.append(round(front * percent + back * (1 - percent)))
    return "#%02x%02x%02x" % tuple(channels)


def _contrast(foreground: str, background: str) -> float:
    lighter, darker = sorted(
        (_luminance(foreground), _luminance(background)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


def test_prose_links_are_visible_without_flattening_material_hierarchy() -> None:
    assert re.search(
        r"\.md-typeset :where\(p, li, dd, blockquote, figcaption, td\) "
        r"a:not\(\.md-button\):not\(\.headerlink\)",
        CSS,
    )
    assert "text-decoration-line: underline" in CSS
    assert ".md-typeset .grid.cards a" in CSS
    assert "text-decoration-line: none" in CSS
    assert ":visited" in CSS


def test_focus_and_reduced_motion_apply_beyond_document_content() -> None:
    assert re.search(r":focus-visible\s*\{[^}]*outline: 3px solid", CSS, re.DOTALL)
    assert "@media (prefers-reduced-motion: reduce)" in CSS
    assert "scroll-behavior: auto !important" in CSS
    assert "transition-duration: 0.01ms !important" in CSS


def test_light_and_dark_link_states_meet_wcag_aa_contrast() -> None:
    """Measure the colours brand.css actually resolves to, not a copy of them.

    Every value below is read from the vendored canonical tokens, or derived
    from them by the same color-mix() brand.css writes. A palette change
    upstream is therefore re-measured here rather than silently trusted.
    """
    ground = COLOR["--surface"]
    raised = COLOR["--surface-raised"]
    inset = COLOR["--inset-bg"]
    inset_raised = COLOR["--inset-raised"]
    inset_text = COLOR["--inset-text"]

    light_states = (
        COLOR["--accent-verified"],
        COLOR["--accent-verified-hover"],
        COLOR["--link-visited"],
        COLOR["--text-secondary"],
        COLOR["--text-tertiary"],
    )
    for foreground in light_states:
        assert _contrast(foreground, ground) >= 4.5
        assert _contrast(foreground, raised) >= 4.5

    dark_states = (
        COLOR["--inset-ok"],
        _mix(COLOR["--inset-ok"], raised, 0.70),
        _mix(COLOR["--link-visited"], inset_text, 0.30),
        _mix(inset_text, inset, 0.70),
        _mix(COLOR["--focus-ring"], inset_text, 0.35),
    )
    for foreground in dark_states:
        assert _contrast(foreground, inset) >= 4.5
        assert _contrast(foreground, inset_raised) >= 4.5


def test_docs_chrome_uses_the_public_site_system_fonts_and_paper_layout() -> None:
    assert "font: false" in MKDOCS
    assert "generator: false" in MKDOCS
    assert "OpenAdapt.ai ↗: https://openadapt.ai" in MKDOCS
    assert "OpenAdapt.AI and MLDSAI Inc." in MKDOCS
    # The stacks themselves live in the canonical tokens. brand.css only maps
    # them onto Material, so assert the mapping here and the value there.
    assert TOKENS["font"]["--font-display"].startswith("'Avenir Next'")
    assert TOKENS["font"]["--font-body"].startswith("-apple-system")
    assert "--oa-display-font: var(--font-display)" in CSS
    assert "--oa-body-font: var(--font-body)" in CSS
    assert ".md-grid" in CSS and "max-width: 72rem" in CSS
    assert re.search(
        r'\[data-md-color-scheme="default"\] \.md-header\s*\{'
        r'[^}]*background: color-mix\(in srgb, var\(--surface-raised\) 97%,'
        r' transparent\)',
        CSS,
        re.DOTALL,
    )
    assert re.search(
        r'\[data-md-color-scheme="default"\] \.md-footer\s*\{'
        r'[^}]*background: var\(--oa-ground\)',
        CSS,
        re.DOTALL,
    )


def test_docs_actions_and_logo_match_the_ink_on_paper_chrome() -> None:
    assert re.search(
        r"\.md-typeset \.md-button\s*\{[^}]*border-radius: 9999px",
        CSS,
        re.DOTALL,
    )
    logo = ET.fromstring(LOGO)
    view_box = [float(value) for value in logo.attrib["viewBox"].split()]
    assert view_box[2] / view_box[3] >= 4.5
    assert all(
        "textLength" not in element.attrib and "lengthAdjust" not in element.attrib
        for element in logo.iter()
    )
    assert 'content: "Docs"' in CSS
    assert "instead of reducing it to “Docs”" in CSS
    assert "filter: brightness(0) invert(1)" in CSS
