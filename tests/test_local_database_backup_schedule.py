import hashlib
import importlib.util
import json
import plistlib
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
capture_module = importlib.import_module("temporary_database_backup")
SPEC = importlib.util.spec_from_file_location("local_database_backup_schedule", SCRIPTS / "local_database_backup_schedule.py")
schedule = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(schedule)
SHA = "a" * 40
ARTIFACT = "b" * 64
CONTRACT = "c" * 64
PROJECT = "abcdefghijklmnopqrst"
PROJECT_HASH = hashlib.sha256(PROJECT.encode()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value))
    path.chmod(0o600)


@pytest.fixture
def configuration(tmp_path):
    backup_root = tmp_path / "archives"
    backup_root.mkdir(mode=0o700)
    postgres = tmp_path / "postgres-bin"
    postgres.mkdir()
    for name in ("identity.agekey", "recipients.txt"):
        (tmp_path / name).write_text("synthetic fixture; never used as a credential")
        (tmp_path / name).chmod(0o600)
    write_json(tmp_path / "capture.json", {
        "project_ref": PROJECT, "management_token": "synthetic-test-only", "owned_role_oid": 12345,
        "pooler_host": "aws-0-us-east-1.pooler.supabase.com",
    })
    value = {"expected_backup_commit": SHA, "internal_commit": "d" * 40,
             "capture_config": str(tmp_path / "capture.json"), "backup_root": str(backup_root),
             "identity": str(tmp_path / "identity.agekey"), "recipients": str(tmp_path / "recipients.txt"),
             "postgres_bin": str(postgres)}
    path = tmp_path / "schedule.json"
    write_json(path, value)
    return path, value


@pytest.fixture
def proof(configuration):
    path, config = configuration
    archive = Path(config["backup_root"]) / "proven-production-archive"
    archive.mkdir(mode=0o700)
    expected = {"database.tar.gz.age": {"bytes": 20, "sha256": "e" * 64},
                "artifact-manifest.json": {"bytes": 30, "sha256": "f" * 64}}
    restored = {"schema": "openadapt.database-restore-evidence/v2", "database_restored": True,
                "storage_restored": False, "artifact_sha256": ARTIFACT, "backup_contract_sha256": CONTRACT,
                "source_project_ref_sha256": PROJECT_HASH, "scratch_project_ref_sha256": "2" * 64}
    copied = {"schema": "openadapt.database-backup-github-release/v1", "scope": "production",
              "repository": "OpenAdaptAI/openadapt-internal", "repository_visibility_verified": "private",
              "off_device_verified": True, "download_readback_verified": True, "artifact_sha256": ARTIFACT,
              "assets": {name: {"id": i, **value} for i, (name, value) in enumerate(expected.items(), 1)}}
    write_json(archive / "restore-receipt.json", restored)
    write_json(archive / "github-release-receipt.json", copied)
    transport = SimpleNamespace(
        REPOSITORY="OpenAdaptAI/openadapt-internal", RECEIPT_NAME="github-release-receipt.json",
        verify_local=lambda archive: ({"artifact_sha256": ARTIFACT,
                                       "artifact": {"backup_contract_sha256": CONTRACT}}, expected),
    )
    return archive, transport


@pytest.mark.parametrize("change", [
    {"command": "arbitrary shell code"}, {"expected_backup_commit": "main"},
    {"internal_commit": "HEAD"}, {"capture_config": "relative.json"},
])
def test_config_is_exact_and_refuses_commands_branches_and_relative_paths(configuration, change):
    path, value = configuration
    write_json(path, {**value, **change})
    with pytest.raises(schedule.ScheduleError):
        schedule.read_config(path)


def test_config_and_credentials_must_be_private_owned_regular_files(configuration):
    path, value = configuration
    path.chmod(0o644)
    with pytest.raises(schedule.ScheduleError, match="private files"):
        schedule.read_config(path)
    path.chmod(0o600)
    Path(value["capture_config"]).chmod(0o644)
    with pytest.raises(schedule.ScheduleError, match="private files"):
        schedule.read_config(path)
    Path(value["capture_config"]).chmod(0o600)
    identity = Path(value["identity"])
    identity.unlink()
    identity.symlink_to(Path(value["recipients"]))
    with pytest.raises(schedule.ScheduleError, match="private files"):
        schedule.read_config(path)


