"""Keep buyer-facing substrate availability separate from bounded evidence."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def _read(relative_path: str) -> str:
    return (DOCS / relative_path).read_text()


def test_scoped_windows_and_macos_evidence_is_exact_and_bounded():
    what_works = _read("get-started/what-works-today.md")

    assert "Windows UIA backend | **Partner qualification; scoped acceptance passed**" in what_works
    assert "`20260717-candidate-56759c8-v2` in-tree WinForms matrix completed 3/3 trials" in what_works
    assert "independent SQLite oracle confirmed 3/3 effects" in what_works
    assert "stale-target and ambiguous-target controls each refused 3/3" in what_works
    assert "0 silent incorrect successes, 0 over-halts, and 0 model calls" in what_works
    assert "not arbitrary Windows applications" in what_works
    assert "preserves earlier rejected diagnostic runs" in what_works
    assert "defafbae758a75c8e149d9693f2cffe1f2264b8c" in what_works
    assert "https://github.com/OpenAdaptAI/openadapt-flow/pull/132" in what_works

    assert "Native macOS backend | **Partner qualification; scoped TextEdit evidence accepted**" in what_works
    assert "one macOS 15.7.3 arm64 host" in what_works
    assert "candidate `b1b61a5` completed 3/3 exact-byte TextEdit trials" in what_works
    assert "refused a two-window ambiguity without changing either file" in what_works
    assert "immutable original report remains `status: failed`" in what_works
    assert "immutable evidence commit `ca1b522`" in what_works
    assert "`ca1b522` preserves its reports and adjudication but is not the current PR head" in what_works
    assert "verifies the exact harness PIDs and temporary root were absent" in what_works
    assert "not clean-machine, design-partner, production, broad-app" in what_works
    assert "ca1b522cad215875f7471782283f8f8bb8e6c998" in what_works
    assert "https://github.com/OpenAdaptAI/openadapt-flow/pull/135" in what_works


def test_availability_does_not_borrow_scoped_evidence_or_other_substrates():
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

    assert "Partner qualification; acceptance in progress**: typed" not in combined
    assert "Partner qualification; acceptance in progress**: permissioned TextEdit" not in combined
    assert "RDP backend | **Partner qualification; acceptance in progress**" in combined
    assert "Design partner needed; no ICA/HDX evidence" in combined
    assert "RDP evidence does not transfer" in combined
    assert "not in the hosted launch candidate" in combined
