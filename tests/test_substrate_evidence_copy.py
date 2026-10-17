"""Keep released substrate availability tied to exact, bounded evidence.

Each surface's evidence names the retained report it comes from and says
what that report doesn't cover. The tests also keep two boundaries apart:
task and environment evidence does not become a broad app-support claim, and
the managed browser runner does not absorb desktop or remote execution.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def _read(relative_path: str) -> str:
    return " ".join((DOCS / relative_path).read_text().split())


def test_native_desktop_evidence_is_exact_and_bounded():
    evidence = _read("security/evidence.md")

    assert "`20260717-candidate-56759c8-v2` WinForms run completed 3/3 trials" in evidence
    assert "independent SQLite read confirmed 3/3 saves" in evidence
    assert "stale-target and ambiguous-target controls each refused 3/3" in evidence
    assert "0 silent incorrect successes, 0 over-halts, and 0 model calls" in evidence
    assert "keeps earlier diagnostic runs that were rejected" in evidence
    assert "defafbae758a75c8e149d9693f2cffe1f2264b8c" in evidence

    assert "candidate `b1b61a5` completed 3/3 TextEdit trials" in evidence
    assert "refused a two-window ambiguity without changing either file" in evidence
    assert "The original report still reads `status: failed`" in evidence
    assert "ca1b522cad215875f7471782283f8f8bb8e6c998" in evidence

    assert "3/3 exact file saves" in evidence
    assert "3/3 ambiguous-target refusals" in evidence
    assert "3/3 stale-target refusals" in evidence
    assert "3de5fc67acf3024a621f812c5a6ed9be07fac335" in evidence
    assert "30059807758, job 89378981573" in evidence
    assert "doesn't establish Wayland or arbitrary third-party application support" in evidence


def test_remote_evidence_covers_rdp_lifecycle_and_citrix_contract():
    evidence = _read("security/evidence.md")

    assert "Aardwolf 0.2.14 into a Parallels Windows 11 virtual machine" in evidence
    assert "3/3 healthy saves and 3/3 drift halts" in evidence
    assert "affedc5f1f0de533a0744deaa8e30a203c91c6b3" in evidence
    assert "packages/flow/benchmark/rdp_ladder/results.json" in evidence
    assert "not Aardwolf, a Windows app, or Citrix ICA/HDX" in evidence

    assert "`--backend citrix` path" in evidence
    assert "requires on-screen readiness text before a governed run" in evidence
    assert "3/3 healthy saves and 3/3 severe-drift halts" in evidence
    assert "`code_readiness_accepted: true` and `ica_hdx_accepted: false`" in evidence
    assert "not a counted real ICA/HDX batch" in evidence
    assert "f6faac5b900b78cbda5980de0e983a9f987285ac" in evidence
    assert "packages/flow/benchmark/citrix_workspace/results.json" in evidence
    assert "github.com/OpenAdaptAI/openadapt-flow" not in evidence


def test_public_managed_runner_and_customer_runtime_boundaries_remain_distinct():
    boundaries = _read("security/deployment-boundaries.md")
    evidence = _read("security/evidence.md")
    combined = " ".join([boundaries, evidence, _read("explanation/surfaces.md"), _read("index.md")])

    for stale_label in ["Early access", "Exploratory", "Design-partner"]:
        assert stale_label not in combined

    assert "Desktop, RDP, and Citrix jobs never go to this runner" in boundaries
    assert "The runner is on infrastructure you control" in boundaries
    assert "desktop, RDP, and Citrix runs happen on a runner you control" in evidence
    assert "not a counted real ICA/HDX batch" in combined


def test_deployment_config_selects_dedicated_citrix_backend_and_safety_contract():
    config = _read("reference/configuration.md")

    assert "Citrix is its own backend, not an alias for RDP" in config
    assert "kind: citrix" in config
    assert "Flow build `CitrixWorkspaceBackend`" in config
    assert "rdp_window_title: Claims - Citrix Workspace" in config
    assert "rdp_max_frame_age_s: 3.0" in config
    assert "rdp_readiness_text: Claims queue" in config
    assert "rdp_readiness_min_ratio: 0.90" in config
    assert "`kind: citrix` rejects `rdp_host`" in config
    assert "Governed Citrix `run` and `resume` require a nonblank `rdp_readiness_text`" in config


def test_every_released_surface_has_an_evidence_row():
    evidence = _read("security/evidence.md")
    surfaces = _read("explanation/surfaces.md")
    for surface in ("Web", "macOS", "Windows", "Linux", "RDP", "Citrix"):
        assert f"| {surface}" in evidence, surface
        assert surface.lower() in surfaces.lower(), surface
