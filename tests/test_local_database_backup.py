import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("local_database_backup", SCRIPTS / "local_database_backup.py")
backup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backup)


@pytest.fixture
def keys(tmp_path):
    if not shutil.which("age-keygen") or not shutil.which("age"):
        pytest.skip("age and age-keygen are required for the real encryption test")
    identity = tmp_path / "synthetic.agekey"
    subprocess.run(["age-keygen", "-o", str(identity)], capture_output=True, check=True)
    identity.chmod(0o600)
    recipient = subprocess.check_output(["age-keygen", "-y", str(identity)]).decode()
    recipients = tmp_path / "recipients.txt"
    recipients.write_text(recipient)
    return identity, recipients


def pack(tmp_path, keys, dumps):
    root = tmp_path / "archives"
    root.mkdir(mode=0o700)
    destination = root / "synthetic"
    receipt = backup.pack(
        dumps, destination, project_ref="syntheticfixture", recipients=keys[1], identity=keys[0],
        source_commit="a" * 40, scope="synthetic", created_at="2026-09-08T00:00:00Z",
    )
    return destination, receipt


def test_real_age_roundtrip_refuses_tampering_and_keeps_no_plaintext(tmp_path, keys):
    dumps = tmp_path / "dump"
    dumps.mkdir()
    (dumps / "roles.sql").write_text("RESET ALL;\n")
    (dumps / "schema.sql").write_text("CREATE TABLE public.runs (id integer, value text);\n")
    (dumps / "data.sql").write_text("COPY public.runs (id, value) FROM stdin;\n1\tsynthetic\n\\.\n")
    archive, receipt = pack(tmp_path, keys, dumps)
    assert receipt["encryption_roundtrip_verified"] is True
    assert receipt["database_restored"] is False
    assert receipt["off_device_verified"] is False
    assert {p.name for p in archive.iterdir()} == {
        "database.tar.gz.age", "artifact-manifest.json", "local-verification.json"
    }
    assert not any(p.name.startswith(".backup-") for p in archive.parent.iterdir())
    assert json.loads((archive / "artifact-manifest.json").read_text())["artifact"]["workflow_run_id"] is None
    recovered = archive.parent / "recovered"
    backup.unpack(archive, keys[0], recovered)
    assert (recovered / "data.sql").read_bytes() == (dumps / "data.sql").read_bytes()
    with pytest.raises(backup.contract.ContractError, match="already exists"):
        backup.unpack(archive, keys[0], recovered)
    cipher = archive / "database.tar.gz.age"
    cipher.write_bytes(cipher.read_bytes()[:-1] + b"!")
    with pytest.raises(backup.contract.ContractError, match="does not match"):
        backup.unpack(archive, keys[0], archive.parent / "tampered")
    assert not (archive.parent / "tampered").exists()


def test_credentials_must_be_private_regular_files(tmp_path):
    value = tmp_path / "private.json"
    value.write_text("{}")
    value.chmod(0o644)
    with pytest.raises(backup.contract.ContractError, match="private regular"):
        backup.private_file(value)
    value.chmod(0o600)
    backup.private_file(value)
    link = tmp_path / "alias.json"
    link.symlink_to(value)
    with pytest.raises(backup.contract.ContractError, match="private regular"):
        backup.private_file(link)


def test_subprocess_failure_does_not_expose_command_or_output():
    with pytest.raises(backup.contract.ContractError) as error:
        backup.run([sys.executable, "-c", "import sys; print('secret-url', file=sys.stderr); sys.exit(1)"])
    assert "secret-url" not in str(error.value)


