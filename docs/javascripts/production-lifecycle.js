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

  const TARGET_REQUIREMENT =
    "Production requires an active signed admission for this exact release or deployment.";
  const PRODUCT_REQUIREMENT =
    "Production requires active signed admissions for every required release and deployment, and execution accepts only active qualified workflow versions.";
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

  function deriveTarget(target, projection, now = Date.now()) {
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
    if (releaseKind === "public_package" && VERSION.test(release.version)) {
      releaseLabel = `release ${release.version}`;
    } else if (
      releaseKind === "public_deployment" &&
      typeof release.deployment_id === "string" &&
      release.deployment_id.length > 0
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

  async function verifyDefaultInstallAuthority(activeTargets, fetchImpl, now) {
    try {
      const checks = await Promise.all(
        Object.entries(PYPI_PROJECTS).map(async ([targetId, project]) => {
          const active = activeTargets.get(targetId);
          if (!active || typeof active.releaseVersion !== "string") return false;
          const url = cacheBustedUrl(
            `https://pypi.org/pypi/${project}/json`,
            now,
          );
          const response = await fetchImpl(url, {
            cache: "no-store",
            credentials: "omit",
          });
          if (!response.ok) return false;
          const metadata = await response.json();
          if (
            !isObject(metadata) ||
            !isObject(metadata.info) ||
            metadata.info.version !== active.releaseVersion ||
            !isObject(metadata.releases)
          ) {
            return false;
          }
          const files = metadata.releases[active.releaseVersion];
          if (!Array.isArray(files)) return false;
          const unyankedKinds = new Set(
            files
              .filter((file) => isObject(file) && file.yanked === false)
              .map((file) => file.packagetype),
          );
          return unyankedKinds.has("bdist_wheel") && unyankedKinds.has("sdist");
        }),
      );
      return checks.every(Boolean);
    } catch (_error) {
      return false;
    }
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

      const activeTargets = new Map();
      for (const [targetId, target] of targets) {
        const active = deriveTarget(target, projection, now);
        if (active) activeTargets.set(targetId, active);
      }
      return Object.freeze({
        activeTargets,
        defaultInstallVerified: await verifyDefaultInstallAuthority(
          activeTargets,
          fetchImpl,
          now,
        ),
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
    element.append("Production — ", active.releaseLabel, " — ");
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
    validateLiveAdmissions,
    validateProjection,
    verifyDefaultInstallAuthority,
  });
});
