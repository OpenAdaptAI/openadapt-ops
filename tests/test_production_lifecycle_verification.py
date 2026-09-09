"""Test record selection and the canonical-verifier process boundary.

These tests exercise the Ops wrapper, not the canonical signature implementation.
Full generation invokes that separate public verifier with actual release bytes.
"""

from __future__ import annotations

import copy
import base64
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime, timezone
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "generate_production_lifecycle_verification",
    ROOT / "scripts" / "generate_production_lifecycle_verification.py",
)
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def admission(sequence: int = 1) -> dict:
    return {
        "target": "flow", "claim_scope": "production_flow",
        "evidence_class": "remote-safe-synthetic",
        "release_identity": {"sequence": sequence},
        "release": {
            "artifacts": [{"name": "candidate.whl"}],
            "source_repository": "OpenAdaptAI/openadapt-flow",
            "source_repository_id": "1291376938", "source_commit": "b" * 40,
            "version": "1.35.1", "tag": "v1.35.1",
            "deployment_id": None, "deployment_sha256": None,
        },
        "production_acceptance_summary_reference": {"id": "summary"},
        "production_acceptance_summary_bundle_reference": {"id": "summary-bundle"},
    }


class RecordTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = {"source_commit": "a" * 40}
        self.reference = {"kind": "qualification-release", "id": "latest"}
        self.admission = admission(2)
        self.summary = {
            f"{kind}_{suffix}": {"id": f"{kind}-{suffix}"}
            for kind in ("production_acceptance_manifest",
                         "qualification_evidence_decision_receipt", "qualification_admission")
            for suffix in ("reference", "bundle_reference")
        }
        self.receipt = {"verdict": "verified", "verified_at": "2026-09-09T18:50:00Z",
                        "trust_state_source_commit": "c" * 40, "version": "1.35.1"}
        self.state = {key: {"id": key} for key in module.CURRENT_STATE_FIELDS}
        self.record = {
            "schema_version": module.RECORD_SCHEMA, "target": "flow",
            "admission_reference": self.reference,
            "admission_bundle_reference": {"id": "latest-bundle"},
            "verification_receipt": copy.deepcopy(self.receipt),
            "current_state": copy.deepcopy(self.state),
        }
        self.latest = {"flow": (self.reference, self.admission)}
        self.store = Mock()
        self.store.pair.side_effect = lambda reference, bundle: (
            self.summary if reference == {"id": "summary"} else {}
        )
        self.store.verifier.trust.require_timestamp.side_effect = lambda value, label: value
        self.store.verifier.verification_receipt.return_value = self.receipt
        self.store.current_state.return_value = self.state

    def document(self, records=None) -> dict:
        return {"schema_version": module.DOCUMENT_SCHEMA, **self.source,
                "records": [self.record] if records is None else records}

    def test_check_keeps_retained_time_and_uses_canonical_chain_validation(self) -> None:
        document = self.document()
        before = copy.deepcopy(document)
        with patch.object(module, "run_verifier", side_effect=AssertionError("must not regenerate")):
            module.validate_document(document, self.source, self.latest, self.store)
        self.assertEqual(document, before)
        kwargs = self.store.verifier.verification_receipt.call_args.kwargs
        self.assertEqual(kwargs["verified_at"], self.receipt["verified_at"])
        self.store.verifier.trust.validate_release_evidence_chain.assert_called_once()
        self.store.verifier.trust.validate_admission_current_state.assert_called_once()
        self.assertEqual(self.store.verify_pair.call_count, 7)
        self.assertEqual({call.args[0]["id"] for call in self.store.verify_pair.call_args_list}, {
            "latest", "summary", "production_acceptance_manifest-reference",
            "qualification_evidence_decision_receipt-reference", "qualification_admission-reference",
            "authority_reference", "revocation_reference",
        })
        self.assertTrue(all(call.kwargs == {"now": self.receipt["verified_at"]}
                            for call in self.store.verify_pair.call_args_list))

    def test_latest_selection_never_falls_back_to_an_accepted_older_row(self) -> None:
        older = {"kind": "qualification-release", "id": "older"}
        newer = {"kind": "qualification-release", "id": "newer"}
        values = {"older": admission(1), "newer": {**admission(2), "verdict": "revoked"}}
        self.store.read_object.side_effect = lambda ref, **kwargs: values[ref["id"]]
        result = module.latest_admissions(
            {"schema_version": module.projection.ADMISSIONS_SCHEMA, "admissions": [newer, older]}, self.store
        )
        self.assertEqual(result["flow"][0], newer)

    def test_duplicate_sequences_refuse_instead_of_selecting_by_order(self) -> None:
        self.store.read_object.return_value = admission()
        with self.assertRaisesRegex(module.VerificationError, "sequence is duplicated"):
            module.latest_admissions(
                {"schema_version": module.projection.ADMISSIONS_SCHEMA,
                 "admissions": [self.reference, self.reference]}, self.store
            )

    def test_mixed_unsupported_admission_does_not_restore_a_v2_record(self) -> None:
        self.store.read_object.return_value = admission()
        latest = module.latest_admissions(
            {"schema_version": module.projection.ADMISSIONS_SCHEMA,
             "admissions": [self.reference, {"target": "flow", "sequence": 2}]}, self.store
        )
        self.assertNotIn("flow", latest)

    def test_stale_admission_wrong_state_receipt_and_extra_fields_refuse(self) -> None:
        mutations = (
            (lambda r: r.update(admission_reference={"id": "older"}), "latest admission"),
            (lambda r: r["current_state"].update(authority_reference={"id": "older"}), "current registered"),
            (lambda r: r["verification_receipt"].update(version="1.34.0"), "receipt differs"),
            (lambda r: r.update(active=True), "fields differ"),
            (lambda r: r["current_state"].update(active=True), "fields differ"),
        )
        for change, message in mutations:
            with self.subTest(message=message):
                record = copy.deepcopy(self.record)
                change(record)
                with self.assertRaisesRegex(module.VerificationError, message):
                    module.validate_record(record, self.latest, self.store)

    def test_wrong_source_and_duplicate_target_refuse(self) -> None:
        wrong_source = self.document()
        wrong_source["source_commit"] = "d" * 40
        with self.assertRaisesRegex(module.VerificationError, "projection source"):
            module.validate_document(wrong_source, self.source, self.latest, self.store)
        with self.assertRaisesRegex(module.VerificationError, "target is duplicated"):
            module.validate_document(self.document([self.record, self.record]),
                                     self.source, self.latest, self.store)

    def test_empty_records_make_no_verification_claim(self) -> None:
        module.validate_document(self.document([]), self.source, {}, self.store)
        self.store.verifier.verification_receipt.assert_not_called()

    def test_evidence_class_is_independent_of_release_version(self) -> None:
        self.admission["evidence_class"] = "customer-production"
        with self.assertRaisesRegex(module.VerificationError, "remote-safe-synthetic"):
            module.validate_record(self.record, self.latest, self.store)

    def test_generation_never_returns_a_record_after_canonical_refusal(self) -> None:
        with patch.object(module, "run_verifier", side_effect=module.VerificationError("refused")):
            with self.assertRaisesRegex(module.VerificationError, "refused"):
                module.generate_record("flow", self.latest, self.store, Path("/verifier"), Path("/artifacts"))
        self.store.current_state.assert_not_called()