def test_duplicate_config_fields_fail(configuration):
    path, _ = configuration
    path.write_text(path.read_text().replace('"internal_commit":', '"internal_commit": "hidden", "internal_commit":'))
    with pytest.raises(schedule.ScheduleError, match="duplicate fields"):
        schedule.read_config(path)


def test_real_git_pin_and_source_hashes_refuse_wrong_commit_changed_and_missing_code(tmp_path, monkeypatch):
    root = tmp_path / "reviewed"
    root.mkdir()
    for name in schedule.SOURCE_FILES:
        target = root / name
        target.parent.mkdir(exist_ok=True)
        target.write_text(f"# synthetic pinned source: {name}\n")

    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE)

    git("init", "-q")
    git("add", "scripts")
    git("-c", "user.name=Backup test", "-c", "user.email=backup-test@example.invalid", "commit", "-qm", "Synthetic source fixture")
    expected = git("rev-parse", "HEAD").decode().strip()
    monkeypatch.setattr(schedule, "CODE_ROOT", root)
    schedule.verify_source(expected)
    with pytest.raises(schedule.ScheduleError, match="reviewed source commit"):
        schedule.verify_source("0" * 40)
    target = root / schedule.SOURCE_FILES[0]
    original = target.read_text()
    target.write_text(original + "# changed after review\n")
    with pytest.raises(schedule.ScheduleError, match="differs"):
        schedule.verify_source(expected)
    target.write_text(original)
    (root / schedule.SOURCE_FILES[-1]).unlink()
    with pytest.raises(OSError):
        schedule.verify_source(expected)


def test_source_verification_disables_lazy_network_fetch(monkeypatch):
    def run(command, **kwargs):
        assert kwargs["env"]["GIT_NO_LAZY_FETCH"] == "1"
        assert kwargs["env"]["GIT_TERMINAL_PROMPT"] == "0"
        return subprocess.CompletedProcess(command, 0, stdout=SHA.encode(), stderr=b"")

    monkeypatch.setattr(schedule.subprocess, "run", run)
    assert schedule.git_read(["rev-parse", "--verify", "HEAD"]) == SHA.encode()


def test_nonblocking_lock_prevents_overlapping_capture(configuration):
    _, value = configuration
    root = Path(value["backup_root"])
    with schedule.run_lock(root):
        with pytest.raises(schedule.ScheduleError, match="already active"):
            with schedule.run_lock(root):
                pytest.fail("two captures must not share the lock")
    with schedule.run_lock(root):
        pass
    assert (root / ".database-backup-schedule.lock").stat().st_mode & 0o077 == 0


def test_run_verifies_source_then_captures_and_publishes_sequentially(configuration, monkeypatch, capsys):
    path, value = configuration
    events = []
    archive = Path(value["backup_root"]) / "new-archive"
    archive.mkdir(mode=0o700)

    def capture(*args):
        events.append("capture")
        assert args == (Path(value["capture_config"]), SHA, Path(value["backup_root"]),
                        Path(value["identity"]), Path(value["recipients"]), Path(value["postgres_bin"]))
        print("private capture diagnostics must not reach launchd logs")
        return archive

    def publish(selected, commit):
        events.append("publish")
        assert selected == archive and commit == value["internal_commit"]
        return {"off_device_verified": True}

    monkeypatch.setattr(schedule, "verify_source", lambda expected: events.append("verify-source"))
    monkeypatch.setattr(schedule, "load_operations", lambda: (SimpleNamespace(capture=capture), SimpleNamespace(publish=publish)))
    assert schedule.run_once(path) == {"off_device_verified": True}
    assert events == ["verify-source", "capture", "publish"]
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("stage", ["source", "capture", "upload", "unverified-upload"])
def test_failed_capture_or_upload_never_claims_success(configuration, monkeypatch, capsys, stage):
    path, value = configuration
    events = []
    archive = Path(value["backup_root"]) / "new-archive"
    archive.mkdir(mode=0o700)

    def verify(expected):
        if stage == "source":
            raise schedule.ScheduleError("private failure details")

    def capture(*args):
        events.append("capture")
        if stage == "capture":
            raise RuntimeError("secret database credentials")
        return archive

    def publish(*args):
        events.append("upload")
        if stage == "upload":
            raise RuntimeError("private upload diagnostics")
        return {"off_device_verified": False}

    monkeypatch.setattr(schedule, "verify_source", verify)
    monkeypatch.setattr(schedule, "load_operations", lambda: (SimpleNamespace(capture=capture), SimpleNamespace(publish=publish)))
    with pytest.raises(SystemExit) as failure:
        schedule.main(["run", "--config", str(path)])
    assert failure.value.code == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "The local database backup operation did not complete.\n"
    if stage == "source":
        assert not events
    if stage == "capture":
        assert events == ["capture"]


