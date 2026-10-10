"""Docs claims that must match the shipped CLI and engine behavior.

Each check scans the canonical docs tree and also runs against small fixtures,
so a check that silently stops matching anything fails here too.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"


def _doc_pages() -> list[Path]:
    return sorted(
        path for path in DOCS.rglob("*") if path.suffix in {".md", ".txt"} and path.is_file()
    )


def _sentences(text: str) -> list[str]:
    """Split markdown into sentences, joining wrapped lines within a paragraph."""
    sentences: list[str] = []
    for paragraph in re.split(r"\n\s*\n", text):
        joined = " ".join(line.strip() for line in paragraph.splitlines())
        sentences.extend(s for s in re.split(r"(?<=[.!?])\s+", joined) if s)
    return sentences


def _scan(check) -> list[str]:
    problems = []
    for page in _doc_pages():
        for sentence in check(page.read_text(encoding="utf-8")):
            problems.append(f"{page.relative_to(ROOT)}: {sentence}")
    return problems


# --- `--break-it` belongs to the tutorial and quickstart, not to `qualify` ---
#
# `openadapt-flow qualify ... --break-it` is an argparse error: the flag exists
# only on `tutorial` (and the launcher's `quickstart`). `qualify propose` and
# `qualify accept` run their break-it fault on their own, with no flag.

_DEMO_FLAG = re.compile(r"(?:tutorial|quickstart)\s+--break-it")


def qualify_break_it_claims(text: str) -> list[str]:
    flagged = []
    for sentence in _sentences(text):
        if "qualify" not in sentence or "--break-it" not in sentence:
            continue
        if "--break-it" in _DEMO_FLAG.sub("", sentence):
            flagged.append(sentence)
    return flagged


def test_break_it_check_flags_the_nonexistent_qualify_flag() -> None:
    bad = "`--break-it` on `openadapt-flow qualify` is the fail-closed test. A fake\nbanner must halt."
    assert qualify_break_it_claims(bad)
    assert qualify_break_it_claims("Those two. `--break-it` on `qualify` is the test.")


def test_break_it_check_accepts_the_real_demo_commands() -> None:
    good = (
        "`openadapt flow tutorial --break-it` (or `openadapt quickstart --break-it`)\n"
        "is the fail-closed demo. During qualification, `qualify propose` and\n"
        "`qualify accept` run the proposed oracle against the same fault."
    )
    assert qualify_break_it_claims(good) == []


def test_docs_never_attach_break_it_to_qualify() -> None:
    assert _scan(qualify_break_it_claims) == []


# --- A single effect verdict never decides a re-run ---
#
# A refuted verdict with observed `absent` proves only that one effect is
# missing. The run is `HALTED_BEFORE_EFFECT` only when every consequential step
# in it is proven absent or stopped before delivery; an earlier confirmed or
# unverified write, or a declared effect with no evidence, makes it
# `RECONCILIATION_REQUIRED`. Re-run advice must come from `transaction_outcome`.

_RERUN = re.compile(r"\b(?:safe to (?:re-?run|retry|try again)|maps to)\b", re.IGNORECASE)


def verdict_rerun_claims(text: str) -> list[str]:
    flagged = []
    for sentence in _sentences(text):
        if not re.search(r"\b(?:refuted|absent)\b", sentence):
            continue
        if "HALTED_BEFORE_EFFECT" not in sentence or not _RERUN.search(sentence):
            continue
        if "transaction_outcome" not in sentence:
            flagged.append(sentence)
    return flagged


def test_verdict_check_flags_a_per_effect_rerun_promise() -> None:
    bad = (
        "| `refuted` | Absent. | If the observed effect is `absent`, the run maps to\n"
        "`HALTED_BEFORE_EFFECT` and is safe to re-run after fixing the cause. |"
    )
    assert verdict_rerun_claims(bad)


def test_verdict_check_accepts_the_run_level_rule() -> None:
    good = (
        "Before re-running, check the run's `transaction_outcome`: re-run only if\n"
        "it is `HALTED_BEFORE_EFFECT`, even when this verdict observed `absent`.\n\n"
        "| `HALTED_BEFORE_EFFECT` | Every consequential step was verified absent. | Safe to fix and re-run. |"
    )
    assert verdict_rerun_claims(good) == []


def test_docs_never_derive_a_rerun_from_one_verdict() -> None:
    assert _scan(verdict_rerun_claims) == []


# --- A failed push is not always safe to re-run ---
#
# `openadapt-flow push` exits 1 both when the server refused the artifact
# (safe to push again) and when delivery is uncertain (the server may hold it;
# the CLI says not to retry until the artifact is reconciled). Any page that
# calls a failed push safe to re-run must, in the same section, cover the
# uncertain case and say to reconcile first.

_SAFE_AGAIN = re.compile(r"\bsafe to (?:re-?run|retry|try again|run again)\b", re.IGNORECASE)


def _sections(text: str) -> list[str]:
    return re.split(r"^#{1,6} ", text, flags=re.MULTILINE)


def push_retry_claims(text: str) -> list[str]:
    flagged = []
    for section in _sections(text):
        lowered = section.lower()
        if "uncertain" in lowered and "reconcile" in lowered:
            continue
        for sentence in _sentences(section):
            if re.search(r"\bpush\b", sentence, re.IGNORECASE) and _SAFE_AGAIN.search(sentence):
                flagged.append(sentence)
    return flagged


def test_push_check_flags_a_blanket_safe_to_rerun() -> None:
    bad = "## Sync\n\nFrom the CLI, a failed `push` exits nonzero and is safe to re-run.\n"
    assert push_retry_claims(bad)


def test_push_check_accepts_guidance_that_covers_uncertain_delivery() -> None:
    good = (
        "## Sync\n\nA refused `push` is safe to re-run. If delivery is uncertain,\n"
        "reconcile the artifact in the hosted control plane first.\n"
    )
    assert push_retry_claims(good) == []


def test_docs_never_call_every_failed_push_safe_to_rerun() -> None:
    assert _scan(push_retry_claims) == []


def test_troubleshooting_names_the_uncertain_push_result() -> None:
    text = (DOCS / "guides/troubleshooting.md").read_text(encoding="utf-8")
    section = next(s for s in _sections(text) if s.startswith("The offline queue is stuck"))
    for required in ("delivery_uncertain", "reconcile", "exit code"):
        assert required in section, required
