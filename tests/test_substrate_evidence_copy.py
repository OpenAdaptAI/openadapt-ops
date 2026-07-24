"""Keep released substrate availability tied to exact, bounded evidence.

Every backend is presented as implemented in the governed product. The tests
also preserve the two independent honesty dimensions: task/environment evidence
does not become a broad app-support claim, and the managed browser runner does
not silently absorb customer-controlled desktop or remote execution.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def _read(relative_path: str) -> str:
    return (DOCS / relative_path).read_text()


def test_native_desktop_evidence_is_exact_and_bounded():
    what_works = _read("get-started/what-works-today.md")

    assert "Windows UIA backend | **Supported**" in what_works
    assert (
        "`20260717-candidate-56759c8-v2` in-tree WinForms matrix completed "
        "3/3 trials" in what_works
    )
    assert "independent SQLite oracle confirmed 3/3 effects" in what_works
    assert "stale-target and ambiguous-target controls each refused 3/3" in what_works
    assert "0 silent incorrect successes, 0 over-halts, and 0 model calls" in what_works
    assert "preserves earlier rejected diagnostic runs" in what_works
    assert "defafbae758a75c8e149d9693f2cffe1f2264b8c" in what_works

    assert "Native macOS backend | **Supported**" in what_works
    assert "candidate `b1b61a5` completed 3/3 exact-byte TextEdit trials" in what_works
    assert "refused a two-window ambiguity without changing either file" in what_works
    assert "immutable original report remains `status: failed`" in what_works
    assert "verifies the exact harness PIDs and temporary root were absent" in what_works
    assert "ca1b522cad215875f7471782283f8f8bb8e6c998" in what_works

    assert "Native Linux backend | **Supported**" in what_works
    assert "3/3 exact-file effects" in what_works
    assert "3/3 ambiguous-target refusals" in what_works
    assert "3/3 stale-target refusals" in what_works
    assert "3de5fc67acf3024a621f812c5a6ed9be07fac335" in what_works
    assert "30059807758/job/89378981573" in what_works
    assert "does not establish Wayland or arbitrary third-party application support" in what_works


def test_remote_evidence_covers_rdp_lifecycle_and_citrix_contract():
    what_works = _read("get-started/what-works-today.md")

    assert "RDP backend | **Supported**" in what_works
    assert "Aardwolf 0.2.14 over a Parallels Windows 11 VM" in what_works
    assert "3/3 Windows Run-dialog file effects" in what_works
    assert "full governed lifecycle at mechanism commit `6031fde`" in what_works
    assert "3/3 healthy effects and 3/3 drift safe-halts" in what_works
    assert "affedc5f1f0de533a0744deaa8e30a203c91c6b3" in what_works
    assert "https://github.com/OpenAdaptAI/openadapt-flow/pull/177" in what_works
    assert "not Aardwolf, a Windows-app qualification, Citrix ICA/HDX" in what_works

    assert "Citrix / VDI backend | **Supported**" in what_works
    assert "dedicated `--backend citrix` path" in what_works
    assert "requires a readiness marker for governed `run`" in what_works
    assert "carries the closed target into durable resume" in what_works
    assert "3/3 healthy effects and 3/3 severe-drift safe-halts" in what_works
    assert "`code_readiness_accepted: true` and `ica_hdx_accepted: false`" in what_works
    assert "not a counted real ICA/HDX batch" in what_works
    assert "f6faac5b900b78cbda5980de0e983a9f987285ac" in what_works
    assert "https://github.com/OpenAdaptAI/openadapt-flow/pull/183" in what_works


def test_public_managed_runner_and_customer_runtime_boundaries_remain_distinct():
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

    for stale_label in ["Early access", "Exploratory", "Design-partner"]:
        assert stale_label not in combined

    assert "The public subscription covers approved browser workflows" in combined
    assert "Customer-controlled runtime connected to Cloud" in combined
    assert "shared managed-browser boundary" in combined
    assert "not a counted real ICA/HDX batch" in combined


def test_desktop_beta_release_is_current_and_cross_platform():
    what_works = _read("get-started/what-works-today.md")
    install = _read("desktop/install.md")

    for source in [what_works, install]:
        assert "desktop-v0.9.0" in source
        assert "Windows" in source
        assert "macOS" in source
        assert "Linux" in source
    assert "SHA256SUMS" in what_works
    assert "installed, launched, and uninstalled" in what_works
