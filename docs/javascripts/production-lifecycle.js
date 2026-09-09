/*
 * Derive public Production labels from the current canonical admission record.
 * Static page text stays useful when the record is unavailable. A page can only
 * gain a Production label after this module validates the complete live record.
 */
(function productionLifecycleModule(root, factory) {
  "use strict";

  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.OpenAdaptProductionLifecycle = api;

  if (root.document && typeof root.fetch === "function") {
    const refresh = () => api.refresh(root.document, root.fetch.bind(root));
    if (root.document.readyState === "loading") {
      root.document.addEventListener("DOMContentLoaded", refresh, { once: true });
    } else {
      refresh();
    }
    if (root.document$ && typeof root.document$.subscribe === "function") {
      root.document$.subscribe(refresh);
    }
  }
})(typeof globalThis === "undefined" ? this : globalThis, function factory() {
  "use strict";

  const TARGET_REQUIREMENT = "No current verified Production admission.";
  const PRODUCT_REQUIREMENT =
    "Not currently Production across all seven targets.";
  const PROJECTION_URL = "/production-lifecycle.json";
  const ADMISSIONS_URL =
    "https://raw.githubusercontent.com/OpenAdaptAI/.github/main/production-lifecycle-admissions.json";
  const EXPECTED_TARGETS = Object.freeze({
    agent: ["qualified_agent_bridge_release", "public_package"],
    capture: ["qualified_native_recorder_release", "public_package"],
    cloud: ["qualified_workflow_control_plane_deployment", "private_deployment"],
    desktop: ["qualified_native_workflow_desktop_release", "public_package"],
    docs: ["production_documentation_deployment", "public_deployment"],
    flow: ["qualified_workflow_runtime_release", "public_package"],
    openadapt: ["qualified_workflow_launcher_release", "public_package"],
  });
  const V2_TARGETS = Object.freeze({
    agent: { claimScope: "production_agent", releaseKind: "package" },
    capture: { claimScope: "production_capture", releaseKind: "package" },
    cloud: { claimScope: "production_cloud", releaseKind: "deployment" },
    desktop: { claimScope: "production_desktop", releaseKind: "package" },
    docs: { claimScope: "production_docs", releaseKind: "deployment" },
    flow: { claimScope: "production_flow", releaseKind: "package" },
    openadapt: { claimScope: "production_openadapt", releaseKind: "package" },
  });
  const TARGET_IDS = Object.freeze(Object.keys(EXPECTED_TARGETS).sort());
  const PYPI_PROJECTS = Object.freeze({
    agent: "openadapt-agent",
    capture: "openadapt-capture",
    desktop: "openadapt-desktop",
    flow: "openadapt-flow",
    openadapt: "openadapt",
  });
  const EXPECTED_SOURCE_FILES = Object.freeze({
    admissions: "production-lifecycle-admissions.json",
    admissions_schema: "schemas/production-lifecycle-admissions.schema.json",
    evidence_registry: "evidence-registry.json",
    evidence_registry_schema: "schemas/evidence-registry.schema.json",
    evidence_registry_validator: "scripts/validate_evidence_registry.py",
    evidence_manifest_schema:
      "schemas/production-lifecycle-evidence-manifest.schema.json",
    evidence_summary_schema:
      "schemas/production-lifecycle-evidence-summary.schema.json",
    lifecycle: "repository-lifecycle.yml",
    policy: "production-lifecycle-policy.json",
    policy_schema: "schemas/production-lifecycle-policy.schema.json",
    validator: "scripts/validate_production_lifecycle.py",
  });
  const HEX40 = /^[0-9a-f]{40}$/;
  const DIGEST = /^sha256:[0-9a-f]{64}$/;
  const VERSION = /^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$/;
  const TIMESTAMP = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;
  let requestSequence = 0;
  let refreshGeneration = 0;

  function isObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function hasExactKeys(value, keys) {
    return (
      isObject(value) &&
      Object.keys(value).sort().join("\u0000") === [...keys].sort().join("\u0000")
    );
  }

  function isHttpsUrl(value) {
    if (typeof value !== "string") return false;
    try {
      const parsed = new URL(value);
      return (
        parsed.protocol === "https:" &&
        parsed.username === "" &&
        parsed.password === ""
      );
    } catch (_error) {
      return false;
    }
  }

  function parseTimestamp(value) {
    if (typeof value !== "string" || !TIMESTAMP.test(value)) return null;
    const parsed = Date.parse(value);
    if (!Number.isFinite(parsed)) return null;
    return new Date(parsed).toISOString() === value.replace(/Z$/, ".000Z")
      ? parsed
      : null;
  }

  function sameJson(left, right) {
    return JSON.stringify(left) === JSON.stringify(right);
  }

  function validateSource(source) {
    if (
      !hasExactKeys(source, ["schema_version", "repository", "source_commit", "files"]) ||
      source.schema_version !== "openadapt.production-lifecycle-source/v1" ||
      source.repository !== "OpenAdaptAI/.github" ||
      !HEX40.test(source.source_commit) ||
      !isObject(source.files)
    ) {
      return false;
    }
    if (!hasExactKeys(source.files, Object.keys(EXPECTED_SOURCE_FILES))) return false;
    const prefix = `https://raw.githubusercontent.com/OpenAdaptAI/.github/${source.source_commit}/`;
    return Object.entries(EXPECTED_SOURCE_FILES).every(([key, path]) => {
      const item = source.files[key];
      return (
        hasExactKeys(item, ["path", "url", "sha256"]) &&
        item.path === path &&
        item.url === `${prefix}${path}` &&
        DIGEST.test(item.sha256)
      );
    });
  }

  function validateProjection(projection) {
    if (
      !isObject(projection) ||
      projection.schema_version !== "openadapt.public-production-lifecycle/v1" ||
      projection.$schema !== "schemas/production-lifecycle-public.schema.json" ||
      !validateSource(projection.source) ||
      !Number.isInteger(projection.policy_revision) ||
      projection.policy_revision < 1 ||
      !Number.isInteger(projection.maximum_admission_days) ||
      projection.maximum_admission_days < 1 ||
      !hasExactKeys(projection.derivation, [
        "mode",
        "static_production_state",
        "expired_or_revoked_latest_behavior",
        "fallback_to_older_release",
      ]) ||
      projection.derivation.mode !== "latest_signed_admission_at_read_time" ||
      projection.derivation.static_production_state !== false ||
      projection.derivation.expired_or_revoked_latest_behavior !== "no_production" ||
      projection.derivation.fallback_to_older_release !== false ||
      !Array.isArray(projection.targets) ||
      projection.targets.length !== TARGET_IDS.length
    ) {
      return null;
    }

    const targets = new Map();
    for (const target of projection.targets) {
      if (
        !hasExactKeys(target, [
          "id",
          "display_name",
          "lifecycle_scope",
          "lifecycle_subject",
          "source_repository",
          "release_kind",
          "required_claim_scope",
          "required_artifact_kinds",
          "package_index_project",
          "artifact_authority_by_kind",
          "latest_admission",
          "admission_history",
        ]) ||
        !TARGET_IDS.includes(target.id) ||
        targets.has(target.id)
      ) {
        return null;
      }
      const [claimScope, releaseKind] = EXPECTED_TARGETS[target.id];
      if (
        target.required_claim_scope !== claimScope ||
        target.release_kind !== releaseKind ||
        typeof target.display_name !== "string" ||
        !["repository", "public_surface"].includes(target.lifecycle_scope) ||
        typeof target.lifecycle_subject !== "string" ||
        !/^OpenAdaptAI\/[A-Za-z0-9._-]+$/.test(target.source_repository) ||
        !Array.isArray(target.required_artifact_kinds) ||
        !isObject(target.artifact_authority_by_kind) ||
        !Array.isArray(target.admission_history)
      ) {
        return null;
      }
      const ordered = [...target.admission_history].sort(
        (left, right) =>
          left?.release_identity?.sequence - right?.release_identity?.sequence,
      );
      if (!sameJson(ordered, target.admission_history)) return null;
      let previousSequence = 0;
      for (const admission of ordered) {
        const sequence = admission?.release_identity?.sequence;
        if (!Number.isInteger(sequence) || sequence <= previousSequence) return null;
        previousSequence = sequence;
      }
      const latest = ordered.length ? ordered[ordered.length - 1] : null;
      if (!sameJson(latest, target.latest_admission)) return null;
      targets.set(target.id, target);
    }
    if (!TARGET_IDS.every((targetId) => targets.has(targetId))) return null;
    return targets;
  }

  function isObjectReferenceRow(admission) {
    return (
      isObject(admission) &&
      admission.kind === "qualification-release" &&
      typeof admission.object_path === "string" &&
      typeof admission.target !== "string"
    );
  }

  function latestAdmissionsAreUntilRevoked(targets) {
    for (const targetId of TARGET_IDS) {
      const admission = targets.get(targetId)?.latest_admission;
      if (
        !isObject(admission) ||
        admission.expires_at !== null ||
        admission.revoked_at != null
      ) {
        return false;
      }
    }
    return true;
  }

  function issuedPolicyBindsOrUntilRevoked(value, projection, targets, policy) {
    if (!DIGEST.test(value.policy_sha256)) return false;
    if (value.policy_sha256 === projection.source.files.policy.sha256) return true;
    return (
      isObject(policy) &&
      policy.admission_validity === "until_revoked" &&
      latestAdmissionsAreUntilRevoked(targets)
    );
  }

  function validateLiveAdmissions(value, projection, targets, policy = null) {
    if (
      !hasExactKeys(value, ["$schema", "schema_version", "policy_sha256", "admissions"]) ||
      value.$schema !== "schemas/production-lifecycle-admissions.schema.json" ||
      value.schema_version !== "openadapt.production-lifecycle-admissions/v1" ||
      !Array.isArray(value.admissions) ||
      !issuedPolicyBindsOrUntilRevoked(value, projection, targets, policy)
    ) {
      return false;
    }
    const byTarget = new Map(TARGET_IDS.map((id) => [id, []]));
    let objectRefCount = 0;
    for (const admission of value.admissions) {
      if (!isObject(admission)) return false;
      if (isObjectReferenceRow(admission)) {
        objectRefCount += 1;
        continue;
      }
      if (!byTarget.has(admission.target)) return false;
      byTarget.get(admission.target).push(admission);
    }
    for (const targetId of TARGET_IDS) {
      const live = byTarget
        .get(targetId)
        .sort((left, right) => left?.release_identity?.sequence - right?.release_identity?.sequence);
      if (live.length === 0 && objectRefCount > 0) continue;
      if (!sameJson(live, targets.get(targetId).admission_history)) return false;
    }
    return true;
  }

  function deriveTargetV2(target, now) {
    const spec = V2_TARGETS[target.id];
    const admission = target.latest_admission;
    if (!spec || !isObject(admission)) return null;
    const identity = admission.release_identity;
    const release = admission.release;
    const issuedAt = parseTimestamp(admission.issued_at);
    if (
      admission.target !== target.id ||
      admission.claim_scope !== spec.claimScope ||
      admission.verdict !== "accepted" ||
      admission.expires_at !== null ||
      admission.revoked_at != null ||
      admission.evidence_class !== "remote-safe-synthetic" ||
      issuedAt === null ||
      issuedAt > now ||
      !isObject(identity) ||
      identity.schema_version !== "openadapt.monotonic-production-release/v1" ||
      identity.channel !== "production" ||
      !Number.isInteger(identity.sequence) ||
      identity.sequence < 1 ||
      !isObject(release) ||
      release.kind !== spec.releaseKind
    ) {
      return null;
    }
    let releaseLabel;
    let releaseVersion = null;
    if (spec.releaseKind === "package" && VERSION.test(release.version)) {
      releaseLabel = `release ${release.version}`;
      releaseVersion = release.version;
    } else if (
      spec.releaseKind === "deployment" &&
      typeof release.deployment_id === "string" &&
      release.deployment_id.length > 0
    ) {
      releaseLabel = `deployment ${release.deployment_id}`;
    } else {
      return null;
    }
    return Object.freeze({
      targetId: target.id,
      releaseLabel,
      releaseVersion,
      summaryUrl: null,
      evidence: { class: admission.evidence_class },
      release,
      untilRevoked: true,
      admission,
      target,
    });
  }

  function deriveTarget(target, projection, now = Date.now()) {
    const untilRevoked = deriveTargetV2(target, now);
    if (untilRevoked) return untilRevoked;
    const admission = target.latest_admission;
    if (!isObject(admission)) return null;
    const [claimScope, releaseKind] = EXPECTED_TARGETS[target.id];
    const identity = admission.release_identity;
    const release = admission.release;
    const evidence = admission.acceptance_evidence;
    const issuedAt = parseTimestamp(admission.issued_at);
    const expiresAt = parseTimestamp(admission.expires_at);
    if (
      admission.target !== target.id ||
      admission.claim_scope !== claimScope ||
      admission.policy_revision !== projection.policy_revision ||
      !isObject(identity) ||
      identity.schema_version !== "openadapt.monotonic-production-release/v1" ||
      identity.channel !== "production" ||
      !Number.isInteger(identity.sequence) ||
      identity.sequence < 1 ||
      !isObject(release) ||
      release.kind !== releaseKind ||
      !isObject(evidence) ||
      !isHttpsUrl(evidence.summary_url) ||
      !DIGEST.test(evidence.summary_sha256) ||
      !isHttpsUrl(evidence.attestation_bundle_url) ||
      !DIGEST.test(evidence.attestation_bundle_sha256) ||
      !HEX40.test(evidence.authority_source_commit) ||
      issuedAt === null ||
      expiresAt === null ||
      issuedAt > now ||
      expiresAt <= now ||
      expiresAt <= issuedAt ||
      expiresAt - issuedAt > projection.maximum_admission_days * 86400000 ||
      admission.revoked_at !== null
    ) {
      return null;
    }

    let releaseLabel;
    if (
      releaseKind === "public_package" &&
      VERSION.test(release.version) &&
      typeof release.tag === "string" &&
      Array.isArray(release.artifacts)
    ) {
      releaseLabel = `release ${release.version}`;
    } else if (
      releaseKind === "public_deployment" &&
      typeof release.deployment_id === "string" &&
      release.deployment_id.length > 0 &&
      Array.isArray(release.artifacts)
    ) {
      releaseLabel = `deployment ${release.deployment_id}`;
    } else if (
      releaseKind === "private_deployment" &&
      typeof release.deployment_release_id === "string" &&
      release.deployment_release_id.length > 0
    ) {
      releaseLabel = `deployment release ${release.deployment_release_id}`;
    } else {
      return null;
    }
    return Object.freeze({
      targetId: target.id,
      releaseLabel,
      releaseVersion:
        releaseKind === "public_package" ? release.version : null,
      summaryUrl: evidence.summary_url,
      admission,
      target,
    });
  }

  async function sha256(bytes) {
    if (!globalThis.crypto?.subtle) throw new Error("SHA-256 is unavailable");
    const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
    return (
      "sha256:" +
      [...new Uint8Array(digest)]
        .map((value) => value.toString(16).padStart(2, "0"))
        .join("")
    );
  }

  function cacheBustedUrl(url, now) {
    requestSequence += 1;
    const separator = url.includes("?") ? "&" : "?";
    return `${url}${separator}openadapt_lifecycle_request=${now}-${requestSequence}`;
  }

  async function fetchJson(fetchImpl, url, now) {
    const response = await fetchImpl(cacheBustedUrl(url, now), {
      cache: "no-store",
      credentials: "omit",
    });
    if (!response.ok) return null;
    const value = await response.json();
    return isObject(value) ? value : null;
  }

  async function fetchBytes(fetchImpl, url, now) {
    const response = await fetchImpl(cacheBustedUrl(url, now), {
      cache: "no-store",
      credentials: "omit",
    });
    if (!response.ok) return null;
    return new Uint8Array(await response.arrayBuffer());
  }

  function validateArtifact(artifact, target) {
    return (
      hasExactKeys(artifact, [
        "name",
        "kind",
        "authority",
        "url",
        "sha256",
        "size_bytes",
      ]) &&
      typeof artifact.name === "string" &&
      artifact.name.length > 0 &&
      typeof artifact.kind === "string" &&
      target.required_artifact_kinds.includes(artifact.kind) &&
      artifact.authority === target.artifact_authority_by_kind[artifact.kind] &&
      isHttpsUrl(artifact.url) &&
      DIGEST.test(artifact.sha256) &&
      Number.isInteger(artifact.size_bytes) &&
      artifact.size_bytes > 0
    );
  }

  async function verifyEvidenceAuthority(active, fetchImpl, now) {
    const reference = active.admission.acceptance_evidence;
    const [summaryBytes, bundleBytes] = await Promise.all([
      fetchBytes(fetchImpl, reference.summary_url, now),
      fetchBytes(fetchImpl, reference.attestation_bundle_url, now),
    ]);
    if (!summaryBytes || !bundleBytes) return false;
    if (
      (await sha256(summaryBytes)) !== reference.summary_sha256 ||
      (await sha256(bundleBytes)) !== reference.attestation_bundle_sha256
    ) {
      return false;
    }

    const summary = JSON.parse(new TextDecoder().decode(summaryBytes));
    if (
      !isObject(summary) ||
      summary.schema_version !== "openadapt.production-lifecycle-evidence-summary/v1" ||
      summary.target !== active.targetId ||
      summary.verdict !== "accepted" ||
      summary.claim_scope !== active.admission.claim_scope ||
      !isObject(summary.evidence_manifest)
    ) {
      return false;
    }
    const manifest = summary.evidence_manifest;
    if (
      manifest.schema_version !== "openadapt.production-acceptance/v1" ||
      !isHttpsUrl(manifest.url) ||
      !DIGEST.test(manifest.sha256)
    ) {
      return false;
    }
    const manifestBytes = await fetchBytes(fetchImpl, manifest.url, now);
    return manifestBytes !== null && (await sha256(manifestBytes)) === manifest.sha256;
  }

  async function verifyPypiArtifacts(active, artifacts, fetchImpl, now) {
    if (!artifacts.length) return true;
    const project = active.target.package_index_project;
    if (project !== PYPI_PROJECTS[active.targetId]) return false;
    const metadata = await fetchJson(
      fetchImpl,
      `https://pypi.org/pypi/${encodeURIComponent(project)}/json`,
      now,
    );
    if (
      !metadata ||
      !isObject(metadata.info) ||
      metadata.info.version !== active.releaseVersion ||
      !isObject(metadata.releases)
    ) {
      return false;
    }
    const files = metadata.releases[active.releaseVersion];
    if (!Array.isArray(files)) return false;
    return artifacts.every((artifact) => {
      const packageType = artifact.kind === "wheel" ? "bdist_wheel" : "sdist";
      return (
        files.filter(
          (file) =>
            isObject(file) &&
            file.filename === artifact.name &&
            file.url === artifact.url &&
            file.size === artifact.size_bytes &&
            file.packagetype === packageType &&
            file.yanked === false &&
            isObject(file.digests) &&
            file.digests.sha256 === artifact.sha256.slice("sha256:".length),
        ).length === 1
      );
    });
  }

  async function verifyGithubArtifacts(active, artifacts, fetchImpl, now) {
    if (!artifacts.length) return true;
    const release = active.admission.release;
    if (typeof release.tag !== "string" || release.tag.length === 0) return false;
    const metadata = await fetchJson(
      fetchImpl,
      `https://api.github.com/repos/${active.target.source_repository}/releases/tags/${encodeURIComponent(release.tag)}`,
      now,
    );
    if (
      !metadata ||
      metadata.tag_name !== release.tag ||
      metadata.draft !== false ||
      metadata.prerelease !== false ||
      metadata.immutable !== true ||
      !Array.isArray(metadata.assets)
    ) {
      return false;
    }
    return artifacts.every(
      (artifact) =>
        metadata.assets.filter(
          (asset) =>
            isObject(asset) &&
            asset.name === artifact.name &&
            asset.url === artifact.url &&
            asset.size === artifact.size_bytes &&
            asset.digest === artifact.sha256 &&
            asset.state === "uploaded",
        ).length === 1,
    );
  }

  async function verifyManagedArtifacts(artifacts, fetchImpl, now) {
    const checks = await Promise.all(
      artifacts.map(async (artifact) => {
        const digest = artifact.sha256.slice("sha256:".length);
        const metadata = await fetchJson(
          fetchImpl,
          `https://evidence.openadapt.ai/api/v1/objects/sha256/${digest}`,
          now,
        );
        return (
          hasExactKeys(metadata, [
            "schema_version",
            "exists",
            "artifact_url",
            "sha256",
            "size_bytes",
            "object_version_sha256",
            "head_verified",
          ]) &&
          metadata.schema_version === "openadapt.managed-artifact-head/v1" &&
          metadata.exists === true &&
          metadata.artifact_url === artifact.url &&
          metadata.sha256 === artifact.sha256 &&
          metadata.size_bytes === artifact.size_bytes &&
          DIGEST.test(metadata.object_version_sha256) &&
          metadata.head_verified === true
        );
      }),
    );
    return checks.every(Boolean);
  }

  async function verifyArtifactAuthorities(active, fetchImpl, now) {
    const release = active.admission.release;
    const requiredKinds = active.target.required_artifact_kinds;
    const artifacts = release.kind === "private_deployment" ? [] : release.artifacts;
    if (!Array.isArray(artifacts)) return false;
    if (!artifacts.every((artifact) => validateArtifact(artifact, active.target))) {
      return false;
    }
    const presentKinds = new Set(artifacts.map((artifact) => artifact.kind));
    if (!requiredKinds.every((kind) => presentKinds.has(kind))) return false;

    const byAuthority = (authority) =>
      artifacts.filter((artifact) => artifact.authority === authority);
    const [pypi, github, managed] = await Promise.all([
      verifyPypiArtifacts(active, byAuthority("pypi"), fetchImpl, now),
      verifyGithubArtifacts(active, byAuthority("github_release"), fetchImpl, now),
      verifyManagedArtifacts(byAuthority("managed_evidence"), fetchImpl, now),
    ]);
    return pypi && github && managed;
  }

  async function verifyTargetAuthorities(active, fetchImpl, now) {
    try {
      const [evidence, artifacts] = await Promise.all([
        verifyEvidenceAuthority(active, fetchImpl, now),
        verifyArtifactAuthorities(active, fetchImpl, now),
      ]);
      return evidence && artifacts;
    } catch (_error) {
      return false;
    }
  }

  // This is a build-time result from the canonical verifier, not a signature.
  // The same-origin generated file is trusted only through the reviewed build.
  const VERIFICATIONS_URL = "/production-lifecycle-verifications.json";
  const CANONICAL_API = "https://api.github.com/repos/OpenAdaptAI/.github";
  const CANONICAL_RAW = "https://raw.githubusercontent.com/OpenAdaptAI/.github";
  const REFERENCE_FIELDS = ["kind", "object_schema_version", "object_path", "object_sha256",
    "size_bytes", "object_media_type", "semantic_identity_sha256", "subject_sha256",
    "registry_entry_sha256"];
  const RECEIPT_FIELDS = ["schema_version", "verification_id_sha256", "verdict", "evidence_class",
    "target", "claim_scope", "admission_object_sha256", "admission_bundle_object_sha256",
    "admission_id_sha256", "release_sha256", "artifact_inventory_sha256", "release_identity",
    "source_repository", "source_repository_id", "source_commit", "version", "tag",
    "draft_release_id", "publication_staging_sha256", "authority_state_sha256",
    "revocation_state_sha256", "signer_registry_sha256", "acceptance_summary_object_sha256",
    "acceptance_manifest_object_sha256", "decision_receipt_object_sha256",
    "qualification_admission_object_sha256", "qualification_admission_id_sha256",
    "workflow_version_id_sha256", "workflow_bundle_sha256", "admitted_runtime_sha256",
    "verified_at", "expires_at", "registry_source_commit", "registry_revision",
    "registry_head_sha256", "trust_state_source_commit"];

  function canonical(value) {
    if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
    if (isObject(value)) return `{${Object.keys(value).sort().map(
      (key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(",")}}`;
    return JSON.stringify(value);
  }

  function sameValue(left, right) { return canonical(left) === canonical(right); }

  function validReference(ref, kind) {
    return isObject(ref) && ref.kind === kind &&
      ref.repository === "OpenAdaptAI/.github" && HEX40.test(ref.registry_source_commit) &&
      DIGEST.test(ref.object_sha256) && Number.isInteger(ref.size_bytes) && ref.size_bytes > 0 &&
      ref.object_path === `production-evidence/objects/sha256/${ref.object_sha256.slice(7, 9)}/${ref.object_sha256.slice(7)}.${kind}.json`;
  }

  async function verifiedObject(ref, kind, fetchImpl, now, commit = ref?.registry_source_commit) {
    if (!validReference(ref, kind) || !HEX40.test(commit)) return null;
    const bytes = await fetchBytes(fetchImpl, `${CANONICAL_RAW}/${commit}/${ref.object_path}`, now);
    if (!bytes || bytes.length !== ref.size_bytes || await sha256(bytes) !== ref.object_sha256) return null;
    const value = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
    return isObject(value) ? value : null;
  }

  function activeWindow(value, startKey, now, expectedStatus) {
    const start = parseTimestamp(value?.[startKey]);
    const end = value?.expires_at === null ? Infinity : parseTimestamp(value?.expires_at);
    return start !== null && start <= now && end !== null && end > now &&
      (expectedStatus === undefined || value.status === expectedStatus);
  }

  function lastPairMatches(registry, kind, ref, bundle) {
    const indexes = registry.entries.map((entry, index) => entry.kind === kind ? index : -1).filter((i) => i >= 0);
    if (!indexes.length) return false;
    const index = indexes[indexes.length - 1];
    return [ref, bundle].every((expected, offset) =>
      isObject(expected) && isObject(registry.entries[index + offset]) &&
      REFERENCE_FIELDS.every((key) => sameValue(expected[key], registry.entries[index + offset][key])));
  }

  function statementKeys(bundle, reference, now) {
    const envelope = bundle?.dsseEnvelope;
    if (!isObject(envelope) || !Array.isArray(envelope.signatures) || envelope.signatures.length !== 1) return null;
    const statement = JSON.parse(atob(envelope.payload));
    if (statement.schema_version !== "openadapt.production-public-trust-signing-statement/v1" ||
      !activeWindow(statement, "not_before", now) ||
      statement.object_sha256 !== reference.object_sha256 || statement.object_size_bytes !== reference.size_bytes ||
      statement.object_kind !== reference.kind || statement.semantic_identity_sha256 !== reference.semantic_identity_sha256 ||
      envelope.signatures[0].keyid !== statement.key_id || typeof statement.key_id !== "string") return null;
    return [statement.key_id];
  }

  async function verifyV2Pair(reference, bundleReference, kind, fetchImpl, now) {
    if (!isObject(reference) || !isObject(bundleReference) ||
      bundleReference.subject_sha256 !== reference.object_sha256 ||
      bundleReference.registry_source_commit !== reference.registry_source_commit) return null;
    const [object, bundle] = await Promise.all([
      verifiedObject(reference, kind, fetchImpl, now),
      verifiedObject(bundleReference, `${kind}-sigstore-bundle`, fetchImpl, now),
    ]);
    const keys = bundle && statementKeys(bundle, reference, now);
    if (!object || !keys) return null;
    if (Object.prototype.hasOwnProperty.call(object, "expires_at") &&
      !activeWindow(object, Object.prototype.hasOwnProperty.call(object, "not_before") ? "not_before" : "issued_at", now)) return null;
    return { object, keys };
  }

  async function currentV2State(record, fetchImpl, now, fresh, evidenceKeys) {
    const state = record.current_state;
    const { registry, commit } = fresh;
    if (!hasExactKeys(state, ["authority_reference", "authority_bundle_reference", "revocation_reference",
      "revocation_bundle_reference", "signer_registry_pointer"]) || !isObject(registry) ||
      registry.repository !== "OpenAdaptAI/.github" || !Array.isArray(registry.entries) ||
      !sameValue(registry.signer_registry, state.signer_registry_pointer)) return false;
    for (const [label, kind] of [["authority", "qualification-authority-state-receipt"],
      ["revocation", "qualification-revocation-state-receipt"]]) {
      if (!lastPairMatches(registry, kind, state[`${label}_reference`], state[`${label}_bundle_reference`])) return false;
    }
    const [authority, revocation, authorityBundle, revocationBundle] = await Promise.all([
      verifiedObject(state.authority_reference, "qualification-authority-state-receipt", fetchImpl, now, commit),
      verifiedObject(state.revocation_reference, "qualification-revocation-state-receipt", fetchImpl, now, commit),
      verifiedObject(state.authority_bundle_reference, "qualification-authority-state-receipt-sigstore-bundle", fetchImpl, now, commit),
      verifiedObject(state.revocation_bundle_reference, "qualification-revocation-state-receipt-sigstore-bundle", fetchImpl, now, commit),
    ]);
    const pointer = state.signer_registry_pointer;
    if (!isObject(pointer) || !DIGEST.test(pointer.object_sha256) ||
      pointer.object_path !== `production-evidence/signer-registries/sha256/${pointer.object_sha256.slice(7, 9)}/${pointer.object_sha256.slice(7)}.qualification-signer-registry.json`) return false;
    const signerBytes = await fetchBytes(fetchImpl, `${CANONICAL_RAW}/${commit}/${pointer.object_path}`, now);
    if (!signerBytes || await sha256(signerBytes) !== pointer.object_sha256) return false;
    const signer = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(signerBytes));
    if (!authorityBundle || !revocationBundle || !activeWindow(authority, "not_before", now, "active") ||
      !activeWindow(revocation, "not_before", now, "current") || !activeWindow(signer, "generated_at", now) ||
      signer.revision !== pointer.registry_revision || !Array.isArray(signer.signers) ||
      !Array.isArray(revocation.revocations)) return false;
    const receipt = record.verification_receipt;
    const signerIdentity = await sha256(new TextEncoder().encode(
      `OpenAdapt qualification signer registry v2\0${canonical(signer)}`));
    if (pointer.registry_identity_sha256 !== signerIdentity ||
      authority.signer_registry_sha256 !== pointer.object_sha256 ||
      authority.signer_registry_identity_sha256 !== signerIdentity ||
      authority.signer_registry_revision !== signer.revision ||
      revocation.signer_registry_sha256 !== signerIdentity ||
      revocation.authority_state_sha256 !== authority.authority_state_sha256 ||
      receipt.signer_registry_sha256 !== signerIdentity ||
      receipt.authority_state_sha256 !== authority.authority_state_sha256 ||
      receipt.revocation_state_sha256 !== revocation.revocation_state_sha256 ||
      state.authority_reference.semantic_identity_sha256 !== authority.authority_state_sha256 ||
      state.revocation_reference.semantic_identity_sha256 !== revocation.revocation_state_sha256) return false;
    const usedKeys = new Set([authority.issuer_key_id, revocation.issuer_key_id, ...evidenceKeys]);
    for (const [bundle, reference] of [[authorityBundle, state.authority_reference],
      [revocationBundle, state.revocation_reference]]) {
      const keys = statementKeys(bundle, reference, now);
      if (!keys) return false;
      for (const key of keys) usedKeys.add(key);
    }
    for (const keyId of usedKeys) {
      const keys = signer.signers.filter((key) => key.key_id === keyId);
      if (keys.length !== 1 || keys[0].status !== "active" ||
        (keys[0].revoked_at !== null && (parseTimestamp(keys[0].revoked_at) === null ||
          parseTimestamp(keys[0].revoked_at) <= now))) return false;
    }
    // Exact current bytes were cryptographically checked by the generator. A
    // different relevant object needs a new verification; registry append alone does not.
    const subjectIds = new Set([receipt.admission_id_sha256, receipt.admission_object_sha256,
      receipt.qualification_admission_id_sha256, receipt.qualification_admission_object_sha256,
      receipt.acceptance_summary_object_sha256, receipt.acceptance_manifest_object_sha256,
      receipt.decision_receipt_object_sha256]);
    return !revocation.revocations.some((item) => subjectIds.has(item.subject_id) ||
      (item.subject_kind === "qualification-signer-key" && signer.signers.some((key) =>
        key.status === "active" && key.public_key_sha256 === item.subject_id)));
  }

  async function verifyV2Receipt(active, record, liveAdmissions, fetchImpl, now) {
    if (!hasExactKeys(record, ["schema_version", "target", "admission_reference", "admission_bundle_reference",
      "verification_receipt", "current_state"]) || record.schema_version !== "openadapt.public-production-lifecycle-verification/v1" ||
      record.target !== active.targetId || !liveAdmissions.admissions.some((ref) => sameValue(ref, record.admission_reference))) return false;
    const ref = record.admission_reference;
    const bundleRef = record.admission_bundle_reference;
    const releasePair = await verifyV2Pair(ref, bundleRef, "qualification-release", fetchImpl, now);
    const admission = releasePair?.object;
    if (!admission || !activeWindow(admission, "not_before", now) || !sameValue(admission, active.admission)) return false;
    const receipt = record.verification_receipt;
    const v2 = active.targetId !== "flow";
    const fields = v2 ? [...RECEIPT_FIELDS, "release_kind", "deployment_id", "deployment_sha256"] : RECEIPT_FIELDS;
    if (!hasExactKeys(receipt, fields) || receipt.schema_version !== `openadapt.qualification-release-verification-receipt/v${v2 ? 2 : 1}` ||
      receipt.verdict !== "verified" || receipt.target !== active.targetId || receipt.evidence_class !== "remote-safe-synthetic" ||
      receipt.admission_object_sha256 !== ref.object_sha256 || receipt.admission_bundle_object_sha256 !== bundleRef.object_sha256 ||
      receipt.registry_source_commit !== ref.registry_source_commit || receipt.registry_revision !== ref.registry_revision ||
      receipt.registry_head_sha256 !== ref.registry_head_sha256 || !HEX40.test(receipt.trust_state_source_commit) ||
      parseTimestamp(receipt.verified_at) === null || parseTimestamp(receipt.verified_at) > now) return false;
    for (const key of ["claim_scope", "admission_id_sha256", "release_sha256", "artifact_inventory_sha256", "release_identity",
      "publication_staging_sha256", "authority_state_sha256", "revocation_state_sha256", "signer_registry_sha256", "expires_at"]) {
      if (!sameValue(receipt[key], admission[key])) return false;
    }
    for (const key of ["source_repository", "source_repository_id", "source_commit", "version", "tag"]) {
      if (receipt[key] !== admission.release[key]) return false;
    }
    if (v2 && (receipt.release_kind !== admission.release.kind || receipt.deployment_id !== admission.release.deployment_id ||
      receipt.deployment_sha256 !== admission.release.deployment_sha256)) return false;
    if (receipt.draft_release_id !== admission.publication_staging.draft_release_id ||
      receipt.acceptance_summary_object_sha256 !== admission.production_acceptance_summary_reference.object_sha256) return false;
    const projection = { ...receipt };
    delete projection.verification_id_sha256;
    const expected = await sha256(new TextEncoder().encode(
      `OpenAdapt qualification release verification receipt v${v2 ? 2 : 1}\0${canonical(projection)}`));
    if (expected !== receipt.verification_id_sha256 || !Object.values(record.current_state).every((item) =>
      !item.registry_source_commit || item.registry_source_commit === receipt.trust_state_source_commit)) return false;
    const summaryPair = await verifyV2Pair(admission.production_acceptance_summary_reference,
      admission.production_acceptance_summary_bundle_reference, "production-acceptance-summary", fetchImpl, now);
    if (!summaryPair) return false;
    const summary = summaryPair.object;
    const dependencies = [
      ["production_acceptance_manifest", "production-acceptance-manifest", "acceptance_manifest_object_sha256"],
      ["qualification_evidence_decision_receipt", "qualification-evidence-decision-receipt", "decision_receipt_object_sha256"],
      ["qualification_admission", "qualification-admission", "qualification_admission_object_sha256"],
    ];
    const pairs = await Promise.all(dependencies.map(async ([field, kind, receiptKey]) => {
      const reference = summary[`${field}_reference`];
      if (reference?.object_sha256 !== receipt[receiptKey]) return null;
      return verifyV2Pair(reference, summary[`${field}_bundle_reference`], kind, fetchImpl, now);
    }));
    if (pairs.some((pair) => !pair)) return false;
    const decision = pairs[1].object;
    const qualification = pairs[2].object;
    if (qualification.admission_id_sha256 !== receipt.qualification_admission_id_sha256 ||
      qualification.workflow_version_id_sha256 !== receipt.workflow_version_id_sha256 ||
      qualification.bundle_sha256 !== receipt.workflow_bundle_sha256 ||
      qualification.admitted_runtime_sha256 !== receipt.admitted_runtime_sha256) return false;
    return [...releasePair.keys, ...summaryPair.keys, ...pairs.flatMap((pair) => pair.keys), decision.issuer_key_id];
  }

  async function verifyV2Tag(active, fetchImpl, now) {
    const release = active.release;
    const base = `https://api.github.com/repos/${release.source_repository}`;
    let ref = await fetchJson(fetchImpl, `${base}/git/ref/tags/${encodeURIComponent(release.tag)}`, now);
    if (ref?.ref !== `refs/tags/${release.tag}`) return false;
    let object = ref.object;
    const seen = new Set();
    for (let depth = 0; object?.type === "tag" && depth < 5; depth += 1) {
      if (!HEX40.test(object.sha) || seen.has(object.sha)) return false;
      seen.add(object.sha);
      ref = await fetchJson(fetchImpl, `${base}/git/tags/${object.sha}`, now);
      if (ref?.sha !== object.sha) return false;
      object = ref.object;
    }
    return object?.type === "commit" && object.sha === release.source_commit;
  }

  async function verifyV2Artifacts(active, fetchImpl, now) {
    const { release, admission } = active;
    const staging = admission.publication_staging;
    const artifacts = release.artifacts;
    // Deployment manifests need a current public deployment observation. A
    // retained URL or synthetic record alone cannot prove a running deployment.
    if (release.kind !== "package" || !isObject(staging) || !Array.isArray(artifacts) || !artifacts.length ||
      release.source_repository !== active.target.source_repository || !HEX40.test(release.source_commit) ||
      !["already-published-pypi", "draft-before-tag"].includes(staging.publication_mode)) return false;
    const repo = `https://api.github.com/repos/${release.source_repository}`;
    const [metadata, pypi, tag] = await Promise.all([
      fetchJson(fetchImpl, `${repo}/releases/${staging.draft_release_id}`, now),
      fetchJson(fetchImpl, `https://pypi.org/pypi/${encodeURIComponent(PYPI_PROJECTS[active.targetId])}/json`, now),
      verifyV2Tag(active, fetchImpl, now),
    ]);
    if (!tag || !metadata || String(metadata.id) !== staging.draft_release_id || metadata.tag_name !== release.tag ||
      metadata.draft !== false || metadata.prerelease !== false || !Array.isArray(metadata.assets) ||
      metadata.author?.login !== staging.release_author_login || !pypi || pypi.info?.version !== release.version ||
      !Array.isArray(pypi.releases?.[release.version])) return false;
    const draftMode = staging.publication_mode === "draft-before-tag";
    if (draftMode && (metadata.immutable !== true || metadata.author?.login !== "openadapt-release[bot]" ||
      String(metadata.author?.id) !== staging.release_app_bot_user_id)) return false;
    const files = pypi.releases[release.version];
    for (const artifact of artifacts) {
      if (!hasExactKeys(artifact, ["name", "kind", "sha256", "size_bytes", "media_type", "publish_destinations"]) ||
        !DIGEST.test(artifact.sha256) || !Number.isInteger(artifact.size_bytes) || artifact.size_bytes <= 0 ||
        !Array.isArray(artifact.publish_destinations) || !artifact.publish_destinations.length) return false;
      if (artifact.publish_destinations.includes("pypi")) {
        const type = { "python-wheel": "bdist_wheel", "python-sdist": "sdist" }[artifact.kind];
        if (!type || files.filter((file) => file.filename === artifact.name && file.size === artifact.size_bytes &&
          file.packagetype === type && file.yanked === false && file.digests?.sha256 === artifact.sha256.slice(7)).length !== 1) return false;
      }
      if (artifact.publish_destinations.includes("github-release")) {
        const retained = staging.assets?.filter((asset) => asset.name === artifact.name);
        if (retained?.length !== 1) return false;
        if (metadata.assets.filter((asset) => String(asset.id) === retained[0].asset_id && asset.name === artifact.name &&
          asset.size === artifact.size_bytes && asset.digest === artifact.sha256 && asset.state === "uploaded" &&
          String(asset.uploader?.id) === retained[0].uploader_id && asset.uploader?.login === retained[0].uploader_login &&
          (!draftMode || asset.uploader.login === "openadapt-release[bot]")).length !== 1) return false;
      }
      if (artifact.publish_destinations.some((destination) => !["pypi", "github-release"].includes(destination))) return false;
    }
    if (!Array.isArray(staging.tag_rulesets) || staging.tag_rulesets.length !== 2) return false;
    const checks = await Promise.all(staging.tag_rulesets.map(async (retained) => {
      const ruleset = await fetchJson(fetchImpl, `${repo}/rulesets/${retained.ruleset_id}`, now);
      // GitHub hides bypass actors from anonymous readers. Those actors and the
      // immutable-releases setting remain authenticated issuance observations.
      return ruleset && String(ruleset.id) === retained.ruleset_id &&
        ["name", "target", "enforcement", "conditions", "rules"].every((key) => sameValue(ruleset[key], retained[key]));
    }));
    return checks.every(Boolean);
  }

  async function loadV2Verification(fetchImpl, now, projection) {
    const [document, head] = await Promise.all([
      fetchJson(fetchImpl, VERIFICATIONS_URL, now),
      fetchJson(fetchImpl, `${CANONICAL_API}/git/ref/heads/main`, now),
    ]);
    const commit = head?.object?.sha;
    if (!hasExactKeys(document, ["schema_version", "source_commit", "records"]) ||
      document.schema_version !== "openadapt.public-production-lifecycle-verifications/v1" ||
      document.source_commit !== projection.source.source_commit || !Array.isArray(document.records) || !HEX40.test(commit)) return null;
    const records = new Map();
    for (const record of document.records) {
      if (!TARGET_IDS.includes(record?.target) || records.has(record.target)) return null;
      records.set(record.target, record);
    }
    const registry = await fetchJson(fetchImpl, `${CANONICAL_RAW}/${commit}/evidence-registry.json`, now);
    return { records, registry, commit };
  }

  async function verifyTargetV2(active, verification, liveAdmissions, fetchImpl, now) {
    try {
      const record = verification?.records.get(active.targetId);
      if (!record) return false;
      const evidenceKeys = await verifyV2Receipt(active, record, liveAdmissions, fetchImpl, now);
      if (!evidenceKeys) return false;
      const [state, artifacts] = await Promise.all([
        currentV2State(record, fetchImpl, now, verification, evidenceKeys), verifyV2Artifacts(active, fetchImpl, now),
      ]);
      return state && artifacts;
    } catch (_error) { return false; }
  }

  function verifyDefaultInstallAuthority(activeTargets) {
    return Object.keys(PYPI_PROJECTS).every((targetId) => activeTargets.has(targetId));
  }

  async function load(fetchImpl, now = Date.now()) {
    try {
      const projectionRequestUrl = cacheBustedUrl(PROJECTION_URL, now);
      const admissionsRequestUrl = cacheBustedUrl(ADMISSIONS_URL, now);
      const [projectionResponse, admissionsResponse] = await Promise.all([
        fetchImpl(projectionRequestUrl, {
          cache: "no-store",
          credentials: "same-origin",
        }),
        fetchImpl(admissionsRequestUrl, { cache: "no-store", credentials: "omit" }),
      ]);
      if (!projectionResponse.ok || !admissionsResponse.ok) return null;
      const projection = await projectionResponse.json();
      const targets = validateProjection(projection);
      if (!targets) return null;
      const admissionsBytes = await admissionsResponse.arrayBuffer();
      const expectedDigest = projection.source.files.admissions.sha256;
      if ((await sha256(admissionsBytes)) !== expectedDigest) return null;
      const liveAdmissions = JSON.parse(new TextDecoder().decode(admissionsBytes));
      let policy = null;
      if (liveAdmissions.policy_sha256 !== projection.source.files.policy.sha256) {
        const policyItem = projection.source.files.policy;
        if (
          !isObject(policyItem) ||
          !isHttpsUrl(policyItem.url) ||
          !DIGEST.test(policyItem.sha256)
        ) {
          return null;
        }
        const policyBytes = await fetchBytes(fetchImpl, policyItem.url, now);
        if (!policyBytes || (await sha256(policyBytes)) !== policyItem.sha256) {
          return null;
        }
        policy = JSON.parse(new TextDecoder().decode(policyBytes));
        if (!isObject(policy) || typeof policy.admission_validity !== "string") {
          return null;
        }
      }
      if (!validateLiveAdmissions(liveAdmissions, projection, targets, policy)) {
        return null;
      }

      const candidates = new Map();
      for (const [targetId, target] of targets) {
        const active = deriveTarget(target, projection, now);
        if (active) candidates.set(targetId, active);
      }

      const verification = [...candidates.values()].some((active) => active.untilRevoked)
        ? await loadV2Verification(fetchImpl, now, projection).catch(() => null) : null;
      const authorityChecks = await Promise.all(
        [...candidates.entries()].map(async ([targetId, active]) => [
          targetId,
          active,
          active.untilRevoked === true
            ? await verifyTargetV2(active, verification, liveAdmissions, fetchImpl, now)
            : await verifyTargetAuthorities(active, fetchImpl, now),
        ]),
      );
      const activeTargets = new Map(
        authorityChecks
          .filter((entry) => entry[2] === true)
          .map(([targetId, active]) => [targetId, active]),
      );
      return Object.freeze({
        activeTargets,
        defaultInstallVerified: verifyDefaultInstallAuthority(activeTargets),
      });
    } catch (_error) {
      return null;
    }
  }

  function renderTarget(element, active) {
    element.textContent = "";
    if (!active) {
      element.textContent = TARGET_REQUIREMENT;
      return;
    }
    element.append("Production: ", active.releaseLabel, ". ");
    if (!isHttpsUrl(active.summaryUrl)) return;
    const link = element.ownerDocument.createElement("a");
    link.href = active.summaryUrl;
    link.rel = "noopener noreferrer";
    link.textContent = "acceptance evidence";
    element.append(link);
  }

  function render(document, state) {
    const active =
      state?.activeTargets instanceof Map ? state.activeTargets : new Map();
    for (const element of document.querySelectorAll("[data-openadapt-production-target]")) {
      renderTarget(element, active.get(element.dataset.openadaptProductionTarget));
    }
    const productIsProduction =
      state?.defaultInstallVerified === true &&
      TARGET_IDS.every((targetId) => active.has(targetId));
    for (const element of document.querySelectorAll("[data-openadapt-production-product]")) {
      element.textContent = productIsProduction ? "Production" : PRODUCT_REQUIREMENT;
    }
  }

  async function refreshWithLoader(document, loader) {
    refreshGeneration += 1;
    const generation = refreshGeneration;
    let state = null;
    try {
      state = await loader();
    } catch (_error) {
      state = null;
    }
    if (generation !== refreshGeneration) return false;
    render(document, state);
    return true;
  }

  async function refresh(document, fetchImpl, now = Date.now()) {
    return refreshWithLoader(document, () => load(fetchImpl, now));
  }

  return Object.freeze({
    ADMISSIONS_URL,
    PRODUCT_REQUIREMENT,
    PROJECTION_URL,
    PYPI_PROJECTS,
    TARGET_IDS,
    TARGET_REQUIREMENT,
    cacheBustedUrl,
    deriveTarget,
    load,
    refresh,
    refreshWithLoader,
    render,
    renderTarget,
    sha256,
    validateArtifact,
    validateLiveAdmissions,
    validateProjection,
    verifyArtifactAuthorities,
    verifyDefaultInstallAuthority,
    verifyEvidenceAuthority,
    verifyTargetAuthorities,
  });
});
