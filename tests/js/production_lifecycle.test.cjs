"use strict";

const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");
const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");
const test = require("node:test");

const lifecycle = require("../../docs/javascripts/production-lifecycle.js");

const NOW = Date.parse("2026-08-20T12:00:00Z");
const COMMIT = "c".repeat(40);
const TARGET_CONFIG = {
  agent: {
    claimScope: "qualified_agent_bridge_release",
    releaseKind: "public_package",
    sourceRepository: "OpenAdaptAI/openadapt-agent",
    project: "openadapt-agent",
    requiredKinds: ["sdist", "wheel"],
    authorities: { sdist: "pypi", wheel: "pypi" },
  },
  capture: {
    claimScope: "qualified_native_recorder_release",
    releaseKind: "public_package",
    sourceRepository: "OpenAdaptAI/openadapt-capture",
    project: "openadapt-capture",
    requiredKinds: ["sdist", "wheel"],
    authorities: { sdist: "pypi", wheel: "pypi" },
  },
  cloud: {
    claimScope: "qualified_workflow_control_plane_deployment",
    releaseKind: "private_deployment",
    sourceRepository: "OpenAdaptAI/openadapt-cloud",
    project: null,
    requiredKinds: [],
    authorities: {},
  },
  desktop: {
    claimScope: "qualified_native_workflow_desktop_release",
    releaseKind: "public_package",
    sourceRepository: "OpenAdaptAI/openadapt-desktop",
    project: "openadapt-desktop",
    requiredKinds: [
      "linux-installer",
      "macos-installer",
      "sdist",
      "wheel",
      "windows-installer",
    ],
    authorities: {
      "linux-installer": "github_release",
      "macos-installer": "github_release",
      sdist: "pypi",
      wheel: "pypi",
      "windows-installer": "github_release",
    },
  },
  docs: {
    claimScope: "production_documentation_deployment",
    releaseKind: "public_deployment",
    sourceRepository: "OpenAdaptAI/openadapt-ops",
    project: null,
    requiredKinds: ["deployment-manifest", "site-archive"],
    authorities: {
      "deployment-manifest": "managed_evidence",
      "site-archive": "managed_evidence",
    },
  },
  flow: {
    claimScope: "qualified_workflow_runtime_release",
    releaseKind: "public_package",
    sourceRepository: "OpenAdaptAI/openadapt-flow",
    project: "openadapt-flow",
    requiredKinds: ["sdist", "wheel"],
    authorities: { sdist: "pypi", wheel: "pypi" },
  },
  openadapt: {
    claimScope: "qualified_workflow_launcher_release",
    releaseKind: "public_package",
    sourceRepository: "OpenAdaptAI/OpenAdapt",
    project: "openadapt",
    requiredKinds: ["sdist", "wheel"],
    authorities: { sdist: "pypi", wheel: "pypi" },
  },
};

function digest(value) {
  return `sha256:${createHash("sha256").update(value).digest("hex")}`;
}

function jsonBytes(value) {
  return Buffer.from(JSON.stringify(value));
}

function artifact(targetId, kind, index) {
  const config = TARGET_CONFIG[targetId];
  const authority = config.authorities[kind];
  const packageName = config.project?.replaceAll("-", "_") ?? "openadapt";
  const nameByKind = {
    "deployment-manifest": "deployment-manifest.json",
    "linux-installer": "openadapt-desktop.AppImage",
    "macos-installer": "openadapt-desktop.dmg",
    sdist: `${packageName}-1.2.3.tar.gz`,
    "site-archive": "docs-site.tar.zst",
    wheel: `${packageName}-1.2.3-py3-none-any.whl`,
    "windows-installer": "openadapt-desktop.msi",
  };
  const sha256 = `sha256:${String(index).repeat(64)}`;
  let url;
  if (authority === "pypi") {
    url = `https://files.pythonhosted.org/packages/${sha256.slice(7)}/${nameByKind[kind]}`;
  } else if (authority === "github_release") {
    url = `https://api.github.com/repos/${config.sourceRepository}/releases/assets/${100 + index}`;
  } else {
    url = `https://evidence.openadapt.ai/objects/${sha256.slice(7)}/${nameByKind[kind]}`;
  }
  return {
    name: nameByKind[kind],
    kind,
    authority,
    url,
    sha256,
    size_bytes: 1000 + index,
  };
}

