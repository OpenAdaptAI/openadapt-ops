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

  function validateLiveAdmissions(value, projection, targets) {
    if (
      !hasExactKeys(value, ["$schema", "schema_version", "policy_sha256", "admissions"]) ||
      value.$schema !== "schemas/production-lifecycle-admissions.schema.json" ||
      value.schema_version !== "openadapt.production-lifecycle-admissions/v1" ||
      value.policy_sha256 !== projection.source.files.policy.sha256 ||
      !Array.isArray(value.admissions)
    ) {
      return false;
    }
    const byTarget = new Map(TARGET_IDS.map((id) => [id, []]));
    for (const admission of value.admissions) {
      if (!isObject(admission) || !byTarget.has(admission.target)) return false;
      byTarget.get(admission.target).push(admission);
    }
    for (const targetId of TARGET_IDS) {
      const live = byTarget
        .get(targetId)
        .sort((left, right) => left?.release_identity?.sequence - right?.release_identity?.sequence);
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
      typeof admission.evidence_class !== "string" ||
      admission.evidence_class.length === 0 ||
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
      if (!validateLiveAdmissions(liveAdmissions, projection, targets)) return null;

      const candidates = new Map();
      for (const [targetId, target] of targets) {
        const active = deriveTarget(target, projection, now);
        if (active) candidates.set(targetId, active);
      }

      const authorityChecks = await Promise.all(
        [...candidates.entries()].map(async ([targetId, active]) => [
          targetId,
          active,
          await verifyTargetAuthorities(active, fetchImpl, now),
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
