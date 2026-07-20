"""Keep buyer-facing substrate availability tied to exact, bounded evidence.

Target-state policy: every execution substrate is presented as first-class and
**Supported / scoped deployment**, not ranked below the browser. This guard does
not police the availability label; it pins the substrate-evidence section to the
current target-state wording and verifies that each first-class substrate still
ships its exact, bounded evidence (run counts, oracle, immutable commit, Flow PR)
and an honest per-surface boundary. The public browser offer must stay distinct
from these scoped deployments.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def _read(relative_path: str) -> str:
    return (DOCS / relative_path).read_text()


def test_scoped_windows_macos_and_rdp_evidence_is_exact_and_bounded():
    what_works = _read("get-started/what-works-today.md")

    assert "Windows UIA backend | **Supported / scoped deployment**" in what_works
    assert "`20260717-candidate-56759c8-v2` in-tree WinForms matrix completed 3/3 trials" in what_works
    assert "independent SQLite oracle confirmed 3/3 effects" in what_works
    assert "stale-target and ambiguous-target controls each refused 3/3" in what_works
    assert "0 silent incorrect successes, 0 over-halts, and 0 model calls" in what_works
    assert "Each Windows workflow is qualified in its real environment" in what_works
    assert "preserves earlier rejected diagnostic runs" in what_works
    assert "defafbae758a75c8e149d9693f2cffe1f2264b8c" in what_works
    assert "https://github.com/OpenAdaptAI/openadapt-flow/pull/132" in what_works

    assert "Native macOS backend | **Supported / scoped deployment**" in what_works
    assert "one macOS 15.7.3 arm64 host" in what_works
    assert "candidate `b1b61a5` completed 3/3 exact-byte TextEdit trials" in what_works
    assert "refused a two-window ambiguity without changing either file" in what_works
    assert "immutable original report remains `status: failed`" in what_works
    assert "immutable evidence commit `ca1b522`" in what_works
    assert "`ca1b522` preserves its reports and adjudication but is not the current PR head" in what_works
    assert "verifies the exact harness PIDs and temporary root were absent" in what_works
    assert "Each macOS workflow is qualified in its real environment" in what_works
    assert "ca1b522cad215875f7471782283f8f8bb8e6c998" in what_works
    assert "https://github.com/OpenAdaptAI/openadapt-flow/pull/135" in what_works

    assert "RDP backend | **Supported / scoped deployment**" in what_works
    assert "one Parallels Windows 11 VM at 1280x800 with Aardwolf 0.2.14" in what_works
    assert "candidate `82a658a` completed 3/3 trials" in what_works
    assert "unique file through the Windows Run dialog over network RDP" in what_works
    assert "Independent guest-tools readback confirmed the exact file contents" in what_works
    assert "51.845s, 10.467s, and 7.477s" in what_works
    assert "0 failures, 0 silent incorrect successes, 0 over-halts, and 0 model calls" in what_works
    assert "restored the exact eight-snapshot inventory" in what_works
    assert "returned the current pointer without resume to the unchanged original base" in what_works
    assert "Each RDP workflow is qualified in its real environment" in what_works
    assert "not counted as acceptance trials" in what_works
    assert "results_82a658a_20260718.sanitized.json" in what_works
    assert "6610d24cebba27918b8ea507b2f05a094057ac85" in what_works
    assert "https://github.com/OpenAdaptAI/openadapt-flow/pull/142" in what_works


def test_public_offer_and_scoped_substrate_evidence_remain_distinct():
    pages = [
        _read("get-started/what-works-today.md"),
        _read("concepts/deployment-matrix.md"),
        _read("concepts/backends.md"),
        _read("concepts/substrate-model.md"),
        _read("guides/hosted.md"),
        _read("guides/security-review.md"),
        _read("concepts/index.md"),
        _read("index.md"),
    ]
    combined = "\n".join(pages)

    assert "acceptance remains in progress" not in combined
    assert "RDP backend | **Supported / scoped deployment**" in combined
    # Citrix / VDI is first-class and Supported / scoped deployment, and the
    # ICA/HDX honesty is preserved: each Citrix/VDI workflow is qualified in its
    # own real ICA/HDX environment rather than inheriting RDP's evidence.
    assert "Citrix / VDI backend | **Supported / scoped deployment**" in combined
    assert "in its real ICA/HDX environment" in combined
    # The public browser subscription stays distinct from the scoped substrate
    # deployments.
    assert "The public subscription covers approved browser workflows" in combined
    assert "scoped separately from the public browser offer" in combined
    assert "ordered separately from these scoped deployments" in combined
    assert "hosted launch candidate" not in combined