function release(targetId) {
  const config = TARGET_CONFIG[targetId];
  if (config.releaseKind === "private_deployment") {
    return {
      kind: "private_deployment",
      deployment_release_id: "cloud-123",
      deployment_release_sha256: `sha256:${"4".repeat(64)}`,
      manifest_sha256: `sha256:${"5".repeat(64)}`,
    };
  }
  const artifacts = config.requiredKinds.map((kind, index) =>
    artifact(targetId, kind, index + 1),
  );
  if (config.releaseKind === "public_deployment") {
    return {
      kind: "public_deployment",
      deployment_id: "docs-123",
      deployment_sha256: `sha256:${"6".repeat(64)}`,
      source_commit: COMMIT,
      immutable_release_url: `https://github.com/${config.sourceRepository}/commit/${COMMIT}`,
      artifacts,
    };
  }
  return {
    kind: "public_package",
    version: "1.2.3",
    tag: "v1.2.3",
    source_commit: COMMIT,
    immutable_release_url: `https://github.com/${config.sourceRepository}/commit/${COMMIT}`,
    artifacts,
  };
}

function authority(targetId) {
  const manifestUrl = `https://evidence.openadapt.ai/${targetId}/manifest.json`;
  const manifestBytes = jsonBytes({ target: targetId, retained: true });
  const summary = {
    schema_version: "openadapt.production-lifecycle-evidence-summary/v1",
    target: targetId,
    verdict: "accepted",
    claim_scope: TARGET_CONFIG[targetId].claimScope,
    evidence_manifest: {
      schema_version: "openadapt.production-acceptance/v1",
      url: manifestUrl,
      sha256: digest(manifestBytes),
    },
  };
  const summaryBytes = jsonBytes(summary);
  const bundleBytes = Buffer.from(`sigstore-bundle:${targetId}`);
  return {
    summaryUrl: `https://evidence.openadapt.ai/${targetId}/summary.json`,
    summaryBytes,
    bundleUrl: `https://evidence.openadapt.ai/${targetId}/summary.sigstore.json`,
    bundleBytes,
    manifestUrl,
    manifestBytes,
  };
}

function admission(targetId, sequence = 1, overrides = {}) {
  const config = TARGET_CONFIG[targetId];
  const evidence = authority(targetId);
  return {
    admission_id: `production:${targetId}:${sequence}`,
    target: targetId,
    claim_scope: config.claimScope,
    release_identity: {
      schema_version: "openadapt.monotonic-production-release/v1",
      channel: "production",
      sequence,
      previous_admission_sha256: null,
    },
    policy_revision: 1,
    release: release(targetId),
    acceptance_evidence: {
      summary_url: evidence.summaryUrl,
      summary_sha256: digest(evidence.summaryBytes),
      attestation_bundle_url: evidence.bundleUrl,
      attestation_bundle_sha256: digest(evidence.bundleBytes),
      authority_source_commit: "d".repeat(40),
    },
    issued_at: "2026-08-19T12:00:00Z",
    expires_at: "2026-09-18T12:00:00Z",
    revoked_at: null,
    ...overrides,
  };
}

function source(admissionsDigest) {
  const commit = "d".repeat(40);
  const base = `https://raw.githubusercontent.com/OpenAdaptAI/.github/${commit}/`;
  const paths = {
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
  };
  return {
    schema_version: "openadapt.production-lifecycle-source/v1",
    repository: "OpenAdaptAI/.github",
    source_commit: commit,
    files: Object.fromEntries(
      Object.entries(paths).map(([key, path]) => [
        key,
        {
          path,
          url: `${base}${path}`,
          sha256:
            key === "admissions"
              ? admissionsDigest
              : `sha256:${(key === "policy" ? "b" : "c").repeat(64)}`,
        },
      ]),
    ),
  };
}

function makeFixture(histories = {}) {
  const admissions = lifecycle.TARGET_IDS.flatMap(
    (targetId) => histories[targetId] ?? [admission(targetId)],
  );
  const live = {
    $schema: "schemas/production-lifecycle-admissions.schema.json",
    schema_version: "openadapt.production-lifecycle-admissions/v1",
    policy_sha256: `sha256:${"b".repeat(64)}`,
    admissions,
  };
  const bytes = jsonBytes(live);
  const projection = {
    $schema: "schemas/production-lifecycle-public.schema.json",
    schema_version: "openadapt.public-production-lifecycle/v1",
    source: source(digest(bytes)),
    policy_revision: 1,
    maximum_admission_days: 30,
    derivation: {
      mode: "latest_signed_admission_at_read_time",
      static_production_state: false,
      expired_or_revoked_latest_behavior: "no_production",
      fallback_to_older_release: false,
    },
    targets: lifecycle.TARGET_IDS.map((targetId) => {
      const history = [...(histories[targetId] ?? [admission(targetId)])].sort(
        (left, right) => left.release_identity.sequence - right.release_identity.sequence,
      );
      const config = TARGET_CONFIG[targetId];
      return {
        id: targetId,
        display_name: targetId,
        lifecycle_scope: targetId === "docs" ? "public_surface" : "repository",
        lifecycle_subject: targetId,
        source_repository: config.sourceRepository,
        required_claim_scope: config.claimScope,
        release_kind: config.releaseKind,
        required_artifact_kinds: config.requiredKinds,
        package_index_project: config.project,
        artifact_authority_by_kind: config.authorities,
        admission_history: history,
        latest_admission: history.at(-1) ?? null,
      };
    }),
  };
  return { bytes, live, projection };
}

