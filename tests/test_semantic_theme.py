"""The selected theme is a pinned, licensed snapshot shared with the product UI."""
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

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


@pytest.mark.parametrize("autocrlf", ["false", "true"])
def test_checkout_preserves_both_vendor_snapshots(tmp_path, autocrlf):
    git = ["git", "-C", str(ROOT)]
    paths = subprocess.check_output(
        [*git, "ls-files", "docs/stylesheets/vendor"], text=True
    ).splitlines()
    assert paths
    subprocess.run(
        [*git, "-c", f"core.autocrlf={autocrlf}", "checkout-index",
         f"--prefix={tmp_path.as_posix()}/", "--", *paths],
        check=True,
    )
    for path in paths:
        original = subprocess.check_output([*git, "show", f":{path}"])
        assert (tmp_path / path).read_bytes() == original, path
