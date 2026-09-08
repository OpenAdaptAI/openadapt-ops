import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("private_database_backup_release", SCRIPTS / "private_database_backup_release.py")
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)
SOURCE = "a" * 40
PRIVATE = {"full_name": release.REPOSITORY, "private": True, "visibility": "private",
           "archived": False, "disabled": False}


def digest(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def write_private(path, value):
    path.write_text(json.dumps(value))
    path.chmod(0o600)


@pytest.fixture
def archive(tmp_path):
    root = tmp_path / "archive"
    root.mkdir(mode=0o700)
    cipher = b"age-encryption.org/v1\nsynthetic-test-ciphertext"
    (root / release.ASSET_NAMES[0]).write_bytes(cipher)
    (root / release.ASSET_NAMES[0]).chmod(0o600)
    artifact = {
        "backup_contract_sha256": "b" * 64,
        "plaintext_archive": digest(b"synthetic-test-only"),
        "ciphertext_archive": digest(cipher), "repository_commit": "c" * 40,
        "workflow_run_id": None,
        "local_execution": {"id": "12345678-1234-1234-1234-123456789abc", "scope": "production",
                            "created_at": "2026-09-08T00:00:00.123456Z"},
    }
    manifest = {"schema": release.contract.ARTIFACT_SCHEMA, "artifact": artifact,
                "artifact_sha256": release.contract.sha256_text(release.contract.stable_json(artifact))}
    write_private(root / release.ASSET_NAMES[1], manifest)
    write_private(root / "local-verification.json", {
        "schema": "openadapt.local-database-backup/v1", "scope": "production",
        "artifact_sha256": manifest["artifact_sha256"], "encryption_roundtrip_verified": True,
    })
    return root


def rewrite_manifest(archive, mutate):
    path = archive / release.ASSET_NAMES[1]
    value = json.loads(path.read_text())
    mutate(value)
    value["artifact_sha256"] = release.contract.sha256_text(release.contract.stable_json(value["artifact"]))
    write_private(path, value)


@pytest.mark.parametrize("mutation", [
    {"private": False}, {"private": "true"}, {"visibility": "public"},
    {"visibility": "internal"}, {"visibility": None}, {"full_name": "OpenAdaptAI/openadapt-ops"},
    {"archived": True}, {"disabled": True},
])
def test_only_exact_active_private_repository_is_allowed(mutation):
    release.require_private_repository(PRIVATE)
    with pytest.raises(release.contract.ContractError, match="private"):
        release.require_private_repository({**PRIVATE, **mutation})


@pytest.mark.parametrize("mutation", [
    {"scope": "synthetic"}, {"encryption_roundtrip_verified": False},
    {"encryption_roundtrip_verified": 1}, {"artifact_sha256": "d" * 64},
])
def test_unverified_or_synthetic_receipt_refuses_before_network(archive, mutation):
    path = archive / "local-verification.json"
    write_private(path, {**json.loads(path.read_text()), **mutation})
    with pytest.raises(release.contract.ContractError, match="verified production"):
        release.publish(archive, SOURCE, github=NeverConnect())


class NeverConnect:
    def api(self, *args, **kwargs):
        pytest.fail("invalid local input must not reach GitHub")


@pytest.mark.parametrize("mutate", [
    lambda m: m.update(password="secret-must-stay-local"),
    lambda m: m["artifact"].update(db_url="postgresql://secret"),
    lambda m: m["artifact"]["ciphertext_archive"].update(filename="roles.sql"),
    lambda m: m["artifact"]["local_execution"].update(scope="synthetic"),
    lambda m: m["artifact"]["local_execution"].update(id="arbitrary-customer-text"),
    lambda m: m["artifact"]["local_execution"].update(created_at="secret"),
    lambda m: m["artifact"].update(repository_commit="secret"),
    lambda m: m["artifact"].update(workflow_run_id=12345),
])
def test_manifest_upload_allowlist_refuses_private_or_invented_metadata(archive, mutate):
    rewrite_manifest(archive, mutate)
    with pytest.raises(release.contract.ContractError):
        release.publish(archive, SOURCE, github=NeverConnect())


def test_duplicate_json_keys_cannot_hide_private_text_in_uploaded_manifest(archive):
    path = archive / release.ASSET_NAMES[1]
    path.write_text(path.read_text().replace('"repository_commit":',
                                            '"repository_commit": "private-text", "repository_commit":'))
    with pytest.raises(release.contract.ContractError, match="duplicate field"):
        release.publish(archive, SOURCE, github=NeverConnect())


def test_manifest_byte_mutation_after_validation_cannot_reach_upload(archive, monkeypatch):
    original = release.redacted_manifest

    def mutate_after_validation(value):
        result = original(value)
        path = archive / release.ASSET_NAMES[1]
        changed = json.loads(path.read_text())
        changed["secret"] = "must-not-upload"
        write_private(path, changed)
        return result

    monkeypatch.setattr(release, "redacted_manifest", mutate_after_validation)
    github = FakeGitHub()
    with pytest.raises(release.contract.ContractError, match="downloaded asset"):
        release.publish(archive, SOURCE, github=github)
    assert github.release is None
    assert not github.blobs


def test_local_ciphertext_integrity_and_asset_limit_fail_closed(archive, monkeypatch):
    release.verify_local(archive)
    monkeypatch.setattr(release, "ASSET_LIMIT", (archive / release.ASSET_NAMES[0]).stat().st_size)
    with pytest.raises(release.contract.ContractError, match="smaller than 2 GiB"):
        release.verify_local(archive)
    monkeypatch.setattr(release, "ASSET_LIMIT", 2 * 1024**3)
    with (archive / release.ASSET_NAMES[0]).open("ab") as stream:
        stream.write(b"corrupt")
    with pytest.raises(release.contract.ContractError, match="does not match"):
        release.verify_local(archive)


def test_plaintext_cannot_be_uploaded_as_age_by_renaming(archive):
    data = b"CREATE TABLE patient (secret text);\n"
    (archive / release.ASSET_NAMES[0]).write_bytes(data)
    rewrite_manifest(archive, lambda m: m["artifact"].update(ciphertext_archive=digest(data)))
    manifest = json.loads((archive / release.ASSET_NAMES[1]).read_text())
    receipt = json.loads((archive / "local-verification.json").read_text())
    write_private(archive / "local-verification.json", {**receipt, "artifact_sha256": manifest["artifact_sha256"]})
    with pytest.raises(release.contract.ContractError, match="age ciphertext header"):
        release.verify_local(archive)


def asset_metadata(expected):
    return [{"id": i, "name": name, "state": "uploaded", "size": entry["bytes"],
             "digest": "sha256:" + entry["sha256"]}
            for i, (name, entry) in enumerate(expected.items(), 101)]


@pytest.mark.parametrize("mutation", [
    lambda a: a.pop(),
    lambda a: a.append(copy.deepcopy(a[0])),
    lambda a: a[1].update(name=a[0]["name"]),
    lambda a: a[1].update(name="database.sql"),
    lambda a: a[1].update(id=a[0]["id"]),
    lambda a: a[0].update(state="starter"),
    lambda a: a[0].update(size=1),
    lambda a: a[0].update(digest=None),
    lambda a: a[0].update(digest="sha256:" + "0" * 64),
])
def test_remote_missing_duplicate_unexpected_or_mismatched_assets_refuse(archive, mutation):
    _, expected = release.verify_local(archive)
    assets = asset_metadata(expected)
    release.verify_assets(assets, expected)
    mutation(assets)
    with pytest.raises(release.contract.ContractError):
        release.verify_assets(assets, expected)


def test_corrupt_download_refuses_even_when_size_matches(archive, tmp_path):
    _, expected = release.verify_local(archive)
    downloaded = tmp_path / "downloaded"
    downloaded.mkdir(mode=0o700)
    for name in release.ASSET_NAMES:
        path = downloaded / name
        path.write_bytes((archive / name).read_bytes())
        path.chmod(0o600)
    release.verify_downloads(downloaded, expected)
    path = downloaded / release.ASSET_NAMES[0]
    path.write_bytes(path.read_bytes()[:-1] + b"!")
    with pytest.raises(release.contract.ContractError, match="downloaded asset"):
        release.verify_downloads(downloaded, expected)


class FakeGitHub:
    """In-memory API fixture; no network or production database execution."""

    def __init__(self, *, corrupt=False, visibility_changes=False, publish_error=False):
        self.events = []
        self.release = None
        self.blobs = {}
        self.metadata = []
        self.corrupt = corrupt
        self.visibility_changes = visibility_changes
        self.publish_error = publish_error

    def api(self, endpoint, *, method="GET", payload=None):
        self.events.append((method, endpoint, copy.deepcopy(payload)))
        if endpoint == release.API_ROOT:
            return {**PRIVATE, "private": not (self.visibility_changes and bool(self.blobs))}
        if "/commits/" in endpoint:
            return {"sha": SOURCE}
        if "/matching-refs/" in endpoint:
            return []
        if method == "POST":
            self.release = {**payload, "id": 42}
        elif method == "PATCH":
            if self.publish_error:
                raise release.contract.ContractError("publication failed")
            self.release.update(payload, published_at="2026-09-08T01:00:00Z")
        elif "/git/ref/" in endpoint:
            return {"object": {"type": "commit", "sha": SOURCE}}
        return copy.deepcopy(self.release)

    def assets(self, release_id):
        assert release_id == 42
        self.events.append(("ASSETS",))
        return copy.deepcopy(self.metadata)

    def upload(self, tag, path):
        assert self.release["draft"] is True
        assert self.events[-1][:2] == ("GET", release.API_ROOT)
        assert path.name in release.ASSET_NAMES
        assert stat_private(path.parent, directory=True)
        self.events.append(("UPLOAD", path.name))
        data = path.read_bytes()
        asset_id = len(self.blobs) + 101
        self.blobs[asset_id] = data
        self.metadata.append({"id": asset_id, "name": path.name, "state": "uploaded",
                              "size": len(data), "digest": "sha256:" + digest(data)["sha256"]})

    def download(self, asset_id, path):
        assert self.release["draft"] is True
        assert stat_private(path.parent, directory=True)
        self.events.append(("DOWNLOAD", asset_id))
        data = self.blobs[asset_id]
        path.write_bytes(data[:-1] + b"!" if self.corrupt else data)
        path.chmod(0o600)


def stat_private(path, directory=False):
    release.private_path(path, directory=directory)
    return True


def test_publish_only_follows_private_upload_metadata_and_download_verification(archive):
    github = FakeGitHub()
    result = release.publish(archive, SOURCE, github=github)
    assert result["off_device_verified"] is True
    assert result["download_readback_verified"] is True
    assert result["database_capture_performed"] is False
    assert result["database_restored"] is False
    assert result["storage_restored"] is False
    assert [e[1] for e in github.events if e[0] == "UPLOAD"] == list(release.ASSET_NAMES)
    patch_index = next(i for i, e in enumerate(github.events) if e[0] == "PATCH")
    assert len([e for e in github.events[:patch_index] if e[0] == "DOWNLOAD"]) == 2
    assert github.events[patch_index - 1][:2] == ("GET", release.API_ROOT)
    assert github.release["target_commitish"] == SOURCE
    assert github.release["make_latest"] == "false"
    assert github.release["draft"] is False
    assert json.loads((archive / release.RECEIPT_NAME).read_text()) == result
    assert stat_private(archive / release.RECEIPT_NAME)
    assert not list(archive.parent.glob(".github-backup-*"))
    with pytest.raises(release.contract.ContractError, match="already exists"):
        release.publish(archive, SOURCE, github=NeverConnect())


@pytest.mark.parametrize("options", [{"corrupt": True}, {"visibility_changes": True}, {"publish_error": True}])
def test_failed_attempt_keeps_original_archive_and_draft_without_success_receipt(archive, options):
    github = FakeGitHub(**options)
    originals = {p.name: p.read_bytes() for p in archive.iterdir()}
    with pytest.raises(release.contract.ContractError):
        release.publish(archive, SOURCE, github=github)
    assert github.release["draft"] is True
    assert {p.name: p.read_bytes() for p in archive.iterdir()} == originals
    assert not (archive / release.RECEIPT_NAME).exists()
    assert not any(e[0] == "DELETE" for e in github.events)
    if options.get("visibility_changes"):
        assert len(github.blobs) == 1


def test_subprocess_diagnostics_never_expose_credentials_or_command(monkeypatch):
    sentinel = "credential-must-never-be-logged"
    monkeypatch.setenv("GH_TOKEN", sentinel)
    monkeypatch.setenv("GH_DEBUG", "api")
    monkeypatch.setenv("GH_HOST", "another-host.invalid")

    def fake_run(command, **kwargs):
        assert command[0] == "gh"
        assert sentinel not in " ".join(command)
        assert kwargs["env"]["GH_TOKEN"] == sentinel
        assert kwargs["env"]["GH_HOST"] == "github.com"
        assert "GH_DEBUG" not in kwargs["env"]
        return subprocess.CompletedProcess(command, 1, stdout=sentinel.encode(), stderr=sentinel.encode())

    monkeypatch.setattr(release.subprocess, "run", fake_run)
    with pytest.raises(release.contract.ContractError) as failure:
        release.GitHub().api(release.API_ROOT)
    assert sentinel not in str(failure.value)


def test_invalid_github_json_does_not_report_success_or_raw_content(monkeypatch):
    monkeypatch.setattr(release.GitHub, "run", lambda *args, **kwargs: b"secret-response-text")
    with pytest.raises(release.contract.ContractError, match="invalid metadata") as failure:
        release.GitHub().api(release.API_ROOT)
    assert "secret-response-text" not in str(failure.value)