@pytest.mark.parametrize("url", [
    "postgresql://postgres:fixture@localhost/postgres",
    "postgresql://postgres:fixture@db.otherproject.supabase.co/postgres",
    "postgresql://postgres@db.syntheticfixture.supabase.co/postgres",
    "postgresql://postgres:fixture@db.syntheticfixture.supabase.co/postgres?sslmode=disable",
    "postgresql://postgres:fixture@db.syntheticfixture.supabase.co/postgres?options=-c%20foo=bar",
])
def test_source_refuses_wrong_identity_missing_password_or_tls_downgrade(url):
    with pytest.raises(backup.contract.ContractError):
        backup.source_config({"project_ref": "syntheticfixture", "db_url": url})


def test_real_supabase_cli_reads_private_passfile_without_password_in_argv(tmp_path):
    if not shutil.which("supabase"):
        pytest.skip("Supabase CLI is required to prove the passfile boundary")
    from urllib.parse import quote
    secret = "synthetic:pass\\word-with-dashes"
    config = {"project_ref": "syntheticfixture", "db_url":
              "postgresql://postgres:" + quote(secret, safe="") +
              "@db.syntheticfixture.supabase.co:5432/postgres?sslmode=require"}
    passwordless, env = backup.dump_connection(config, tmp_path / "source.pgpass")
    assert secret not in passwordless
    assert quote(secret, safe="") not in passwordless
    assert "PGPASSWORD" not in env
    assert "SUPABASE_DB_PASSWORD" not in env
    assert (tmp_path / "source.pgpass").stat().st_mode & 0o777 == 0o600
    # This executes the real pinned CLI parser, without a server connection or
    # Docker. Its generated script proves that it loaded the correct password.
    output = subprocess.check_output(
        ["supabase", "db", "dump", "--db-url", passwordless, "--dry-run", "--role-only"],
        env=env, stderr=subprocess.PIPE,
    ).decode()
    assert 'export PGPASSWORD="' + secret + '"' in output


