import copy
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("private_database_backup_freshness", SCRIPTS / "private_database_backup_freshness.py")
freshness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(freshness)
transport = freshness.transport
NOW = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)
SOURCE = "a" * 40
PRIVATE = {"full_name": transport.REPOSITORY, "private": True, "visibility": "private",
           "archived": False, "disabled": False}


def iso(value):
    return value.isoformat().replace("+00:00", "Z")


class FakeGitHub:
    """Read-only fixtures. Downloading ciphertext or any mutation fails a test."""

    def __init__(self):
        self.calls = []
        self.downloads = []
        self.private = copy.deepcopy(PRIVATE)
        self.release = {"id": 42, "tag_name": "database-backup-20260909T113000Z-" + "f" * 32,
                        "draft": False, "prerelease": False, "target_commitish": SOURCE,
                        "published_at": "2026-09-09T11:30:00Z", "updated_at": iso(NOW)}
        self.releases = [self.release]
        artifact = {
            "backup_contract_sha256": "b" * 64,
            "plaintext_archive": {"bytes": 200, "sha256": "c" * 64},
            "ciphertext_archive": {"bytes": 300, "sha256": "d" * 64},
            "repository_commit": "e" * 40, "workflow_run_id": None,
            "local_execution": {"id": "12345678-1234-1234-1234-123456789abc", "scope": "production",
                                "created_at": iso(NOW - timedelta(hours=2))},
        }
        self.manifest = {"schema": transport.contract.ARTIFACT_SCHEMA, "artifact": artifact}
        self.rebuild()

    def rebuild(self):
        self.manifest["artifact_sha256"] = transport.contract.sha256_text(
            transport.contract.stable_json(self.manifest["artifact"]))
        self.data = json.dumps(self.manifest).encode()
        self.asset_list = [
            {"id": 101, "name": transport.ASSET_NAMES[0], "size": 300, "digest": "sha256:" + "d" * 64,
             "state": "uploaded"},
            {"id": 102, "name": transport.ASSET_NAMES[1], "size": len(self.data),
             "digest": "sha256:" + hashlib.sha256(self.data).hexdigest(), "state": "uploaded"},
        ]

    def api(self, endpoint, *, method="GET", payload=None):
        assert method == "GET" and payload is None
        assert endpoint.startswith(transport.API_ROOT)
        self.calls.append(endpoint)
        if endpoint == transport.API_ROOT:
            return copy.deepcopy(self.private)
        if endpoint == f"{transport.API_ROOT}/releases?per_page=100&page=1":
            return copy.deepcopy(self.releases)
        if endpoint == f"{transport.API_ROOT}/releases/42":
            return copy.deepcopy(self.release)
        if "/git/ref/tags/" in endpoint:
            return {"object": {"type": "commit", "sha": SOURCE}}
        pytest.fail("unexpected API endpoint")

    def assets(self, release_id):
        assert release_id == 42
        return copy.deepcopy(self.asset_list)

    def download(self, asset_id, path):
        assert asset_id == 102, "the hourly check must never download ciphertext"
        transport.private_path(path.parent, directory=True)
        self.downloads.append(asset_id)
        path.write_bytes(self.data)
        path.chmod(0o600)


def test_fresh_backup_reads_only_manifest_and_reports_no_application_data():
    github = FakeGitHub()
    result = freshness.check(github=github, now=NOW)
    assert result == {"schema": "openadapt.database-backup-github-freshness/v1", "fresh": True,
                      "age_seconds": 7200, "maximum_age_seconds": 93600,
                      "release_id": 42, "ciphertext_downloaded": False}
    assert github.downloads == [102]
    assert github.calls[0] == github.calls[-1] == transport.API_ROOT


@pytest.mark.parametrize("seconds, succeeds", [(93600, True), (93601, False), (-1, False)])
def test_age_uses_capture_time_and_refuses_stale_or_future(seconds, succeeds):
    github = FakeGitHub()
    github.manifest["artifact"]["local_execution"]["created_at"] = iso(NOW - timedelta(seconds=seconds))
    github.rebuild()
    if succeeds:
        assert freshness.check(github=github, now=NOW)["age_seconds"] == seconds
    else:
        with pytest.raises(transport.contract.ContractError):
            freshness.check(github=github, now=NOW)


def test_release_update_and_new_draft_do_not_refresh_an_old_backup():
    github = FakeGitHub()
    github.manifest["artifact"]["local_execution"]["created_at"] = iso(NOW - timedelta(hours=27))
    github.rebuild()
    github.releases.insert(0, {**github.release, "id": 43, "draft": True, "published_at": None,
                               "updated_at": iso(NOW)})
    with pytest.raises(transport.contract.ContractError, match="older than 26 hours"):
        freshness.check(github=github, now=NOW)


@pytest.mark.parametrize("mutation", [
    lambda g: g.releases.clear(),
    lambda g: g.release.update(draft=True),
    lambda g: g.release.update(draft="false"),
    lambda g: g.release.update(prerelease=True),
    lambda g: g.release.update(published_at="not-a-time"),
    lambda g: g.release.update(published_at=iso(NOW + timedelta(seconds=1))),
    lambda g: g.release.update(published_at="2026-09-09T10:00:00"),
    lambda g: g.release.update(tag_name="database-backup-20260999T113000Z-" + "f" * 32),
    lambda g: g.release.update(tag_name="database-backup-invalid"),
    lambda g: g.release.update(target_commitish="main"),
])
def test_missing_draft_invalid_or_future_release_fails(mutation):
    github = FakeGitHub()
    mutation(github)
    with pytest.raises((transport.contract.ContractError, ValueError)):
        freshness.check(github=github, now=NOW)


