"""Tests for the exact public Production lifecycle projection."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "render_production_lifecycle", ROOT / "scripts" / "render_production_lifecycle.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _source() -> dict:
    commit = "a" * 40
    return {
        "schema_version": MODULE.SOURCE_SCHEMA,
        "repository": "OpenAdaptAI/.github",
        "source_commit": commit,
        "files": {
            key: {
                "path": path,
                "url": (
                    "https://raw.githubusercontent.com/OpenAdaptAI/.github/"
                    f"{commit}/{path}"
                ),
                "sha256": "sha256:" + f"{index:x}" * 64,
            }
            for index, (key, path) in enumerate(
                sorted(MODULE.EXPECTED_PATHS.items()), start=1
            )
        },
    }


def _inputs(admissions: list[dict] | None = None) -> dict[str, bytes]:
    target = {
        "id": "flow",
        "display_name": "OpenAdapt Flow",
        "lifecycle_scope": "repository",
        "lifecycle_subject": "openadapt-flow",
        "source_repository": "OpenAdaptAI/openadapt-flow",
        "release_kind": "public_package",
        "required_claim_scope": "qualified_workflow_runtime_release",
        "required_artifact_kinds": ["sdist", "wheel"],
        "package_index_project": "openadapt-flow",
        "artifact_authority_by_kind": {"sdist": "pypi", "wheel": "pypi"},
    }
    values = {
        "policy": {
            "schema_version": MODULE.POLICY_SCHEMA,
            "revision": 1,
            "maximum_admission_days": 30,
            "targets": [target],
        },
        "admissions": {
            "schema_version": MODULE.ADMISSIONS_SCHEMA,
            "policy_sha256": "sha256:" + "4" * 64,
            "admissions": admissions or [],
        },
    }
    return {key: json.dumps(value).encode() for key, value in values.items()}


class ProductionLifecycleProjectionTests(unittest.TestCase):
    def test_render_never_publishes_static_production_state(self) -> None:
        source = _source()
        source["files"]["policy"]["sha256"] = "sha256:" + "4" * 64
        output = MODULE.render(source, _inputs())

        self.assertEqual(
            output["derivation"],
            {
                "mode": "latest_signed_admission_at_read_time",
                "static_production_state": False,
                "expired_or_revoked_latest_behavior": "no_production",
                "fallback_to_older_release": False,
            },
        )
        self.assertIsNone(output["targets"][0]["latest_admission"])
        self.assertNotIn("status", output["targets"][0])
        self.assertNotIn("production_targets", output)

    def test_render_preserves_history_and_selects_highest_sequence(self) -> None:
        first = {
            "target": "flow",
            "release_identity": {"sequence": 1},
            "admission_id": "production:flow:1",
        }
        second = {
            "target": "flow",
            "release_identity": {"sequence": 2},
            "admission_id": "production:flow:2",
        }
        source = _source()
        source["files"]["policy"]["sha256"] = "sha256:" + "4" * 64
        output = MODULE.render(source, _inputs([second, first]))

        target = output["targets"][0]
        self.assertEqual(
            [item["admission_id"] for item in target["admission_history"]],
            ["production:flow:1", "production:flow:2"],
        )
        self.assertEqual(
            target["latest_admission"]["admission_id"], "production:flow:2"
        )

    def test_committed_projection_is_admission_free_and_schema_bound(self) -> None:
        output = json.loads(
            (ROOT / "docs" / "production-lifecycle.json").read_text(encoding="utf-8")
        )
        self.assertEqual(output["schema_version"], MODULE.OUTPUT_SCHEMA)
        self.assertEqual(
            output["$schema"], "schemas/production-lifecycle-public.schema.json"
        )
        self.assertTrue(
            (
                ROOT / "docs" / "schemas" / "production-lifecycle-public.schema.json"
            ).is_file()
        )
        self.assertFalse(output["derivation"]["static_production_state"])
        source = json.loads(
            (ROOT / "production-lifecycle-source.json").read_text(encoding="utf-8")
        )
        self.assertEqual(output["source"], source)
        self.assertEqual(len(output["targets"]), 7)
        for target in output["targets"]:
            self.assertIsNone(target["latest_admission"])
            self.assertEqual(target["admission_history"], [])

    def test_source_requires_exact_commit_bound_inventory(self) -> None:
        source = _source()
        source["files"]["policy"]["url"] = (
            "https://raw.githubusercontent.com/OpenAdaptAI/.github/main/"
            "production-lifecycle-policy.json"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.json"
            path.write_text(json.dumps(source))
            with self.assertRaisesRegex(MODULE.RenderError, "exact commit"):
                MODULE.load_source(path)

    def test_source_requires_the_complete_evidence_registry_contract(self) -> None:
        for key in (
            "evidence_registry",
            "evidence_registry_schema",
            "evidence_registry_validator",
        ):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                source = _source()
                source["files"].pop(key)
                path = Path(directory) / "source.json"
                path.write_text(json.dumps(source))
                with self.assertRaisesRegex(
                    MODULE.RenderError, "inventory is not exact"
                ):
                    MODULE.load_source(path)


if __name__ == "__main__":
    unittest.main()