def test_real_postgres_isolated_restore(tmp_path, keys, monkeypatch):
    """Run only when explicitly enabled; no production connection is possible."""
    configured = os.environ.get("OPENADAPT_TEST_POSTGRES_BIN")
    if not configured:
        pytest.skip("set OPENADAPT_TEST_POSTGRES_BIN for the isolated PostgreSQL drill")
    binary = Path(configured)
    native17 = b" 17." in subprocess.check_output([str(binary / "pg_dump"), "--version"])
    clusters = []
    source_port = None
    with tempfile.TemporaryDirectory(prefix="oadb-", dir="/private/tmp" if sys.platform == "darwin" else "/tmp") as work:
        root = Path(work)
        root.chmod(0o700)

        def connection_env(cluster):
            env = os.environ.copy()
            for name in list(env):
                if name.startswith("PG"):
                    env.pop(name)
            port = str(source_port) if cluster.name == "source" else "55481"
            env.update(PGHOST=str(cluster / "socket"), PGPORT=port, PGUSER="postgres", PGDATABASE="postgres",
                       PGSSLMODE="require", PGCONNECT_TIMEOUT="3",
                       PGOPTIONS="-c default_transaction_read_only=on")
            return env

        def command(cluster, executable, *args, input=None):
            env = connection_env(cluster)
            env.pop("PGOPTIONS")  # Only the test fixture writer can change synthetic data.
            return subprocess.run([str(binary / executable), *args], input=input, env=env,
                                  capture_output=True, check=True, timeout=60).stdout

        def dumps(cluster, output):
            output.mkdir()
            (output / "roles.sql").write_text("RESET ALL;\n")
            for name, flag in (("schema.sql", "--schema-only"), ("data.sql", "--data-only")):
                if native17:
                    flags = [] if flag == "--schema-only" else ["--data-only", "--use-copy", "-x", "storage.buckets_vectors", "-x", "storage.vector_indexes"]
                    backup.native_dump(output / name, flags, connection_env(cluster), binary)
                else:
                    (output / name).write_bytes(command(cluster, "pg_dump", flag, "--no-owner", "--no-privileges"))

        try:
            for name in ("source", "scratch"):
                cluster = root / name
                cluster.mkdir()
                (cluster / "socket").mkdir()
                if name == "source":
                    with socket.socket() as listener:
                        listener.bind(("127.0.0.1", 0))
                        source_port = listener.getsockname()[1]
                command(cluster, "initdb", "-D", str(cluster / "data"), "-U", "postgres", "--auth=trust", "--no-locale", "-E", "UTF8")
                hostname = "127.0.0.1" if name == "source" else "''"
                port = source_port if name == "source" else 55481
                command(cluster, "pg_ctl", "-D", str(cluster / "data"), "-l", str(cluster / "server.log"),
                        "-o", f"-h {hostname} -k {cluster / 'socket'} -p {port}", "-w", "start")
                clusters.append(cluster)
            command(clusters[0], "psql", "-X", "-v", "ON_ERROR_STOP=1", input=(
                b"CREATE TABLE public.records (id integer PRIMARY KEY, amount numeric(12,2), note text);\n"
                b"INSERT INTO public.records VALUES (1,123.45,'synthetic'),(2,-3.50,E'line1\\nline2'),(3,NULL,NULL);\n"
            ))
            source_dumps = root / "source-dump"
            if native17:
                # Same real client and server: allow plaintext as a control,
                # then require TLS and verify refusal before any archive exists.
                tcp = connection_env(clusters[0]) | {"PGHOST": "127.0.0.1", "PGSSLMODE": "disable"}
                backup.native_dump(root / "tls-control.sql", [], tcp, binary)
                tcp["PGSSLMODE"] = "require"
                with pytest.raises(backup.contract.ContractError):
                    backup.native_dump(root / "tls-refused.sql", [], tcp, binary)
                # Inject the exact live DDL race after the schema dump. The
                # data dump must import the same exported snapshot.
                original = backup.native_dump
                def migrate_after_schema(output, flags, env, postgres_bin, **kwargs):
                    original(output, flags, env, postgres_bin, **kwargs)
                    if output.name == "schema.sql":
                        command(clusters[0], "psql", "-X", "-v", "ON_ERROR_STOP=1", "-c",
                                "ALTER TABLE records ADD COLUMN migration_race text NOT NULL DEFAULT 'new'; UPDATE records SET amount=999 WHERE id=1;")
                source_dumps.mkdir()
                with monkeypatch.context() as patch:
                    patch.setattr(backup, "native_dump", migrate_after_schema)
                    backup.capture_dumps(source_dumps, connection_env(clusters[0]), binary)
            else:
                dumps(clusters[0], source_dumps)
            archive, receipt = pack(tmp_path, keys, source_dumps)
            recovered = archive.parent / "restore-input"
            backup.unpack(archive, keys[0], recovered)
            command(clusters[1], "psql", "-X", "-v", "ON_ERROR_STOP=1", "--single-transaction",
                    "-f", str(recovered / "roles.sql"), "-f", str(recovered / "schema.sql"), "-f", str(recovered / "data.sql"))
            restored_dumps = root / "restored-dump"
            dumps(clusters[1], restored_dumps)
            backup.quiet(backup.contract.verify_restored_dumps, source_dir=str(recovered), restored_dir=str(restored_dumps))
            actual = command(clusters[1], "psql", "-X", "-At", "-c", "SELECT count(*), sum(amount), count(note) FROM records;")
            assert actual.strip() == b"3|119.95|2"
            # This probe proves the restore oracle notices a lost row.
            command(clusters[1], "psql", "-X", "-v", "ON_ERROR_STOP=1", "-c", "DELETE FROM records WHERE id=2;")
            changed = root / "changed-dump"
            dumps(clusters[1], changed)
            with pytest.raises(backup.contract.ContractError, match="data.sql does not match"):
                backup.quiet(backup.contract.verify_restored_dumps, source_dir=str(recovered), restored_dir=str(changed))
        finally:
            for cluster in reversed(clusters):
                command(cluster, "pg_ctl", "-D", str(cluster / "data"), "-m", "fast", "-w", "stop")
