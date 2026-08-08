import importlib.util
import io
import json
import tarfile
from argparse import Namespace
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "database_backup_contract.py"
SPEC = importlib.util.spec_from_file_location("database_backup_contract", MODULE_PATH)
assert SPEC and SPEC.loader
backup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backup)

SOURCE_REF = "abcdefghijklmnopqrst"
SCRATCH_REF = "zyxwvutsrqponmlkjihg"
RECIPIENT = "age1cw6u268e7vrjsl224w69may8ujxvqhqfymz79xm99dup5mf5y9jqv0vcqu"


def write_dumps(root: Path, *, data: str = "COPY public.runs (id) FROM stdin;\n1\n\\.\n") -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "roles.sql").write_text("CREATE ROLE example;\n")
    (root / "schema.sql").write_text("CREATE TABLE public.runs (id integer);\n")
    (root / "data.sql").write_text(data)


def write_recipient(path: Path, value: str = RECIPIENT) -> None:
    path.write_text(f"# public only\n{value}\n")


def make_contract(tmp_path: Path) -> tuple[Path, Path, Path]:
    dumps = tmp_path / "dump"
    write_dumps(dumps)
    recipients = tmp_path / "recipients.txt"
    write_recipient(recipients)
    contract = dumps / "backup-contract.json"
    backup.create_contract(
        Namespace(
            project_ref=SOURCE_REF,
            recipients=str(recipients),
            dump_dir=str(dumps),
            created_at="2026-08-08T07:23:00Z",
            supabase_cli_version="2.75.0",
            maximum_rpo_seconds=86400,
            retention_days=90,
            output=str(contract),
        )
    )
    return dumps, recipients, contract


def test_source_must_match_declared_supabase_project(tmp_path: Path) -> None:
    recipients = tmp_path / "recipients.txt"
    write_recipient(recipients)
    direct = f"postgresql://postgres:secret@db.{SOURCE_REF}.supabase.co:5432/postgres"
    backup.database_identity(direct, SOURCE_REF, "production")

    pooler = (
        f"postgresql://postgres.{SOURCE_REF}:secret@aws-0-us-east-1.pooler.supabase.com:5432/postgres"
    )
    backup.database_identity(pooler, SOURCE_REF, "production")

    with pytest.raises(backup.ContractError, match="does not match"):
        backup.database_identity(direct, SCRATCH_REF, "production")
    with pytest.raises(backup.ContractError, match="declared Supabase project"):
        backup.database_identity("postgresql://postgres:x@127.0.0.1/postgres", SOURCE_REF, "production")


def test_recipient_and_dump_contract_fail_closed(tmp_path: Path) -> None:
    recipient_file = tmp_path / "recipients.txt"
    recipient_file.write_text("# none\n")
    with pytest.raises(backup.ContractError, match="age public recipients"):
        backup.recipients(recipient_file)

    dumps = tmp_path / "dump"
    write_dumps(dumps, data="-- schema-only accident\n")
    with pytest.raises(backup.ContractError, match="no COPY"):
        backup.dump_inventory(dumps)

    write_dumps(dumps, data="COPY public.runs (id) FROM PROGRAM 'id';\n")
    with pytest.raises(backup.ContractError, match="unsafe local command"):
        backup.dump_inventory(dumps)

    write_dumps(dumps)
    (dumps / "schema.sql").write_text(
        "CREATE TABLE public.runs (id integer);\n\\! touch /tmp/not-allowed\n"
    )
    with pytest.raises(backup.ContractError, match="unsafe local command"):
        backup.dump_inventory(dumps)


def test_manifest_detects_ciphertext_tampering(tmp_path: Path) -> None:
    _, _, contract = make_contract(tmp_path)
    plaintext = tmp_path / "backup.tar.gz"
    ciphertext = tmp_path / "backup.tar.gz.age"
    plaintext.write_bytes(b"plain")
    ciphertext.write_bytes(b"ciphertext")
    manifest = tmp_path / "artifact-manifest.json"
    backup.create_manifest(
        Namespace(
            contract=str(contract),
            plaintext_archive=str(plaintext),
            ciphertext_archive=str(ciphertext),
            repository_commit="a" * 40,
            workflow_run_id="123",
            output=str(manifest),
        )
    )
    backup.verify_artifact(
        Namespace(manifest=str(manifest), ciphertext_archive=str(ciphertext))
    )
    ciphertext.write_bytes(b"changed")
    with pytest.raises(backup.ContractError, match="does not match"):
        backup.verify_artifact(
            Namespace(manifest=str(manifest), ciphertext_archive=str(ciphertext))
        )