function byteResponse(value) {
  return {
    ok: true,
    arrayBuffer: async () =>
      value.buffer.slice(value.byteOffset, value.byteOffset + value.byteLength),
  };
}

function targetForProject(project) {
  return Object.keys(TARGET_CONFIG).find(
    (targetId) => TARGET_CONFIG[targetId].project === project,
  );
}

function fetchFixture(fixture, options = {}) {
  return async (url) => {
    if (options.unavailable) return { ok: false };
    if (url.startsWith(`${lifecycle.PROJECTION_URL}?openadapt_lifecycle_request=`)) {
      return { ok: true, json: async () => structuredClone(fixture.projection) };
    }
    if (url.startsWith(`${lifecycle.ADMISSIONS_URL}?openadapt_lifecycle_request=`)) {
      return byteResponse(options.bytes ?? fixture.bytes);
    }

    const parsed = new URL(url);
    const cleanUrl = `${parsed.origin}${parsed.pathname}`;
    for (const targetId of lifecycle.TARGET_IDS) {
      const evidence = authority(targetId);
      const unavailablePart = options.evidenceUnavailable?.[targetId];
      if (cleanUrl === evidence.summaryUrl) {
        return unavailablePart === "summary" ? { ok: false } : byteResponse(evidence.summaryBytes);
      }
      if (cleanUrl === evidence.bundleUrl) {
        return unavailablePart === "bundle" ? { ok: false } : byteResponse(evidence.bundleBytes);
      }
      if (cleanUrl === evidence.manifestUrl) {
        return unavailablePart === "manifest"
          ? { ok: false }
          : byteResponse(evidence.manifestBytes);
      }
    }

    if (cleanUrl.startsWith("https://pypi.org/pypi/")) {
      const project = decodeURIComponent(parsed.pathname.split("/")[2]);
      const targetId = targetForProject(project);
      const admittedRelease = release(targetId);
      const version = options.pypiVersions?.[project] ?? admittedRelease.version;
      const files = admittedRelease.artifacts
        .filter((item) => item.authority === "pypi")
        .filter((item) => !options.pypiMissingArtifact?.includes(project))
        .map((item) => {
          const configured = options.pypiYankedValues?.[project];
          const yanked =
            configured ??
            (options.pypiYanked?.includes(project) ? true : false);
          const value = {
            filename: item.name,
            url: item.url,
            size: item.size_bytes,
            packagetype: item.kind === "wheel" ? "bdist_wheel" : "sdist",
            digests: { sha256: item.sha256.slice(7) },
            yanked,
          };
          if (options.pypiMissingYanked?.includes(project)) delete value.yanked;
          return value;
        });
      return {
        ok: !options.pypiUnavailable?.includes(project),
        json: async () => ({
          info: { version },
          releases: { [admittedRelease.version]: files },
        }),
      };
    }

    if (cleanUrl.startsWith("https://api.github.com/repos/")) {
      const admittedRelease = release("desktop");
      return {
        ok: options.githubUnavailable !== true,
        json: async () => ({
          tag_name: admittedRelease.tag,
          draft: false,
          prerelease: false,
          immutable: true,
          assets: options.githubMissingArtifact
            ? []
            : admittedRelease.artifacts
                .filter((item) => item.authority === "github_release")
                .map((item) => ({
                  name: item.name,
                  url: item.url,
                  size: item.size_bytes,
                  digest: item.sha256,
                  state: "uploaded",
                })),
        }),
      };
    }

    if (cleanUrl.startsWith("https://evidence.openadapt.ai/api/v1/objects/sha256/")) {
      const admittedRelease = release("docs");
      const digestValue = parsed.pathname.split("/").at(-1);
      const item = admittedRelease.artifacts.find(
        (candidate) => candidate.sha256 === `sha256:${digestValue}`,
      );
      if (!item || options.managedUnavailable === true) return { ok: false };
      return {
        ok: true,
        json: async () => ({
          schema_version: "openadapt.managed-artifact-head/v1",
          exists: options.managedMissing === true ? false : true,
          artifact_url: item.url,
          sha256: item.sha256,
          size_bytes: item.size_bytes,
          object_version_sha256: `sha256:${"e".repeat(64)}`,
          head_verified: true,
        }),
      };
    }

    return { ok: false };
  };
}

