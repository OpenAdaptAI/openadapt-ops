"""Tests for the public source and generated-site boundary."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_source_boundary as guard  # noqa: E402

CI_WORKFLOW = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
SYNC_WORKFLOW = (ROOT / ".github/workflows/sync.yml").read_text(encoding="utf-8")


@pytest.fixture()
def policy() -> guard.SourcePolicy:
    return guard.load_policy()


def _repository(tmp_path: Path, relative: str, content: bytes) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    subprocess.run(["git", "add", relative], cwd=tmp_path, check=True)
    return tmp_path


def _policy_document() -> dict:
    return json.loads(guard.POLICY_PATH.read_text(encoding="utf-8"))


def test_repository_policy_is_public_and_complete() -> None:
    document = _policy_document()
    repository = document["public_repositories"][guard.REPOSITORY_NAME]
    assert repository["classification"] == "public"
    assert repository["slug"] == guard.REPOSITORY_SLUG
    assert set(repository["must_not_contain"]) == set(
        document["crown_jewel_categories"]
    )


def test_this_repository_source_passes(policy: guard.SourcePolicy) -> None:
    assert guard.scan_tracked_source(ROOT, policy) == []


def test_missing_policy_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(guard.PolicyError, match="cannot read"):
        guard.load_policy(tmp_path / "missing.json")


def test_invalid_policy_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "policy.json"
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(guard.PolicyError, match="not valid JSON"):
        guard.load_policy(path)


def test_missing_repository_classification_fails_closed() -> None:
    document = _policy_document()
    del document["public_repositories"][guard.REPOSITORY_NAME]
    with pytest.raises(guard.PolicyError, match=guard.REPOSITORY_NAME):
        guard.SourcePolicy.from_document(document)


def test_missing_build_content_patterns_fails_closed() -> None:
    document = _policy_document()
    del document["enforcement"]["built_artifacts"]["content_patterns"]
    with pytest.raises(guard.PolicyError, match="content_patterns"):
        guard.SourcePolicy.from_document(document)


def test_missing_policy_digest_fails_closed() -> None:
    document = _policy_document()
    del document["policy_digest"]
    with pytest.raises(guard.PolicyError, match="policy_digest"):
        guard.SourcePolicy.from_document(document)


def test_tracked_source_rejects_an_innocently_named_tuning_file(
    tmp_path: Path, policy: guard.SourcePolicy
) -> None:
    root = _repository(
        tmp_path,
        "docs/notes.txt",
        b"deployment-derived threshold = 0.82\n",
    )
    violations = guard.scan_tracked_source(root, policy)
    assert any("build-content pattern" in item for item in violations)


def test_generated_site_rejects_an_innocently_named_tuning_file(
    tmp_path: Path, policy: guard.SourcePolicy
) -> None:
    site = tmp_path / "site"
    site.mkdir()
    (site / "notes.txt").write_text(
        "deployment-derived threshold = 0.82\n", encoding="utf-8"
    )
    violations = guard.scan_generated_site(site, policy)
    assert any("build-content pattern" in item for item in violations)


def test_generated_site_rejects_a_denylisted_path(
    tmp_path: Path, policy: guard.SourcePolicy
) -> None:
    site = tmp_path / "site"
    path = site / "assets" / "customer_recipe" / "notes.txt"
    path.parent.mkdir(parents=True)
    path.write_text("placeholder\n", encoding="utf-8")
    violations = guard.scan_generated_site(site, policy)
    assert any("denylisted token" in item for item in violations)


def test_generated_site_rejects_a_private_signature(
    tmp_path: Path, policy: guard.SourcePolicy
) -> None:
    site = tmp_path / "site"
    site.mkdir()
    (site / "artifact.bin").write_bytes(b"prefix" + policy.content_signatures[0])
    violations = guard.scan_generated_site(site, policy)
    assert any("private-artifact signature" in item for item in violations)


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlinks are unavailable")
def test_generated_site_rejects_a_symbolic_link(
    tmp_path: Path, policy: guard.SourcePolicy
) -> None:
    site = tmp_path / "site"
    site.mkdir()
    target = tmp_path / "outside.txt"
    target.write_text("outside\n", encoding="utf-8")
    os.symlink(target, site / "linked.txt")
    violations = guard.scan_generated_site(site, policy)
    assert any("symbolic link" in item for item in violations)


def test_missing_generated_site_fails_closed(
    tmp_path: Path, policy: guard.SourcePolicy
) -> None:
    with pytest.raises(guard.ScanError, match="does not exist"):
        guard.scan_generated_site(tmp_path / "missing", policy)


def test_ci_scans_source_and_the_complete_generated_site() -> None:
    assert "python scripts/check_source_boundary.py\n" in CI_WORKFLOW
    build = CI_WORKFLOW.index("mkdocs build --strict")
    generated_guard = CI_WORKFLOW.index(
        "python scripts/check_source_boundary.py --site site"
    )
    assert build < generated_guard


def test_sync_scans_generated_output_before_pr_or_deploy() -> None:
    prepare = SYNC_WORKFLOW.split("  prepare-sync:\n", 1)[1].split(
        "  deploy-main:\n", 1
    )[0]
    deploy = SYNC_WORKFLOW.split("  deploy-main:\n", 1)[1]

    prepare_build = prepare.index("mkdocs build --strict")
    prepare_guard = prepare.index("python scripts/check_source_boundary.py --site site")
    prepare_pr = prepare.index("Record the generated docs source")
    assert prepare_build < prepare_guard < prepare_pr

    deploy_build = deploy.index("mkdocs build --strict")
    deploy_guard = deploy.index("python scripts/check_source_boundary.py --site site")
    upload = deploy.index("actions/upload-pages-artifact")
    publication = deploy.index("actions/deploy-pages")
    assert deploy_build < deploy_guard < upload < publication