@pytest.mark.parametrize("filename, mutation", [
    ("restore-receipt.json", {"database_restored": False}),
    ("restore-receipt.json", {"artifact_sha256": "0" * 64}),
    ("restore-receipt.json", {"backup_contract_sha256": "0" * 64}),
    ("restore-receipt.json", {"scratch_project_ref_sha256": PROJECT_HASH}),
    ("github-release-receipt.json", {"scope": "synthetic"}),
    ("github-release-receipt.json", {"off_device_verified": False}),
    ("github-release-receipt.json", {"download_readback_verified": False}),
    ("github-release-receipt.json", {"repository_visibility_verified": "public"}),
    ("github-release-receipt.json", {"artifact_sha256": "0" * 64}),
    ("github-release-receipt.json", {"assets": {}}),
])
def test_setup_requires_restore_and_offdevice_receipts_for_same_production_archive(configuration, proof, filename, mutation):
    path, _ = configuration
    archive, transport = proof
    receipt = archive / filename
    write_json(receipt, {**json.loads(receipt.read_text()), **mutation})
    with pytest.raises(schedule.ScheduleError):
        schedule.verify_recovery(archive, schedule.read_config(path), transport, capture_module)


def test_setup_generates_real_private_0400_plist_without_installation(configuration, proof, monkeypatch, tmp_path):
    config_path, config = configuration
    archive, transport = proof
    events = []
    monkeypatch.setattr(schedule, "verify_source", lambda expected: events.append(expected))
    monkeypatch.setattr(schedule, "load_operations", lambda: (capture_module, transport))
    output = tmp_path / "review.plist"
    assert schedule.setup(config_path, archive, output) == output
    with output.open("rb") as stream:
        value = plistlib.load(stream)
    assert events == [SHA]
    assert value["StartCalendarInterval"] == {"Hour": 4, "Minute": 0}
    assert value["RunAtLoad"] is False and value["KeepAlive"] is False
    assert value["ProgramArguments"] == [str(Path(schedule.sys.executable).resolve()),
                                         str(Path(schedule.__file__).resolve()), "run", "--config", str(config_path)]
    assert value["Umask"] == 0o077
    assert output.stat().st_mode & 0o077 == 0
    assert Path(value["StandardErrorPath"]).stat().st_mode & 0o077 == 0
    assert Path(value["StandardOutPath"]).stat().st_mode & 0o077 == 0
    with pytest.raises(FileExistsError):
        schedule.setup(config_path, archive, output)
    forbidden = tmp_path / "LaunchAgents"
    forbidden.mkdir(mode=0o700)
    with pytest.raises(schedule.ScheduleError, match="never a launchd installation"):
        schedule.setup(config_path, archive, forbidden / "backup.plist")
    assert not list(forbidden.iterdir())


def test_missing_restore_receipt_cannot_generate_a_plist(configuration, proof, monkeypatch, tmp_path):
    path, _ = configuration
    archive, transport = proof
    (archive / "restore-receipt.json").unlink()
    monkeypatch.setattr(schedule, "verify_source", lambda expected: None)
    monkeypatch.setattr(schedule, "load_operations", lambda: (capture_module, transport))
    output = tmp_path / "review.plist"
    with pytest.raises(OSError):
        schedule.setup(path, archive, output)
    assert not output.exists()


def test_project_a_restore_cannot_authorize_a_schedule_for_project_b(configuration, proof, monkeypatch, tmp_path):
    config_path, config = configuration
    archive, transport = proof
    capture_path = Path(config["capture_config"])
    changed = json.loads(capture_path.read_text())
    changed["project_ref"] = "zyxwvutsrqponmlkjihg"
    write_json(capture_path, changed)
    assert capture_module.config_file(capture_path)["project_ref"] == changed["project_ref"]
    monkeypatch.setattr(schedule, "verify_source", lambda expected: None)
    monkeypatch.setattr(schedule, "load_operations", lambda: (capture_module, transport))
    output = tmp_path / "review.plist"
    with pytest.raises(schedule.ScheduleError, match="configured production project"):
        schedule.setup(config_path, archive, output)
    assert not output.exists()
    assert not (Path(config["backup_root"]) / "schedule.stdout.log").exists()
