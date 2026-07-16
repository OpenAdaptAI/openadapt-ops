from __future__ import annotations

import re
from pathlib import Path


CSS = (Path(__file__).parents[1] / "docs/stylesheets/brand.css").read_text(
    encoding="utf-8"
)


def _luminance(hex_color: str) -> float:
    channels = [int(hex_color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


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
    combinations = (
        ("#3e6b4f", "#f2f1ec"),
        ("#2f513c", "#f2f1ec"),
        ("#76512f", "#f2f1ec"),
        ("#86d9a8", "#14171a"),
        ("#a8e8bf", "#14171a"),
        ("#e0b27f", "#14171a"),
    )
    for foreground, background in combinations:
        assert _contrast(foreground, background) >= 4.5
