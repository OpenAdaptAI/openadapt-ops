#!/usr/bin/env python3
"""Check private backup age without downloading ciphertext or accessing a database.

Success is silent. Only the published manifest's capture time can establish
freshness. A draft upload or a release metadata update cannot reset that time.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import private_database_backup_release as transport

contract = transport.contract
MAXIMUM_AGE_SECONDS = 26 * 60 * 60
MAXIMUM_MANIFEST_BYTES = 64 * 1024
MAXIMUM_RELEASE_PAGES = 10
TAG = re.compile(r"database-backup-(\d{8}T\d{6}Z)-[0-9a-f]{32}")


def timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise contract.ContractError("the release timestamp is missing")
    return contract.parse_time(value, "release timestamp")


def published_candidate(releases: list, *, now: datetime) -> dict:
    candidates = []
    ids = set()
    for entry in releases:
        if not isinstance(entry, dict) or not isinstance(entry.get("tag_name"), str):
            raise contract.ContractError("the release inventory is invalid")
        if not entry["tag_name"].startswith("database-backup-"):
            continue
        if entry.get("draft") is True:
            # Failed captures/uploads cannot advance the last published point.
            continue
        tag = TAG.fullmatch(entry["tag_name"])
        if tag is None:
            raise contract.ContractError("a published backup tag is invalid")
        tag_time = datetime.strptime(tag.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        commit = entry.get("target_commitish")
        if not isinstance(commit, str) or transport.SHA.fullmatch(commit) is None:
            raise contract.ContractError("the backup release does not bind an exact internal source commit")
        release_id = transport.check_release(entry, entry["tag_name"], commit, draft=False)
        if release_id in ids:
            raise contract.ContractError("the release inventory contains a duplicate backup")
        ids.add(release_id)
        published = timestamp(entry.get("published_at"))
        if published > now or tag_time > now:
            raise contract.ContractError("a backup release timestamp is in the future")
        candidates.append((published, release_id, entry))
    if not candidates:
        raise contract.ContractError("no published production backup is available")
    return max(candidates, key=lambda value: value[:2])[2]


def inventory(github: transport.GitHub) -> list:
    result = []
    for page in range(1, MAXIMUM_RELEASE_PAGES + 1):
        entries = github.api(f"{transport.API_ROOT}/releases?per_page=100&page={page}")
        if not isinstance(entries, list) or len(entries) > 100:
            raise contract.ContractError("the release inventory is invalid")
        result.extend(entries)
        if len(entries) < 100:
            return result
    # Never claim that a truncated result identifies the newest publication.
    raise contract.ContractError("the release inventory exceeds the bounded inspection limit")


def metadata_expected(assets: list) -> dict:
    """Check the exact asset inventory before selecting a bounded download."""
    if not isinstance(assets, list):
        raise contract.ContractError("the release asset inventory is invalid")
    expected = {}
    for asset in assets:
        if not isinstance(asset, dict):
            raise contract.ContractError("the release asset metadata is invalid")
        name, size, digest = asset.get("name"), asset.get("size"), asset.get("digest")
        if (not isinstance(name, str) or name not in transport.ASSET_NAMES or name in expected
                or type(size) is not int or not 0 < size < transport.ASSET_LIMIT
                or not isinstance(digest, str) or not digest.startswith("sha256:")
                or contract.SHA256.fullmatch(digest[7:]) is None):
            raise contract.ContractError("the release asset inventory or integrity fields are invalid")
        expected[name] = {"bytes": size, "sha256": digest[7:]}
    if set(expected) != set(transport.ASSET_NAMES):
        raise contract.ContractError("the release asset inventory is incomplete")
    if expected[transport.ASSET_NAMES[1]]["bytes"] > MAXIMUM_MANIFEST_BYTES:
        raise contract.ContractError("the backup manifest exceeds its download limit")
    transport.verify_assets(assets, expected)
    return expected


def check(*, github: transport.GitHub | None = None, now: datetime | None = None) -> dict:
    now = now if now is not None else datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise contract.ContractError("the freshness check requires a timezone-aware clock")
    now = now.astimezone(timezone.utc)
    github = github or transport.GitHub()
    transport.require_private_repository(github.api(transport.API_ROOT))
    selected = published_candidate(inventory(github), now=now)
    release_id, tag, commit = selected["id"], selected["tag_name"], selected["target_commitish"]
    endpoint = f"{transport.API_ROOT}/releases/{release_id}"
    current = github.api(endpoint)
    transport.check_release(current, tag, commit, draft=False, release_id=release_id)
    if current.get("published_at") != selected["published_at"]:
        raise contract.ContractError("the backup publication changed during inspection")
    remote_assets = github.assets(release_id)
    expected = metadata_expected(remote_assets)
    identities = transport.verify_assets(remote_assets, expected)
    manifest_name = transport.ASSET_NAMES[1]
    with tempfile.TemporaryDirectory(prefix="openadapt-backup-freshness-") as temporary:
        path = Path(temporary) / manifest_name
        github.download(identities[manifest_name]["id"], path)
        transport.private_path(path)
        if path.stat().st_size != expected[manifest_name]["bytes"]:
            raise contract.ContractError("the downloaded manifest size does not match")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected[manifest_name]["sha256"]:
            raise contract.ContractError("the downloaded manifest digest does not match")
        manifest = transport.redacted_manifest(json.loads(data, object_pairs_hook=transport.unique_json_fields))
        # The independent manifest, not its own remote metadata, supplies the
        # ciphertext hash and size. The hourly reader does not download it.
        expected[transport.ASSET_NAMES[0]] = manifest["artifact"]["ciphertext_archive"]
        transport.verify_assets(remote_assets, expected)
        captured = timestamp(manifest["artifact"]["local_execution"]["created_at"])
        age = (now - captured).total_seconds()
        if age < 0:
            raise contract.ContractError("the backup capture time is in the future")
        if captured > timestamp(selected["published_at"]):
            raise contract.ContractError("the backup capture time follows its publication")
        if age > MAXIMUM_AGE_SECONDS:
            raise contract.ContractError("the production backup is older than 26 hours")
    if transport.verify_assets(github.assets(release_id), expected) != identities:
        raise contract.ContractError("the remote backup assets changed during inspection")
    current = github.api(endpoint)
    transport.check_release(current, tag, commit, draft=False, release_id=release_id)
    if current.get("published_at") != selected["published_at"]:
        raise contract.ContractError("the backup publication changed during inspection")
    ref = github.api(f"{transport.API_ROOT}/git/ref/tags/{tag}")
    if (not isinstance(ref, dict) or not isinstance(ref.get("object"), dict)
            or ref["object"].get("type") != "commit" or ref["object"].get("sha") != commit):
        raise contract.ContractError("the backup tag does not bind the exact internal source commit")
    transport.require_private_repository(github.api(transport.API_ROOT))
    return {"schema": "openadapt.database-backup-github-freshness/v1", "fresh": True,
            "age_seconds": int(age), "maximum_age_seconds": MAXIMUM_AGE_SECONDS,
            "release_id": release_id, "ciphertext_downloaded": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    os.umask(0o077)
    try:
        check()
    except (contract.ContractError, OSError, ValueError, TypeError, KeyError):
        parser.exit(1, "Private database backup freshness is unverified.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