test("current digest-bound admissions with live authorities render Production", async () => {
  const fixture = makeFixture();
  const state = await lifecycle.load(fetchFixture(fixture), NOW);

  assert.ok(state.activeTargets instanceof Map);
  assert.equal(state.defaultInstallVerified, true);
  assert.deepEqual([...state.activeTargets.keys()].sort(), lifecycle.TARGET_IDS);
  assert.equal(state.activeTargets.get("flow").releaseLabel, "release 1.2.3");
  assert.equal(
    state.activeTargets.get("cloud").releaseLabel,
    "deployment release cloud-123",
  );
});

test("an expired latest admission does not retain Production", async () => {
  const expired = admission("flow", 1, { expires_at: "2026-08-20T11:59:59Z" });
  const fixture = makeFixture({ flow: [expired] });
  const state = await lifecycle.load(fetchFixture(fixture), NOW);

  assert.ok(state.activeTargets instanceof Map);
  assert.equal(state.activeTargets.has("flow"), false);
  assert.equal(state.defaultInstallVerified, false);
});

test("a revoked latest admission never falls back to an older active release", async () => {
  const old = admission("flow", 1);
  const revoked = admission("flow", 2, { revoked_at: "2026-08-20T11:00:00Z" });
  const fixture = makeFixture({ flow: [old, revoked] });
  const state = await lifecycle.load(fetchFixture(fixture), NOW);

  assert.ok(state.activeTargets instanceof Map);
  assert.equal(state.activeTargets.has("flow"), false);
});

test("a live-record digest mismatch fails closed", async () => {
  const fixture = makeFixture();
  const changed = Buffer.from(`${fixture.bytes.toString()}\n`);

  assert.equal(await lifecycle.load(fetchFixture(fixture, { bytes: changed }), NOW), null);
  assert.equal(await lifecycle.load(fetchFixture(fixture, { unavailable: true }), NOW), null);
});

test("a projection without the complete evidence-registry source fails closed", () => {
  for (const key of [
    "evidence_registry",
    "evidence_registry_schema",
    "evidence_registry_validator",
  ]) {
    const fixture = makeFixture();
    delete fixture.projection.source.files[key];
    assert.equal(lifecycle.validateProjection(fixture.projection), null, key);
  }
});

test("every live authority request is uncached", async () => {
  const fixture = makeFixture();
  const urls = [];
  const fetchImpl = fetchFixture(fixture);
  const recordingFetch = async (url, options) => {
    urls.push(url);
    assert.equal(options.cache, "no-store");
    return fetchImpl(url, options);
  };

  await lifecycle.load(recordingFetch, NOW);
  const firstRun = [...urls];
  await lifecycle.load(recordingFetch, NOW);
  const secondRun = urls.slice(firstRun.length);

  assert.equal(firstRun.length, secondRun.length);
  assert.ok(firstRun.length > 20);
  assert.notEqual(firstRun[0], secondRun[0]);
  assert.notEqual(firstRun[1], secondRun[1]);
  assert.match(firstRun[0], /^\/production-lifecycle\.json\?openadapt_lifecycle_request=/);
  assert.match(
    firstRun[1],
    /^https:\/\/raw\.githubusercontent\.com\/OpenAdaptAI\/\.github\/main\/production-lifecycle-admissions\.json\?openadapt_lifecycle_request=/,
  );
  assert.ok(firstRun.every((url) => url.includes("openadapt_lifecycle_request=")));
});

test("PyPI drift and yanks remove the affected target from Production", async () => {
  const fixture = makeFixture();
  const drifted = await lifecycle.load(
    fetchFixture(fixture, { pypiVersions: { "openadapt-flow": "1.2.4" } }),
    NOW,
  );
  assert.equal(drifted.activeTargets.has("flow"), false);
  assert.equal(drifted.activeTargets.size, 6);
  assert.equal(drifted.defaultInstallVerified, false);

  const yanked = await lifecycle.load(
    fetchFixture(fixture, { pypiYanked: ["openadapt-agent"] }),
    NOW,
  );
  assert.equal(yanked.activeTargets.has("agent"), false);
  assert.equal(yanked.activeTargets.size, 6);

  const malformed = await lifecycle.load(
    fetchFixture(fixture, {
      pypiYankedValues: { "openadapt-capture": "false" },
    }),
    NOW,
  );
  assert.equal(malformed.activeTargets.has("capture"), false);
});

