#!/usr/bin/env python3
"""Transport verified ciphertext to the existing private recovery repository.

This command never captures or restores a database. It publishes only after
checking GitHub's asset metadata and downloading and rehashing both assets.
Failed attempts preserve the local archive and any draft release for diagnosis.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import database_backup_contract as contract

REPOSITORY = "OpenAdaptAI/openadapt-internal"
API_ROOT = f"repos/{REPOSITORY}"
ASSET_NAMES = ("database.tar.gz.age", "artifact-manifest.json")
ASSET_LIMIT = 2 * 1024**3
RECEIPT_NAME = "github-release-receipt.json"
SHA = re.compile(r"[0-9a-f]{40}")


def require_private_repository(value: object) -> None:
    if (not isinstance(value, dict) or value.get("full_name") != REPOSITORY
            or value.get("private") is not True or value.get("visibility") != "private"
            or value.get("archived") is not False or value.get("disabled") is not False):
        raise contract.ContractError("the exact recovery repository must be active and private")


def private_path(path: Path, *, directory: bool = False) -> None:
    info = path.lstat()
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    if not kind(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid():
        raise contract.ContractError("the archive requires private, owned regular files and directories")


def exact_keys(value: object, expected: set[str]) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise contract.ContractError("the manifest contains missing or unapproved fields")


def redacted_manifest(value: dict) -> dict:
    """Reject arbitrary metadata rather than copying it to an external host."""
    exact_keys(value, {"schema", "artifact", "artifact_sha256"})
    artifact = value["artifact"]
    if (value["schema"] != contract.ARTIFACT_SCHEMA
            or value["artifact_sha256"] != contract.sha256_text(contract.stable_json(artifact))):
        raise contract.ContractError("the artifact manifest schema or digest is invalid")
    exact_keys(artifact, {"backup_contract_sha256", "plaintext_archive", "ciphertext_archive",
                          "repository_commit", "workflow_run_id", "local_execution"})
    if (not isinstance(artifact["repository_commit"], str)
            or not SHA.fullmatch(artifact["repository_commit"])
            or artifact["workflow_run_id"] is not None):
        raise contract.ContractError("the local artifact requires an exact source SHA and no Actions run ID")
    if not isinstance(artifact["backup_contract_sha256"], str) or not contract.SHA256.fullmatch(
            artifact["backup_contract_sha256"]):
        raise contract.ContractError("the backup contract digest is invalid")
    for name in ("plaintext_archive", "ciphertext_archive"):
        entry = artifact[name]
        exact_keys(entry, {"bytes", "sha256"})
        if (type(entry["bytes"]) is not int or entry["bytes"] <= 0
                or not isinstance(entry["sha256"], str)
                or not contract.SHA256.fullmatch(entry["sha256"])):
            raise contract.ContractError("the archive integrity fields are invalid")
    local = artifact["local_execution"]
    exact_keys(local, {"id", "scope", "created_at"})
    if (local["scope"] != "production" or not isinstance(local["id"], str)
            or not re.fullmatch(r"[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}", local["id"])
            or not isinstance(local["created_at"], str)
            or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?Z", local["created_at"])):
        raise contract.ContractError("the artifact must describe a production local capture")
    contract.parse_time(local["created_at"], "local capture time")
    return value


def unique_json_fields(pairs: list) -> dict:
    result = {}
    for name, value in pairs:
        if name in result:
            raise contract.ContractError("the manifest contains a duplicate field")
        result[name] = value
    return result


def verify_local(archive: Path) -> tuple[dict, dict]:
    private_path(archive, directory=True)
    for name in (*ASSET_NAMES, "local-verification.json"):
        private_path(archive / name)
    manifest_path = archive / ASSET_NAMES[1]
    with manifest_path.open("rb") as stream:
        manifest_bytes = stream.read(64 * 1024 + 1)
    if len(manifest_bytes) > 64 * 1024:
        raise contract.ContractError("the redacted manifest is unexpectedly large")
    manifest = redacted_manifest(json.loads(manifest_bytes, object_pairs_hook=unique_json_fields))
    receipt_path = archive / "local-verification.json"
    if receipt_path.stat().st_size > 64 * 1024:
        raise contract.ContractError("the local verification receipt is unexpectedly large")
    receipt = json.loads(receipt_path.read_text())
    if (not isinstance(receipt, dict) or receipt.get("schema") != "openadapt.local-database-backup/v1"
            or receipt.get("scope") != "production"
            or receipt.get("encryption_roundtrip_verified") is not True
            or receipt.get("artifact_sha256") != manifest["artifact_sha256"]):
        raise contract.ContractError("a matching verified production capture is required")
    cipher_path = archive / ASSET_NAMES[0]
    cipher_size = cipher_path.stat().st_size
    if not 0 < cipher_size < ASSET_LIMIT or not 0 < len(manifest_bytes) < ASSET_LIMIT:
        raise contract.ContractError("each release asset must be nonempty and smaller than 2 GiB")
    # Hash the exact manifest bytes that passed the privacy checks. Re-reading
    # the original path here could accept a different, unvalidated document.
    expected = {
        ASSET_NAMES[0]: {"bytes": cipher_size, "sha256": contract.sha256_file(cipher_path)},
        ASSET_NAMES[1]: {"bytes": len(manifest_bytes), "sha256": contract.sha256_text(manifest_bytes.decode())},
    }
    if expected[ASSET_NAMES[0]] != manifest["artifact"]["ciphertext_archive"]:
        raise contract.ContractError("the encrypted archive does not match the manifest")
    with (archive / ASSET_NAMES[0]).open("rb") as stream:
        if stream.read(22) != b"age-encryption.org/v1\n":
            raise contract.ContractError("the archive does not have the age ciphertext header")
    return manifest, expected


def verify_assets(assets: object, expected: dict) -> dict:
    if not isinstance(assets, list) or len(assets) != len(ASSET_NAMES):
        raise contract.ContractError("the remote release asset inventory is incomplete or unexpected")
    result = {}
    ids = set()
    for asset in assets:
        if not isinstance(asset, dict):
            raise contract.ContractError("the remote asset metadata is invalid")
        name = asset.get("name")
        if not isinstance(name, str) or name not in expected or name in result:
            raise contract.ContractError("the remote release has duplicate or unexpected assets")
        asset_id = asset.get("id")
        if type(asset_id) is not int or asset_id <= 0 or asset_id in ids:
            raise contract.ContractError("the remote asset identity is invalid or duplicated")
        if (asset.get("state") != "uploaded" or type(asset.get("size")) is not int
                or asset["size"] != expected[name]["bytes"]
                or asset.get("digest") != "sha256:" + expected[name]["sha256"]):
            raise contract.ContractError("the remote asset state, size, or SHA256 does not match")
        ids.add(asset_id)
        result[name] = {"id": asset_id, **expected[name]}
    return result


def verify_downloads(directory: Path, expected: dict) -> None:
    if {path.name for path in directory.iterdir()} != set(ASSET_NAMES):
        raise contract.ContractError("the downloaded asset inventory does not match")
    for name in ASSET_NAMES:
        path = directory / name
        private_path(path)
        if (path.stat().st_size != expected[name]["bytes"]
                or contract.sha256_file(path) != expected[name]["sha256"]):
            raise contract.ContractError("a downloaded asset does not match the original archive")


class GitHub:
    def run(self, arguments: list[str], *, input: bytes | None = None, stdout=None) -> bytes:
        env = dict(os.environ, GH_HOST="github.com", GH_PROMPT_DISABLED="1", GH_PAGER="cat")
        env.pop("GH_DEBUG", None)
        env.pop("DEBUG", None)
        try:
            result = subprocess.run(["gh", *arguments], input=input,
                                    stdout=stdout if stdout is not None else subprocess.PIPE,
                                    stderr=subprocess.PIPE, env=env, timeout=1800, check=False)
        except (OSError, subprocess.TimeoutExpired):
            raise contract.ContractError("GitHub transport failed; no off-device success is claimed") from None
        if result.returncode:
            raise contract.ContractError("GitHub transport failed; no off-device success is claimed")
        return result.stdout

    def api(self, endpoint: str, *, method: str = "GET", payload: dict | None = None):
        arguments = ["api", "--hostname", "github.com", "--method", method, endpoint,
                     "-H", "Accept: application/vnd.github+json",
                     "-H", "X-GitHub-Api-Version: 2022-11-28"]
        data = None
        if payload is not None:
            arguments += ["--input", "-"]
            data = json.dumps(payload).encode()
        try:
            return json.loads(self.run(arguments, input=data))
        except (ValueError, UnicodeError):
            raise contract.ContractError("GitHub returned invalid metadata") from None

    def assets(self, release_id: int) -> list:
        # A third asset already violates the exact inventory. Requesting 100
        # makes truncation harmless: a full page also fails the two-asset gate.
        return self.api(f"{API_ROOT}/releases/{release_id}/assets?per_page=100")

    def upload(self, tag: str, path: Path) -> None:
        self.run(["release", "upload", tag, str(path), "--repo", f"github.com/{REPOSITORY}"])

    def download(self, asset_id: int, path: Path) -> None:
        with path.open("xb") as stream:
            path.chmod(0o600)
            self.run(["api", "--hostname", "github.com", f"{API_ROOT}/releases/assets/{asset_id}",
                      "-H", "Accept: application/octet-stream"], stdout=stream)
            stream.flush()
            os.fsync(stream.fileno())


def check_release(value: object, tag: str, source_commit: str, *, draft: bool,
                  release_id: int | None = None) -> int:
    if (not isinstance(value, dict) or type(value.get("id")) is not int or value["id"] <= 0
            or (release_id is not None and value["id"] != release_id)
            or value.get("tag_name") != tag or value.get("target_commitish") != source_commit
            or value.get("draft") is not draft or value.get("prerelease") is not False):
        raise contract.ContractError("the release identity, commit, or publication state does not match")
    if not draft and not value.get("published_at"):
        raise contract.ContractError("GitHub did not confirm release publication")
    return value["id"]


def publish(archive: Path, source_commit: str, *, github: GitHub | None = None) -> dict:
    if not isinstance(source_commit, str) or not SHA.fullmatch(source_commit):
        raise contract.ContractError("the internal source commit must be an exact Git SHA")
    archive = archive.absolute()
    if "#" in str(archive):
        raise contract.ContractError("the archive path must not contain GitHub's asset-label separator")
    manifest, expected = verify_local(archive)
    receipt_path = archive / RECEIPT_NAME
    if receipt_path.exists() or receipt_path.is_symlink():
        raise contract.ContractError("an off-device receipt already exists; refusing to overwrite it")
    github = github or GitHub()
    require_private_repository(github.api(API_ROOT))
    commit = github.api(f"{API_ROOT}/commits/{source_commit}")
    if not isinstance(commit, dict) or commit.get("sha") != source_commit:
        raise contract.ContractError("the exact source commit does not exist in the private repository")
    tag = f"database-backup-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex}"
    if github.api(f"{API_ROOT}/git/matching-refs/tags/{tag}") != []:
        raise contract.ContractError("the release tag already exists; refusing to reuse it")
    with tempfile.TemporaryDirectory(prefix=".github-backup-", dir=archive.parent) as temporary:
        staged = Path(temporary)
        # Only these two files cross the boundary. Freeze their bytes before
        # creating a release; changes to the original never change an upload.
        for name in ASSET_NAMES:
            shutil.copyfile(archive / name, staged / name)
            (staged / name).chmod(0o600)
        verify_downloads(staged, expected)
        require_private_repository(github.api(API_ROOT))
        release = github.api(f"{API_ROOT}/releases", method="POST", payload={
            "tag_name": tag, "target_commitish": source_commit, "name": tag,
            "draft": True, "prerelease": False, "make_latest": "false",
            "generate_release_notes": False,
        })
        release_id = check_release(release, tag, source_commit, draft=True)
        endpoint = f"{API_ROOT}/releases/{release_id}"
        for name in ASSET_NAMES:
            check_release(github.api(endpoint), tag, source_commit, draft=True, release_id=release_id)
            require_private_repository(github.api(API_ROOT))
            github.upload(tag, staged / name)
        assets = verify_assets(github.assets(release_id), expected)
        downloaded = staged / "downloaded"
        downloaded.mkdir(mode=0o700)
        for name in ASSET_NAMES:
            github.download(assets[name]["id"], downloaded / name)
        verify_downloads(downloaded, expected)
        if verify_assets(github.assets(release_id), expected) != assets:
            raise contract.ContractError("the remote assets changed during readback")
        check_release(github.api(endpoint), tag, source_commit, draft=True, release_id=release_id)
        require_private_repository(github.api(API_ROOT))
        published = github.api(endpoint, method="PATCH", payload={"draft": False, "make_latest": "false"})
        check_release(published, tag, source_commit, draft=False, release_id=release_id)
        require_private_repository(github.api(API_ROOT))
        check_release(github.api(endpoint), tag, source_commit, draft=False, release_id=release_id)
        if verify_assets(github.assets(release_id), expected) != assets:
            raise contract.ContractError("the published assets do not match the verified readback")
        ref = github.api(f"{API_ROOT}/git/ref/tags/{tag}")
        if (not isinstance(ref, dict) or not isinstance(ref.get("object"), dict)
                or ref["object"].get("type") != "commit" or ref["object"].get("sha") != source_commit):
            raise contract.ContractError("the published tag does not bind the exact internal source commit")
        receipt = {
            "schema": "openadapt.database-backup-github-release/v1", "scope": "production",
            "repository": REPOSITORY, "repository_visibility_verified": "private",
            "release_id": release_id, "tag": tag, "source_commit": source_commit,
            "url": f"https://github.com/{REPOSITORY}/releases/tag/{tag}",
            "verified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "artifact_sha256": manifest["artifact_sha256"], "assets": assets,
            "off_device_verified": True, "download_readback_verified": True,
            "database_capture_performed": False, "database_restored": False, "storage_restored": False,
        }
        with receipt_path.open("x") as stream:
            receipt_path.chmod(0o600)
            json.dump(receipt, stream, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--source-commit", required=True, help="exact commit in the private destination repository")
    args = parser.parse_args()
    os.umask(0o077)
    try:
        receipt = publish(args.archive, args.source_commit)
    except (contract.ContractError, OSError, ValueError, TypeError, KeyError):
        # Neither raw subprocess errors nor untrusted manifest values belong
        # in terminal output. Preserve all originals and any draft for review.
        parser.exit(1, "Private backup transport failed; no off-device success is claimed.\n")
    print(json.dumps({"off_device_verified": True, "release_id": receipt["release_id"],
                      "receipt": str(args.archive / RECEIPT_NAME)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
