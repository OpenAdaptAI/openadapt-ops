"""Fail-closed public projection of the workflow-admission ledger."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "render_production_workflow_admissions",
    ROOT / "scripts" / "render_production_workflow_admissions.py",
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

PINNED_COMMIT = "078db7a9399702d0b725676e4a427b1b52fb19ff"
PINNED_LEDGER_SHA256 = (
    "sha256:fa3b4cc4ed0ab62d8d4ff5705495ec0a82f0572654617a152fd9675818684150"
)


def _source() -> dict:
    return {
        "schema_version": MODULE.SOURCE_SCHEMA,
        "repository": "OpenAdaptAI/.github",
        "source_commit": PINNED_COMMIT,
        "files": {
            "admissions": {
                "path": "production-workflow-admissions.json",
                "url": (
                    "https://raw.githubusercontent.com/OpenAdaptAI/.github/"
                    f"{PINNED_COMMIT}/production-workflow-admissions.json"
                ),
                "sha256": PINNED_LEDGER_SHA256,
            }
        },
    }


class ProductionWorkflowAdmissionsProjectionTests(unittest.TestCase):
    def test_committed_projection_lists_seven_inactive_synthetic_records(self) -> None:
        source = json.loads(
            (ROOT / "production-workflow-admissions-source.json").read_text(
                encoding="utf-8"
            )
        )
        projection = json.loads(
            (ROOT / "docs" / "production-workflow-admissions.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(source["source_commit"], PINNED_COMMIT)
        self.assertEqual(
            source["files"]["admissions"]["sha256"], PINNED_LEDGER_SHA256
        )
        self.assertEqual(projection["source"], source)
        self.assertEqual(projection["schema_version"], MODULE.OUTPUT_SCHEMA)
        self.assertEqual(len(projection["admissions"]), 7)
        for row in projection["admissions"]:
            self.assertEqual(row["kind"], "qualification-admission")
            self.assertEqual(row["evidence_class"], "remote-safe-synthetic")
            self.assertEqual(row["bundle_version"], "0.0.0-synthetic")
            self.assertEqual(row["verdict"], "accepted")
            self.assertIsNone(row["expires_at"])
        encoded = json.dumps(projection)
        self.assertNotIn("mockmed", encoded.lower())
        self.assertNotIn("MockMed production_acceptance", encoded)

    def test_source_requires_exact_commit_bound_inventory(self) -> None:
        source = _source()
        source["files"]["admissions"]["url"] = (
            "https://raw.githubusercontent.com/OpenAdaptAI/.github/main/"
            "production-workflow-admissions.json"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.json"
            path.write_text(json.dumps(source))
            with self.assertRaisesRegex(MODULE.RenderError, "exact commit"):
                MODULE.load_source(path)

    def test_render_refuses_object_digest_drift(self) -> None:
        ledger = {
            "$schema": "schemas/production-workflow-admissions.schema.json",
            "schema_version": MODULE.LEDGER_SCHEMA,
            "policy_sha256": "sha256:" + "a" * 64,
            "admissions": [
                {
                    "kind": "qualification-admission",
                    "object_path": "production-evidence/objects/sha256/aa/bb.qualification-admission.json",
                    "object_sha256": "sha256:" + "b" * 64,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            tree = Path(directory)
            object_path = tree / ledger["admissions"][0]["object_path"]
            object_path.parent.mkdir(parents=True, exist_ok=True)
            object_path.write_text('{"evidence_class": "remote-safe-synthetic"}')
            with self.assertRaisesRegex(MODULE.RenderError, "object digest changed"):
                MODULE.render(
                    _source(),
                    {"admissions": json.dumps(ledger).encode()},
                    tree=tree,
                )

    def test_render_refuses_non_synthetic_evidence_class(self) -> None:
        admission = {
            "bundle_version": "0.0.0-synthetic",
            "evidence_class": "customer-production",
            "expires_at": None,
            "verdict": "accepted",
        }
        body = json.dumps(admission).encode()
        digest = MODULE._digest_bytes(body)
        object_rel = (
            "production-evidence/objects/sha256/aa/"
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            ".qualification-admission.json"
        )
        ledger = {
            "$schema": "schemas/production-workflow-admissions.schema.json",
            "schema_version": MODULE.LEDGER_SCHEMA,
            "policy_sha256": "sha256:" + "a" * 64,
            "admissions": [
                {
                    "kind": "qualification-admission",
                    "object_path": object_rel,
                    "object_sha256": digest,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            tree = Path(directory)
            path = tree / object_rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
            with self.assertRaisesRegex(MODULE.RenderError, "evidence class"):
                MODULE.render(
                    _source(),
                    {"admissions": json.dumps(ledger).encode()},
                    tree=tree,
                )


class ProductionWorkflowAdmissionsCopyTests(unittest.TestCase):
    def test_llms_names_public_synthetic_ledger_not_a_customer_job(self) -> None:
        text = (ROOT / "docs" / "llms.txt").read_text(encoding="utf-8")
        self.assertIn(
            "A Production run still needs an active admission for the exact "
            "workflow version",
            text,
        )
        self.assertIn("no target is actively admitted", text)
        self.assertIn("null expiry", text)
        self.assertIn("0.0.0-synthetic", text)
        self.assertIn("remote-safe-synthetic", text)
        self.assertIn("production-workflow-admissions.json", text)
        self.assertIn(PINNED_COMMIT, text)
        self.assertIn("aren't customer workflows", text)
        self.assertNotIn("customer job is admitted", text.lower())
        self.assertNotIn("MockMed production_acceptance", text)

    def test_lifecycle_page_names_public_synthetic_ledger(self) -> None:
        text = (ROOT / "docs" / "reference" / "production-lifecycle.md").read_text(
            encoding="utf-8"
        )
        collapsed = " ".join(text.split())
        self.assertIn("0.0.0-synthetic", text)
        self.assertIn("production-workflow-admissions.json", text)
        self.assertIn(PINNED_COMMIT, text)
        self.assertIn("aren't customer workflows", collapsed)
        self.assertIn("none is actively admitted", collapsed)
        self.assertIn("seven Production targets", text)
        self.assertNotIn("MockMed production_acceptance", text)


if __name__ == "__main__":
    unittest.main()