@pytest.mark.parametrize("mutation", [
    lambda m: m["artifact"]["local_execution"].update(scope="synthetic"),
    lambda m: m["artifact"]["local_execution"].update(created_at="invalid"),
    lambda m: m["artifact"].update(ciphertext_archive={"bytes": 300, "sha256": "9" * 64}),
    lambda m: m["artifact"].update(ciphertext_archive={"bytes": 301, "sha256": "d" * 64}),
    lambda m: m.update(customer_details="must-never-appear"),
    lambda m: m["artifact"].update(workflow_run_id=9000),
])
def test_manifest_scope_shape_and_ciphertext_binding_fail_closed(mutation):
    github = FakeGitHub()
    mutation(github.manifest)
    github.rebuild()
    with pytest.raises(transport.contract.ContractError):
        freshness.check(github=github, now=NOW)


@pytest.mark.parametrize("mutation", [
    lambda a: a.pop(),
    lambda a: a.append(copy.deepcopy(a[0])),
    lambda a: a[1].update(name="local-verification.json"),
    lambda a: a[1].update(id=101),
    lambda a: a[1].update(state="starter"),
    lambda a: a[1].update(digest=None),
    lambda a: a[1].update(size=65537),
    lambda a: a[0].update(size=transport.ASSET_LIMIT),
])
def test_incomplete_or_unsafe_assets_fail_before_download(mutation):
    github = FakeGitHub()
    mutation(github.asset_list)
    with pytest.raises(transport.contract.ContractError):
        freshness.check(github=github, now=NOW)
    assert not github.downloads


def test_tampered_download_and_invalid_manifest_digest_fail():
    github = FakeGitHub()
    github.data = github.data[:-1] + b"!"
    with pytest.raises(transport.contract.ContractError, match="downloaded manifest digest"):
        freshness.check(github=github, now=NOW)
    github = FakeGitHub()
    github.manifest["artifact_sha256"] = "0" * 64
    github.data = json.dumps(github.manifest).encode()
    github.asset_list[1]["digest"] = "sha256:" + hashlib.sha256(github.data).hexdigest()
    with pytest.raises(transport.contract.ContractError, match="schema or digest"):
        freshness.check(github=github, now=NOW)


def test_invalid_newest_publication_does_not_fall_back_to_an_older_backup():
    github = FakeGitHub()
    github.releases.append({**github.release, "id": 41, "published_at": "2026-09-09T09:00:00Z"})
    github.asset_list.pop()
    with pytest.raises(transport.contract.ContractError, match="incomplete"):
        freshness.check(github=github, now=NOW)
    assert not any(endpoint.endswith("/releases/41") for endpoint in github.calls)


@pytest.mark.parametrize("mutation", [
    {"private": False}, {"visibility": "public"}, {"visibility": "internal"},
    {"full_name": "OpenAdaptAI/openadapt-ops"},
])
def test_private_repository_boundary_precedes_any_artifact_access(mutation):
    github = FakeGitHub()
    github.private.update(mutation)
    with pytest.raises(transport.contract.ContractError, match="private"):
        freshness.check(github=github, now=NOW)
    assert github.calls == [transport.API_ROOT]
    assert not github.downloads


def test_private_visibility_change_or_asset_change_cannot_report_fresh(monkeypatch):
    github = FakeGitHub()
    original = github.download

    def changed(asset_id, path):
        original(asset_id, path)
        github.private["private"] = False

    monkeypatch.setattr(github, "download", changed)
    with pytest.raises(transport.contract.ContractError, match="private"):
        freshness.check(github=github, now=NOW)
    github = FakeGitHub()
    original = github.download

    def replaced(asset_id, path):
        original(asset_id, path)
        github.asset_list[0]["id"] = 999

    monkeypatch.setattr(github, "download", replaced)
    with pytest.raises(transport.contract.ContractError, match="changed during inspection"):
        freshness.check(github=github, now=NOW)


def test_release_inventory_is_bounded_and_cannot_silently_truncate():
    class ManyReleases:
        def __init__(self):
            self.calls = 0

        def api(self, endpoint):
            self.calls += 1
            return [{"tag_name": "unrelated"}] * 100

    github = ManyReleases()
    with pytest.raises(transport.contract.ContractError, match="bounded inspection limit"):
        freshness.inventory(github)
    assert github.calls == freshness.MAXIMUM_RELEASE_PAGES


def test_cli_success_is_silent_and_failure_is_nonzero_without_sensitive_diagnostics(monkeypatch, capsys):
    monkeypatch.setattr(freshness, "check", lambda: {"fresh": True})
    assert freshness.main([]) == 0
    assert capsys.readouterr() == ("", "")

    def failure():
        raise transport.contract.ContractError("secret application details must stay private")

    monkeypatch.setattr(freshness, "check", failure)
    with pytest.raises(SystemExit) as result:
        freshness.main([])
    assert result.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "Private database backup freshness is unverified.\n"