def test_safe_extraction_accepts_only_the_exact_regular_file_set(tmp_path: Path) -> None:
    dumps, _, contract = make_contract(tmp_path)
    ciphertext = tmp_path / "backup.tar.gz.age"
    ciphertext.write_bytes(b"synthetic-ciphertext")

    def manifest_for(archive: Path, name: str) -> Path:
        manifest = tmp_path / name
        backup.create_manifest(
            Namespace(
                contract=str(contract),
                plaintext_archive=str(archive),
                ciphertext_archive=str(ciphertext),
                repository_commit="a" * 40,
                workflow_run_id="123",
                output=str(manifest),
            )
        )
        return manifest

    archive = tmp_path / "backup.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        for name in backup.ARCHIVE_MEMBERS:
            bundle.add(dumps / name, arcname=name)
    manifest = manifest_for(archive, "manifest.json")
    output = tmp_path / "out"
    backup.extract_artifact(
        Namespace(
            plaintext_archive=str(archive), manifest=str(manifest), output_dir=str(output)
        )
    )
    assert sorted(path.name for path in output.iterdir()) == sorted(backup.ARCHIVE_MEMBERS)
    assert all(path.stat().st_mode & 0o077 == 0 for path in output.iterdir())

    with archive.open("ab") as stream:
        stream.write(b"tamper")
    with pytest.raises(backup.ContractError, match="decrypted archive does not match"):
        backup.extract_artifact(
            Namespace(
                plaintext_archive=str(archive),
                manifest=str(manifest),
                output_dir=str(tmp_path / "tampered-out"),
            )
        )

    other = tmp_path / "other"
    write_dumps(other)
    other_contract = other / "backup-contract.json"
    recipient_file = tmp_path / "other-recipients.txt"
    write_recipient(recipient_file)
    backup.create_contract(
        Namespace(
            project_ref=SCRATCH_REF,
            recipients=str(recipient_file),
            dump_dir=str(other),
            created_at="2026-08-08T07:23:00Z",
            supabase_cli_version="2.75.0",
            maximum_rpo_seconds=86400,
            retention_days=90,
            output=str(other_contract),
        )
    )
    substituted = tmp_path / "substituted.tar.gz"
    with tarfile.open(substituted, "w:gz") as bundle:
        for name in backup.ARCHIVE_MEMBERS:
            bundle.add(other / name, arcname=name)
    # The outer manifest is valid for these bytes but names the first backup
    # contract. Extraction must bind the decrypted inner contract before SQL.
    substituted_manifest = manifest_for(substituted, "substituted-manifest.json")
    with pytest.raises(backup.ContractError, match="contract does not match"):
        backup.extract_artifact(
            Namespace(
                plaintext_archive=str(substituted),
                manifest=str(substituted_manifest),
                output_dir=str(tmp_path / "substituted-out"),
            )
        )

    unsafe = tmp_path / "unsafe.tar.gz"
    with tarfile.open(unsafe, "w:gz") as bundle:
        info = tarfile.TarInfo("../roles.sql")
        payload = b"CREATE ROLE example;\n"
        info.size = len(payload)
        bundle.addfile(info, io.BytesIO(payload))
    unsafe_manifest = manifest_for(unsafe, "unsafe-manifest.json")
    with pytest.raises(backup.ContractError, match="allowlist"):
        backup.extract_artifact(
            Namespace(
                plaintext_archive=str(unsafe),
                manifest=str(unsafe_manifest),
                output_dir=str(tmp_path / "unsafe-out"),
            )
        )

    symlink = tmp_path / "symlink.tar.gz"
    with tarfile.open(symlink, "w:gz") as bundle:
        for name in backup.ARCHIVE_MEMBERS:
            if name == "roles.sql":
                info = tarfile.TarInfo(name)
                info.type = tarfile.SYMTYPE
                info.linkname = "/etc/passwd"
                bundle.addfile(info)
            else:
                bundle.add(dumps / name, arcname=name)
    symlink_manifest = manifest_for(symlink, "symlink-manifest.json")
    with pytest.raises(backup.ContractError, match="non-regular"):
        backup.extract_artifact(
            Namespace(
                plaintext_archive=str(symlink),
                manifest=str(symlink_manifest),
                output_dir=str(tmp_path / "symlink-out"),
            )
        )