test("a missing GitHub installer removes Desktop from Production", async () => {
  const fixture = makeFixture();
  const state = await lifecycle.load(
    fetchFixture(fixture, { githubMissingArtifact: true }),
    NOW,
  );

  assert.equal(state.activeTargets.has("desktop"), false);
  assert.equal(state.activeTargets.size, 6);
});

test("a managed-evidence outage removes Docs from Production", async () => {
  const fixture = makeFixture();
  const state = await lifecycle.load(
    fetchFixture(fixture, { managedUnavailable: true }),
    NOW,
  );

  assert.equal(state.activeTargets.has("docs"), false);
  assert.equal(state.activeTargets.size, 6);
});

test("an evidence authority outage removes the affected target from Production", async () => {
  const fixture = makeFixture();
  for (const part of ["summary", "bundle", "manifest"]) {
    const state = await lifecycle.load(
      fetchFixture(fixture, { evidenceUnavailable: { cloud: part } }),
      NOW,
    );
    assert.equal(state.activeTargets.has("cloud"), false, part);
    assert.equal(state.activeTargets.size, 6, part);
  }
});

test("an older delayed refresh cannot overwrite a newer negative state", async () => {
  const product = { textContent: "" };
  const document = {
    querySelectorAll(selector) {
      if (selector === "[data-openadapt-production-product]") return [product];
      return [];
    },
  };
  let resolveOlder;
  let resolveNewer;
  const olderState = new Promise((resolve) => {
    resolveOlder = resolve;
  });
  const newerState = new Promise((resolve) => {
    resolveNewer = resolve;
  });
  const activeTargets = new Map(lifecycle.TARGET_IDS.map((id) => [id, {}]));

  const olderRefresh = lifecycle.refreshWithLoader(document, () => olderState);
  const newerRefresh = lifecycle.refreshWithLoader(document, () => newerState);
  resolveNewer(null);
  assert.equal(await newerRefresh, true);
  assert.equal(product.textContent, lifecycle.PRODUCT_REQUIREMENT);

  resolveOlder({ activeTargets, defaultInstallVerified: true });
  assert.equal(await olderRefresh, false);
  assert.equal(product.textContent, lifecycle.PRODUCT_REQUIREMENT);
});

test("product-wide Production requires all seven verified targets", () => {
  const product = { textContent: "" };
  const document = {
    querySelectorAll(selector) {
      if (selector === "[data-openadapt-production-product]") return [product];
      return [];
    },
  };
  const six = new Map(lifecycle.TARGET_IDS.slice(0, 6).map((id) => [id, {}]));
  lifecycle.render(document, { activeTargets: six, defaultInstallVerified: false });
  assert.equal(product.textContent, lifecycle.PRODUCT_REQUIREMENT);

  const seven = new Map(lifecycle.TARGET_IDS.map((id) => [id, {}]));
  lifecycle.render(document, {
    activeTargets: seven,
    defaultInstallVerified: true,
  });
  assert.equal(product.textContent, "Production");
});

test("an inactive target uses the exact neutral lifecycle term", () => {
  const target = {
    textContent: "",
    append() {
      throw new Error("inactive targets must not append a Production label");
    },
  };
  lifecycle.renderTarget(target, null);
  assert.equal(target.textContent, lifecycle.TARGET_REQUIREMENT);
});

test("the ecosystem page uses the runtime target fallback label", () => {
  assert.equal(
    lifecycle.TARGET_REQUIREMENT,
    "No current verified Production admission.",
  );
  assert.equal(
    lifecycle.PRODUCT_REQUIREMENT,
    "Not currently Production across all seven targets.",
  );

  const ecosystem = readFileSync(
    resolve(__dirname, "../../docs/ecosystem/index.md"),
    "utf8",
  );
  const targetSpans = [
    ...ecosystem.matchAll(
      /<span\b[^>]*\bdata-openadapt-production-target="([^"]+)"[^>]*>([^<]+)<\/span>/g,
    ),
  ];
  assert.deepEqual(
    targetSpans.map((match) => match[1]).sort(),
    [...lifecycle.TARGET_IDS].sort(),
  );
  assert.ok(
    targetSpans.every((match) => match[2] === lifecycle.TARGET_REQUIREMENT),
  );

});

test("the committed admission-free projection keeps every label neutral", async () => {
  const committed = require("../../docs/production-lifecycle.json");
  const targets = lifecycle.validateProjection(committed);

  assert.ok(targets instanceof Map);
  for (const target of targets.values()) {
    assert.equal(lifecycle.deriveTarget(target, committed, NOW), null);
  }
});