class CanonicalStoreTests(unittest.TestCase):
    def test_offline_fetch_refuses_other_origins_mutable_commits_and_paths(self) -> None:
        store = module.CanonicalStore(Path("/unused"), None, {})
        for url in (
            "https://example.com/object.json",
            "https://raw.githubusercontent.com/OpenAdaptAI/.github/main/object.json",
            "https://raw.githubusercontent.com/OpenAdaptAI/.github/" + "a" * 40 + "/../secret",
            "https://raw.githubusercontent.com/OpenAdaptAI/.github/" + "a" * 40 + "/%2e%2e/secret",
        ):
            with self.subTest(url=url), self.assertRaises(module.VerificationError):
                store.fetch(url)

    def test_outer_failure_restores_verifier_fetch_and_clock(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            policy = Path(directory) / "policy.json"
            policy.write_text("{}")
            original_fetch = Mock()
            verifier = SimpleNamespace(
                fetch=original_fetch, datetime=datetime, POLICY_PATH=policy,
                public_trust=SimpleNamespace(STATEMENT_MEDIA_TYPE="public-dsse"),
                fetch_pair=Mock(return_value=()),
                verify_registered_signature=Mock(side_effect=ValueError("invalid signature")),
            )
            store = module.CanonicalStore(Path(directory), verifier, {})
            store.pair = Mock()
            store.read = Mock(return_value={"dsseEnvelope": {"payloadType": "public-dsse"}})
            with self.assertRaisesRegex(ValueError, "invalid signature"):
                store.verify_pair({}, {}, now=datetime(2026, 9, 9, tzinfo=timezone.utc))
            self.assertIs(verifier.fetch, original_fetch)
            self.assertIs(verifier.datetime, datetime)

    def test_outer_verification_refuses_a_keyless_profile_without_dispatch(self) -> None:
        verifier = SimpleNamespace(
            public_trust=SimpleNamespace(STATEMENT_MEDIA_TYPE="public-dsse"), fetch_pair=Mock()
        )
        store = module.CanonicalStore(Path("/unused"), verifier, {})
        store.pair = Mock()
        store.read = Mock(return_value={"dsseEnvelope": {"payloadType": "keyless"}})
        with self.assertRaisesRegex(module.VerificationError, "public DSSE profile"):
            store.verify_pair({}, {}, now=datetime(2026, 9, 9, tzinfo=timezone.utc))
        verifier.fetch_pair.assert_not_called()

    def test_current_state_uses_last_relevant_entries_and_adjacent_bundles(self) -> None:
        verifier = SimpleNamespace(evidence=SimpleNamespace(
            REFERENCE_SCHEMA="reference/v2", REPOSITORY="OpenAdaptAI/.github",
            REPOSITORY_ID="858454062", REPOSITORY_OWNER_ID="132681217",
        ))
        store = module.CanonicalStore(Path("/unused"), verifier, {})
        entries = [
            {"kind": "qualification-authority-state-receipt", "id": "authority-older"},
            {"kind": "qualification-revocation-state-receipt", "id": "revocation-older"},
            {"kind": "qualification-authority-state-receipt", "id": "authority-current"},
            {"kind": "qualification-revocation-state-receipt", "id": "revocation-current"},
            {"kind": "qualification-release", "id": "unrelated"},
        ]
        registry = {"revision": 9, "registry_head_sha256": "sha256:" + "f" * 64,
                    "signer_registry": {"id": "current-signer"}}
        store.registry = Mock(return_value=(registry, entries))
        store.signer = Mock(return_value={})
        store.bundle = Mock(side_effect=lambda reference: {"subject": reference["id"]})
        state = store.current_state("a" * 40)
        self.assertEqual(state["authority_reference"]["id"], "authority-current")
        self.assertEqual(state["revocation_reference"]["id"], "revocation-current")
        self.assertEqual(state["authority_bundle_reference"], {"subject": "authority-current"})
        self.assertEqual(state["signer_registry_pointer"], {"id": "current-signer"})
        self.assertEqual(state["authority_reference"]["registry_source_commit"], "a" * 40)


def check_retained_signed_pairs(tree: Path) -> None:
    """Use the pinned upstream fixture's unchanged real public signatures."""
    with module.canonical_verifier(tree) as verifier:
        spec = importlib.util.spec_from_file_location(
            "_canonical_signed_fixture", tree / "tests" / "test_registered_software_verifier.py"
        )
        fixture_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture_module)
        fixture = fixture_module.RegisteredSoftwareVerifierTests()
        fixture.setUp()
        try:
            with tempfile.TemporaryDirectory(prefix="ops-signed-fixture-") as directory:
                root = Path(directory)
                def store_files():
                    for name, raw in fixture.files.items():
                        path = root / name
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_bytes(raw)
                    (root / "evidence-registry.json").write_bytes(fixture_module.canonical(fixture.registry))
                    return module.CanonicalStore(root, verifier, {fixture_module.STORAGE_COMMIT: root})

                instant = datetime(2026, 9, 9, 18, 50, tzinfo=timezone.utc)
                store = store_files()
                for digest in (fixture_module.RELEASE_SHA, fixture_module.AUTHORITY_SHA,
                               fixture_module.REVOCATION_SHA):
                    reference = fixture.reference(digest)
                    store.verify_pair(reference, store.bundle(reference), now=instant)
                reference = fixture.reference(fixture_module.RELEASE_SHA)
                release = store.read(reference)
                summary = json.loads((tree / release["production_acceptance_summary_reference"]["object_path"]).read_bytes())
                qualification = json.loads((tree / summary["qualification_admission_reference"]["object_path"]).read_bytes())

                def receipt(current_store):
                    current_ref = fixture.reference(fixture_module.RELEASE_SHA)
                    return verifier.verification_receipt(
                        admission=release, admission_reference=current_ref,
                        admission_bundle_reference=current_store.bundle(current_ref),
                        summary=summary, qualification_admission=qualification,
                        verified_at=instant, trust_state_source_commit=fixture_module.STORAGE_COMMIT,
                    )

                before = receipt(store)
                fixture.replace_bundle(fixture_module.RELEASE_SHA, lambda bundle: (
                    bundle["dsseEnvelope"]["signatures"][0].update(
                        sig=base64.b64encode(bytes(64)).decode()
                    )
                ))
                store = store_files()
                after = receipt(store)
                assert before["verification_id_sha256"] != after["verification_id_sha256"]
                reference = fixture.reference(fixture_module.RELEASE_SHA)
                bundle = store.bundle(reference)
                # Byte, semantic identity, registry, adjacency, and receipt hashes
                # have all been recomputed. Only the signature check rejects it.
                store.pair(reference, bundle)
                try:
                    store.verify_pair(reference, bundle, now=instant)
                except verifier.trust.TrustError as exc:
                    assert "signature" in str(exc).lower(), str(exc)
                else:
                    raise AssertionError("corrupted registered outer signature was accepted")
        finally:
            fixture.doCleanups()


