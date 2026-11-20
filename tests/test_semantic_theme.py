"""The selected theme is a pinned, licensed snapshot shared with the product UI."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / 'docs/stylesheets/vendor/semantic-theme'


def test_semantic_theme_snapshot_and_licenses_are_complete():
    proof = json.loads((VENDOR / 'provenance.json').read_text())
    assert proof['version'] == 2
    assert proof['source'] == 'OpenAdaptAI/openadapt-web'
    for member in ['semantic-theme.css', 'semantic-theme.json', 'fonts.css',
                   'fonts/OFL-PublicSans.txt', 'fonts/OFL-InterTight.txt']:
        assert member in proof['files']
    for name, item in proof['files'].items():
        assert not Path(name).is_absolute()
        assert '..' not in Path(name).parts
        assert hashlib.sha256((VENDOR / name).read_bytes()).hexdigest() == item['sha256']


def test_navigation_does_not_use_the_verified_outcome_color():
    contract = json.loads((VENDOR / 'semantic-theme.json').read_text())
    for colors in contract['themes'].values():
        assert colors['--oa-link'] != colors['--oa-verified']
        assert colors['--oa-stopped'] != colors['--oa-reconcile']
    css = (ROOT / 'docs/stylesheets/semantic-theme.css').read_text()
    assert '--md-typeset-a-color: var(--oa-link)' in css
    assert '--oa-accent: var(--oa-link)' in css
