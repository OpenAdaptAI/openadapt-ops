#!/usr/bin/env python3
"""Retain the public canonical verifier's result for one exact latest admission.

Generation runs the pinned release verifier against the complete local artifact
inventory. The deterministic check validates retained references and the receipt;
it does not repeat release downloads or claim that a historical result is active.
The browser must also check the current canonical state and public artifacts.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

_projection_spec = importlib.util.spec_from_file_location(
    "_ops_production_lifecycle_renderer",
    Path(__file__).with_name("render_production_lifecycle.py"),
)
assert _projection_spec is not None and _projection_spec.loader is not None
projection = importlib.util.module_from_spec(_projection_spec)
_projection_spec.loader.exec_module(projection)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "docs" / "production-lifecycle-verifications.json"
DOCUMENT_SCHEMA = "openadapt.public-production-lifecycle-verifications/v1"
RECORD_SCHEMA = "openadapt.public-production-lifecycle-verification/v1"
RECORD_FIELDS = {
    "schema_version", "target", "admission_reference",
    "admission_bundle_reference", "verification_receipt", "current_state",
}
CURRENT_STATE_FIELDS = {
    "authority_reference", "authority_bundle_reference", "revocation_reference",
    "revocation_bundle_reference", "signer_registry_pointer",
}
REFERENCE_PREFIX_FIELDS = {
    "schema_version", "repository", "repository_id", "repository_owner_id",
    "registry_source_commit", "registry_revision", "registry_head_sha256",
}


class VerificationError(ValueError):
    """The retained result is not bound to the exact public evidence."""


def closed(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise VerificationError(f"{label} fields differ")
    return value


def exact_commit(value: Any) -> str:
    if not isinstance(value, str) or projection.HEX40.fullmatch(value) is None:
        raise VerificationError("canonical source commit is not exact")
    return value


@contextlib.contextmanager
def canonical_verifier(tree: Path) -> Iterator[Any]:
    """Load only the verifier and public dependencies from the pinned tree."""
    script_dir = tree / "scripts"
    names = {path.stem for path in script_dir.glob("*.py")}
    previous = {name: sys.modules.pop(name) for name in names if name in sys.modules}
    sys.path.insert(0, str(script_dir))
    try:
        spec = importlib.util.spec_from_file_location(
            "_openadapt_pinned_release_verifier",
            script_dir / "verify_production_release_admission.py",
        )
        if spec is None or spec.loader is None:
            raise VerificationError("canonical release verifier is missing")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.path.remove(str(script_dir))
        for name in names:
            sys.modules.pop(name, None)
        sys.modules.update(previous)


class CanonicalStore:
    """Read exact Git objects without accepting caller-supplied transport URLs."""

    def __init__(self, directory: Path, verifier: Any, trees: dict[str, Path]):
        self.directory = directory
        self.verifier = verifier
        self.trees = trees
        self.registries: dict[str, tuple[dict, list]] = {}

    def tree(self, commit: str) -> Path:
        exact_commit(commit)
        if commit not in self.trees:
            path = self.directory / commit
            projection.materialize_commit(commit, path)
            self.trees[commit] = path
        return self.trees[commit]

    def registry(self, commit: str) -> tuple[dict, list]:
        if commit not in self.registries:
            value = json.loads((self.tree(commit) / "evidence-registry.json").read_bytes())
            entries = self.verifier.evidence.validate_registry(value)
            self.registries[commit] = value, entries
        return self.registries[commit]

    def reference(self, commit: str, entry: dict) -> dict:
        registry, _ = self.registry(commit)
        evidence = self.verifier.evidence
        return {
            "schema_version": evidence.REFERENCE_SCHEMA,
            "repository": evidence.REPOSITORY,
            "repository_id": evidence.REPOSITORY_ID,
            "repository_owner_id": evidence.REPOSITORY_OWNER_ID,
            "registry_source_commit": commit,
            "registry_revision": registry["revision"],
            "registry_head_sha256": registry["registry_head_sha256"],
            **entry,
        }

    def read(self, reference: dict) -> dict:
        reference = self.verifier.evidence.validate_reference(reference)
        commit = reference["registry_source_commit"]
        registry, entries = self.registry(commit)
        if (
            reference["registry_revision"] != registry["revision"]
            or reference["registry_head_sha256"] != registry["registry_head_sha256"]
        ):
            raise VerificationError("reference registry identity differs")
        self.verifier.evidence.require_registered(
            entries, reference=reference, label="verification record object"
        )
        return self.read_object(reference)

    def read_object(self, reference: dict, *, source_commit: str | None = None) -> dict:
        reference = self.verifier.evidence.validate_reference(reference)
        commit = source_commit or reference["registry_source_commit"]
        raw = (self.tree(commit) / reference["object_path"]).read_bytes()
        return self.verifier.verify_bytes(raw, reference, "verification record object")

    def bundle(self, reference: dict) -> dict:
        self.read(reference)
        commit = reference["registry_source_commit"]
        _, entries = self.registry(commit)
        index = next(i for i, entry in enumerate(entries)
                     if entry["registry_entry_sha256"] == reference["registry_entry_sha256"])
        if index + 1 >= len(entries):
            raise VerificationError("object has no adjacent signature bundle")
        bundle = self.reference(commit, entries[index + 1])
        self.verifier.trust.validate_reference_pair(reference, bundle, kind=reference["kind"])
        self.read(bundle)
        return bundle

    def pair(self, reference: dict, bundle: dict) -> dict:
        if self.bundle(reference) != bundle:
            raise VerificationError("signature bundle is not the exact adjacent entry")
        return self.read(reference)

    def fetch(self, url: str, **_kwargs: Any) -> bytes:
        prefix = "https://raw.githubusercontent.com/OpenAdaptAI/.github/"
        if not isinstance(url, str) or not url.startswith(prefix):
            raise VerificationError("offline verification refuses a non-canonical URL")
        commit, separator, path = url[len(prefix):].partition("/")
        exact_commit(commit)
        if (
            not separator or not path or "?" in path or "#" in path or "%" in path
            or any(part in {"", ".", ".."} for part in path.split("/"))
            or "\\" in path
        ):
            raise VerificationError("offline verification refuses a non-canonical path")
        return (self.tree(commit) / path).read_bytes()

    def verify_pair(self, reference: dict, bundle: dict, *, now: datetime) -> None:
        """Run the pinned DSSE route at retained time from immutable Git bytes.

        Authority v2 binds the raw signer registry digest. The canonical route
        handles that distinction and proves its unique historical reverse
        revocation link before it verifies the authority's outer signature.
        """
        self.pair(reference, bundle)
        value = self.read(bundle)
        envelope = value.get("dsseEnvelope")
        if not isinstance(envelope, dict) or envelope.get("payloadType") != (
            self.verifier.public_trust.STATEMENT_MEDIA_TYPE
        ):
            raise VerificationError("retained verification requires a public DSSE profile")

        class RetainedTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return now.astimezone(tz) if tz is not None else now.replace(tzinfo=None)

        previous_fetch, previous_datetime = self.verifier.fetch, self.verifier.datetime
        try:
            self.verifier.fetch = self.fetch
            self.verifier.datetime = RetainedTime
            pair = self.verifier.fetch_pair(reference, bundle)
            self.verifier.verify_registered_signature(
                reference, bundle, pair,
                policy=json.loads(self.verifier.POLICY_PATH.read_bytes()),
            )
        finally:
            self.verifier.fetch, self.verifier.datetime = previous_fetch, previous_datetime

    def current_state(self, commit: str) -> dict:
        registry, entries = self.registry(commit)
        result = {}
        for label, kind in (
            ("authority", "qualification-authority-state-receipt"),
            ("revocation", "qualification-revocation-state-receipt"),
        ):
            matches = [entry for entry in entries if entry["kind"] == kind]
            if not matches:
                raise VerificationError(f"verification state has no {kind}")
            reference = self.reference(commit, matches[-1])
            result[f"{label}_reference"] = reference
            result[f"{label}_bundle_reference"] = self.bundle(reference)
        self.signer(commit)
        result["signer_registry_pointer"] = registry["signer_registry"]
        return result

    def signer(self, commit: str) -> dict:
        registry, _ = self.registry(commit)
        pointer = registry["signer_registry"]
        if pointer is None:
            raise VerificationError("verification state has no signer registry")
        raw = (self.tree(commit) / pointer["object_path"]).read_bytes()
        signer = self.verifier.evidence.validate_signer_registry(json.loads(raw))
        if (
            projection._digest_bytes(raw) != pointer["object_sha256"]
            or raw != self.verifier.evidence.canonical(signer) + b"\n"
            or signer["revision"] != pointer["registry_revision"]
            or self.verifier.evidence.signer_registry_identity_digest(signer)
            != pointer["registry_identity_sha256"]
        ):
            raise VerificationError("verification signer registry bytes or identity differ")
        return signer


def latest_admissions(ledger: dict, store: CanonicalStore,
                      *, source_commit: str | None = None) -> dict[str, tuple[dict, dict]]:
    if ledger.get("schema_version") != projection.ADMISSIONS_SCHEMA:
        raise VerificationError("admissions ledger schema is not supported")
    result: dict[str, tuple[dict, dict]] = {}
    sequences: dict[str, set[int]] = {}
    unsupported_targets = set()
    for reference in ledger["admissions"]:
        # Legacy inline rows have no V2 verification record.
        if reference.get("kind") != "qualification-release":
            if isinstance(reference.get("target"), str):
                unsupported_targets.add(reference["target"])
            continue
        # Selection must retain a latest refusal without making older, unrelated
        # reference metadata a prerequisite for another target's verification.
        # A selected record must still pass read()/pair() in validate_record.
        admission = store.read_object(reference, source_commit=source_commit)
        target = admission["target"]
        sequence = admission["release_identity"]["sequence"]
        if type(sequence) is not int or sequence < 1:
            raise VerificationError("admission sequence is invalid")
        seen = sequences.setdefault(target, set())
        if sequence in seen:
            raise VerificationError("admission sequence is duplicated")
        seen.add(sequence)
        if target not in result or sequence > result[target][1]["release_identity"]["sequence"]:
            result[target] = reference, admission
    return {target: value for target, value in result.items() if target not in unsupported_targets}


def validate_record(record: dict, latest: dict, store: CanonicalStore) -> None:
    closed(record, RECORD_FIELDS, "verification record")
    if record["schema_version"] != RECORD_SCHEMA:
        raise VerificationError("verification record schema is not supported")
    target = record["target"]
    if target not in latest:
        raise VerificationError("verification target has no latest admission")
    reference, admission = latest[target]
    if record["admission_reference"] != reference:
        raise VerificationError("verification record does not bind the latest admission")
    store.pair(reference, record["admission_bundle_reference"])
    if admission.get("evidence_class") != "remote-safe-synthetic":
        raise VerificationError("verification evidence is not remote-safe-synthetic")
    receipt = record["verification_receipt"]
    if not isinstance(receipt, dict):
        raise VerificationError("verification receipt must be an object")
    instant = store.verifier.trust.require_timestamp(receipt["verified_at"], "verified_at")
    summary = store.pair(
        admission["production_acceptance_summary_reference"],
        admission["production_acceptance_summary_bundle_reference"],
    )
    evidence_chain = {
        kind: store.pair(summary[f"{kind}_reference"], summary[f"{kind}_bundle_reference"])
        for kind in ("production_acceptance_manifest", "qualification_evidence_decision_receipt")
    }
    qualification = store.pair(
        summary["qualification_admission_reference"],
        summary["qualification_admission_bundle_reference"],
    )
    expected_receipt = store.verifier.verification_receipt(
        admission=admission, admission_reference=reference,
        admission_bundle_reference=record["admission_bundle_reference"],
        summary=summary, qualification_admission=qualification,
        verified_at=instant,
        trust_state_source_commit=exact_commit(receipt["trust_state_source_commit"]),
    )
    if receipt != expected_receipt:
        raise VerificationError("closed canonical verification receipt differs")
    closed(record["current_state"], CURRENT_STATE_FIELDS, "verification current state")
    if record["current_state"] != store.current_state(receipt["trust_state_source_commit"]):
        raise VerificationError("verification state is not the exact current registered state")
    signer = store.signer(receipt["trust_state_source_commit"])
    store.verifier.trust.validate_release_evidence_chain(
        admission, summary=summary,
        manifest=evidence_chain["production_acceptance_manifest"],
        receipt=evidence_chain["qualification_evidence_decision_receipt"],
        qualification_admission=qualification, receipt_signer_registry=signer,
        now=instant,
    )
    store.verifier.trust.validate_admission_current_state(
        admission, admission_reference=reference,
        authority_state=store.read(record["current_state"]["authority_reference"]),
        revocation_state=store.read(record["current_state"]["revocation_reference"]),
        signer_registry=signer, now=instant,
    )
    pairs = [
        (reference, record["admission_bundle_reference"]),
        (admission["production_acceptance_summary_reference"],
         admission["production_acceptance_summary_bundle_reference"]),
        *((summary[f"{kind}_reference"], summary[f"{kind}_bundle_reference"])
          for kind in ("production_acceptance_manifest",
                       "qualification_evidence_decision_receipt", "qualification_admission")),
        *((record["current_state"][f"{kind}_reference"],
           record["current_state"][f"{kind}_bundle_reference"])
          for kind in ("authority", "revocation")),
    ]
    for regular, bundle in pairs:
        store.verify_pair(regular, bundle, now=instant)


def validate_document(document: dict, source: dict, latest: dict, store: CanonicalStore) -> None:
    closed(document, {"schema_version", "source_commit", "records"}, "verification document")
    if document["schema_version"] != DOCUMENT_SCHEMA:
        raise VerificationError("verification document schema is not supported")
    if document["source_commit"] != source["source_commit"]:
        raise VerificationError("verification source differs from the projection source")
    records = document["records"]
    if not isinstance(records, list):
        raise VerificationError("verification records must be an array")
    seen = set()
    for record in records:
        validate_record(record, latest, store)
        if record["target"] in seen:
            raise VerificationError("verification target is duplicated")
        seen.add(record["target"])
    if [record["target"] for record in records] != sorted(seen):
        raise VerificationError("verification records are not sorted by target")


def run_verifier(tree: Path, reference: dict, bundle: dict, admission: dict,
                 artifact_root: Path, *, python: str = sys.executable) -> dict:
    release = admission["release"]
    inventory = {
        "schema_version": "openadapt.production-release-artifact-inventory/v1",
        "target": admission["target"], "claim_scope": admission["claim_scope"],
        "artifacts": release["artifacts"],
    }
    with tempfile.TemporaryDirectory(prefix="openadapt-verification-caller-") as directory:
        path = Path(directory)
        for name, value in (("admission", reference), ("bundle", bundle), ("inventory", inventory)):
            (path / f"{name}.json").write_text(json.dumps(value), encoding="utf-8")
        command = [
            python, str(tree / "scripts" / "verify_production_release_admission.py"),
            "--admission-reference", str(path / "admission.json"),
            "--admission-bundle-reference", str(path / "bundle.json"),
            "--artifact-inventory", str(path / "inventory.json"),
            "--artifact-root", str(artifact_root.resolve()),
            "--expected-target", admission["target"],
            "--expected-repository", release["source_repository"],
            "--expected-repository-id", release["source_repository_id"],
            "--expected-source-commit", release["source_commit"],
        ]
        for name in ("version", "tag", "deployment_id", "deployment_sha256"):
            if release[name] is not None:
                command.extend([f"--expected-{name.replace('_', '-')}", release[name]])
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=600)
    if result.returncode:
        detail = (result.stderr or result.stdout or "verification failed").strip().splitlines()[-1]
        raise VerificationError(f"canonical release verifier refused: {detail}")
    receipt = json.loads(result.stdout)
    if not isinstance(receipt, dict) or receipt.get("verdict") != "verified":
        raise VerificationError("canonical release verifier returned no verified receipt")
    return receipt


def generate_record(target: str, latest: dict, store: CanonicalStore,
                    verifier_tree: Path, artifact_root: Path) -> dict:
    if target not in latest:
        raise VerificationError("requested target has no latest V2 admission")
    reference, admission = latest[target]
    bundle = store.bundle(reference)
    receipt = run_verifier(verifier_tree, reference, bundle, admission, artifact_root)
    record = {
        "schema_version": RECORD_SCHEMA, "target": target,
        "admission_reference": reference, "admission_bundle_reference": bundle,
        "verification_receipt": receipt,
        "current_state": store.current_state(exact_commit(receipt["trust_state_source_commit"])),
    }
    validate_record(record, latest, store)
    return record


def run_with_dependencies(tree: Path, directory: Path, argv: list[str]) -> int | None:
    """Keep the pinned dependency environment alive until the child exits."""
    python = projection._validator_python(tree, directory / "runtime")
    if python == sys.executable:
        return None
    result = subprocess.run(
        [python, str(Path(__file__).resolve()), *argv],
        check=False,
        timeout=900,
    )
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=projection.SOURCE_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--target", choices=sorted(projection.PUBLIC_TARGET_CONTRACT))
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.check and (args.target or args.artifact_root):
        parser.error("--check does not accept generation inputs")
    if not args.check and (not args.target or not args.artifact_root):
        parser.error("generation requires --target and --artifact-root")
    try:
        source = projection.load_source(args.source)
        with tempfile.TemporaryDirectory(prefix="openadapt-verification-") as temporary:
            directory = Path(temporary)
            tree = directory / source["source_commit"]
            projection.materialize_commit(source["source_commit"], tree)
            inputs = projection.read_pinned_files(source, tree)
            child_status = run_with_dependencies(
                tree, directory, sys.argv[1:] if argv is None else argv
            )
            if child_status is not None:
                return child_status
            with canonical_verifier(tree) as verifier:
                store = CanonicalStore(directory, verifier, {source["source_commit"]: tree})
                latest = latest_admissions(json.loads(inputs["admissions"]), store,
                                           source_commit=source["source_commit"])
                if args.output.exists():
                    document = json.loads(args.output.read_bytes())
                else:
                    if args.check:
                        raise VerificationError("verification document is missing")
                    document = {"schema_version": DOCUMENT_SCHEMA,
                                "source_commit": source["source_commit"], "records": []}
                if not args.check:
                    closed(document, {"schema_version", "source_commit", "records"}, "verification document")
                    if document["schema_version"] != DOCUMENT_SCHEMA or not isinstance(document["records"], list):
                        raise VerificationError("existing verification document is invalid")
                    exact_commit(document["source_commit"])
                    old_targets = [closed(r, RECORD_FIELDS, "verification record")["target"]
                                   for r in document["records"]]
                    if len(set(old_targets)) != len(old_targets):
                        raise VerificationError("verification target is duplicated")
                    document["records"] = [r for r in document["records"] if r.get("target") != args.target]
                    document["source_commit"] = source["source_commit"]
                    validate_document(document, source, latest, store)
                    record = generate_record(args.target, latest, store, tree, args.artifact_root)
                    document["records"] = sorted([*document["records"], record], key=lambda r: r["target"])
                validate_document(document, source, latest, store)
        if not args.check:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=args.output.parent,
                                             prefix=args.output.name + ".", delete=False) as handle:
                json.dump(document, handle, indent=2, sort_keys=True)
                handle.write("\n")
                pending = Path(handle.name)
            os.replace(pending, args.output)
        print("Verification records match the pinned evidence." if args.check else "Verification record written.")
    except (OSError, ValueError, KeyError, TypeError, ImportError, subprocess.SubprocessError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