class SignedPairIntegrationTests(unittest.TestCase):
    def test_retained_signatures_and_rehashed_corrupt_bundle(self) -> None:
        # Pin public fixture and verifier code together. Reuse the same dependency
        # selection as the command; no private signing key or service is needed.
        commit = "f0fb9cc812c0d1653b1ec2998749b078f244308e"
        with tempfile.TemporaryDirectory(prefix="ops-signed-verifier-") as directory:
            root = Path(directory)
            tree = root / commit
            module.projection.materialize_commit(commit, tree)
            python = module.projection._validator_python(tree, root / "runtime")
            result = subprocess.run(
                [python, "-c", "import runpy,sys; from pathlib import Path; "
                 "runpy.run_path(sys.argv[1])['check_retained_signed_pairs'](Path(sys.argv[2]))",
                 str(Path(__file__).resolve()), str(tree)],
                capture_output=True, text=True, check=False, timeout=120,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class VerifierProcessTests(unittest.TestCase):
    def test_dependency_reexecution_preserves_arguments_and_exit_status(self) -> None:
        args = ["--check", "--source", "source with spaces.json", "--output", "output.json"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tree = root / "exact-canonical-tree"
            for status in (0, 7):
                with self.subTest(status=status), patch.object(
                    module.projection, "_validator_python", return_value="/pinned/venv/bin/python"
                ) as selector, patch.object(
                    module.subprocess, "run", return_value=subprocess.CompletedProcess([], status)
                ) as runner:
                    self.assertEqual(module.run_with_dependencies(tree, root, args), status)
                    selector.assert_called_once_with(tree, root / "runtime")
                    runner.assert_called_once_with(
                        ["/pinned/venv/bin/python", str(Path(module.__file__).resolve()), *args],
                        check=False, timeout=900,
                    )

    def test_current_interpreter_does_not_start_another_process(self) -> None:
        with patch.object(module.projection, "_validator_python", return_value=sys.executable), patch.object(
            module.subprocess, "run"
        ) as runner:
            self.assertIsNone(module.run_with_dependencies(Path("/tree"), Path("/runtime"), ["--check"]))
        runner.assert_not_called()

    def test_subprocess_receives_exact_pinned_verifier_identity_and_inventory(self) -> None:
        # A real subprocess checks the wrapper's CLI contract. Signature checking
        # remains the canonical verifier's contract and is not simulated here.
        with tempfile.TemporaryDirectory() as directory:
            tree = Path(directory)
            (tree / "scripts").mkdir()
            (tree / "scripts" / "verify_production_release_admission.py").write_text(
                "import json,sys\n"
                "from pathlib import Path\n"
                "args=dict(zip(sys.argv[1::2],sys.argv[2::2]))\n"
                "inventory=json.loads(Path(args['--artifact-inventory']).read_text())\n"
                "assert inventory['artifacts']==[{'name':'candidate.whl'}]\n"
                "assert args['--expected-version']=='1.35.1'\n"
                "assert args['--expected-source-commit']=='b'*40\n"
                "assert '--expected-deployment-id' not in args\n"
                "assert json.loads(Path(args['--admission-reference']).read_text())=={'id':'admission'}\n"
                "print(json.dumps({'verdict':'verified'}))\n", encoding="utf-8"
            )
            result = module.run_verifier(tree, {"id": "admission"}, {"id": "bundle"},
                                         admission(), tree / "artifacts", python=sys.executable)
            self.assertEqual(result, {"verdict": "verified"})

    def test_nonzero_exit_and_non_receipt_output_refuse(self) -> None:
        for result, message in (
            (subprocess.CompletedProcess([], 1, "", "REFUSED: stale state"), "stale state"),
            (subprocess.CompletedProcess([], 0, '{"verdict":"refused"}', ""), "no verified receipt"),
        ):
            with self.subTest(message=message), patch.object(module.subprocess, "run", return_value=result):
                with self.assertRaisesRegex(module.VerificationError, message):
                    module.run_verifier(Path("/verifier"), {}, {}, admission(), Path("/artifacts"))


if __name__ == "__main__":
    unittest.main()
