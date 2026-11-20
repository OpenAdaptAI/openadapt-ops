"""The selected theme is a pinned, licensed snapshot shared with the product UI."""
import hashlib
import json
import shutil
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
                   'fonts/OFL-PublicSans.txt', 'fonts/OFL-InterTight.txt',
                   'fonts/PublicSans-Variable.woff2', 'fonts/InterTight-Variable.woff2',
                   'fonts/SOURCES.md']:
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


def test_material_paints_semantic_roles_in_both_schemes(tmp_path):
    """Render the effective cascade, including Material and the real CSS load order."""
    from mkdocs.config import load_config

    browser = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    if not browser:
        mac_chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        if not mac_chrome.is_file():
            pytest.skip("Chromium is required for the computed-style regression")
        browser = str(mac_chrome)

    config = load_config(config_file=str(ROOT / "mkdocs.yml"))
    material_css = next(Path(path) / "assets/stylesheets" for path in config.theme.dirs
                        if (Path(path) / "assets/stylesheets").is_dir())
    styles = [next(material_css.glob("main.*.min.css")), next(material_css.glob("palette.*.min.css"))]
    styles.extend(Path(config.docs_dir) / path for path in config.extra_css)
    links = "\n".join(f'<link rel="stylesheet" href="{path.as_uri()}">' for path in styles)
    fixture = (ROOT / "tests/fixtures/semantic-theme-roles.html").read_text()
    page = tmp_path / "roles.html"
    page.write_text(fixture.replace("<!-- stylesheets -->", links))

    result = subprocess.run(
        [browser, "--headless", "--disable-gpu", "--disable-background-networking",
         "--use-mock-keychain", "--password-store=basic", f"--user-data-dir={tmp_path}/profile",
         "--allow-file-access-from-files", "--dump-dom", page.as_uri()],
        capture_output=True, check=True, text=True, timeout=45,
    )
    start = '<output id="failures">'
    errors = result.stdout.split(start, 1)[1].split("</output>", 1)[0]
    assert json.loads(errors) == []