def test_restore_target_can_never_be_production() -> None:
    scratch_url = f"postgresql://postgres:secret@db.{SOURCE_REF}.supabase.co/postgres"
    with pytest.raises(backup.ContractError, match="production project"):
        backup.validate_restore_target(
            Namespace(
                source_project_ref=SOURCE_REF,
                scratch_project_ref=SOURCE_REF,
                scratch_db_url=scratch_url,
            )
        )


def test_restore_evidence_is_bound_to_exact_backup_and_scratch(tmp_path: Path) -> None:
    dumps, _, contract = make_contract(tmp_path)
    restored = tmp_path / "restored"
    write_dumps(restored)
    verification = tmp_path / "verification.json"
    source = {item["name"]: item for item in backup.dump_inventory(dumps)}
    verification.write_text(
        json.dumps(
            {
                "valid": True,
                "schema_sha256": source["schema.sql"]["sha256"],
                "data_sha256": source["data.sql"]["sha256"],
            }
        )
    )
    plaintext = tmp_path / "backup.tar.gz"
    ciphertext = tmp_path / "backup.tar.gz.age"
    plaintext.write_bytes(b"plain")
    ciphertext.write_bytes(b"ciphertext")
    manifest = tmp_path / "manifest.json"
    backup.create_manifest(
        Namespace(
            contract=str(contract),
            plaintext_archive=str(plaintext),
            ciphertext_archive=str(ciphertext),
            repository_commit="a" * 40,
            workflow_run_id="123",
            output=str(manifest),
        )
    )
    evidence = tmp_path / "restore-evidence.json"
    backup.record_restore(
        Namespace(
            manifest=str(manifest),
            contract=str(contract),
            verification=str(verification),
            source_project_ref=SOURCE_REF,
            scratch_project_ref=SCRATCH_REF,
            started_at="2026-08-08T08:00:00Z",
            completed_at="2026-08-08T08:05:00Z",
            output=str(evidence),
        )
    )
    value = json.loads(evidence.read_text())
    assert value["database_restored"] is True
    assert value["storage_restored"] is False
    assert value["rto_seconds"] == 300
    assert value["rpo_seconds_at_start"] == 2220

    verification.write_text(
        json.dumps(
            {
                "valid": True,
                "schema_sha256": "0" * 64,
                "data_sha256": source["data.sql"]["sha256"],
            }
        )
    )
    with pytest.raises(backup.ContractError, match="does not match the backup contract"):
        backup.record_restore(
            Namespace(
                manifest=str(manifest),
                contract=str(contract),
                verification=str(verification),
                source_project_ref=SOURCE_REF,
                scratch_project_ref=SCRATCH_REF,
                started_at="2026-08-08T08:00:00Z",
                completed_at="2026-08-08T08:05:00Z",
                output=str(tmp_path / "forged-evidence.json"),
            )
        )

    verification.write_text(
        json.dumps(
            {
                "valid": True,
                "schema_sha256": source["schema.sql"]["sha256"],
                "data_sha256": source["data.sql"]["sha256"],
            }
        )
    )

    with pytest.raises(backup.ContractError, match="already exists"):
        backup.record_restore(
            Namespace(
                manifest=str(manifest),
                contract=str(contract),
                verification=str(verification),
                source_project_ref=SOURCE_REF,
                scratch_project_ref=SCRATCH_REF,
                started_at="2026-08-08T08:00:00Z",
                completed_at="2026-08-08T08:05:00Z",
                output=str(evidence),
            )
        )
