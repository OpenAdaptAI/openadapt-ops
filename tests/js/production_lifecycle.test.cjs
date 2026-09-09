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

test("the committed ledger is not yet active before issued_at", () => {
  const committed = require("../../docs/production-lifecycle.json");
  const targets = lifecycle.validateProjection(committed);

  assert.ok(targets instanceof Map);
  for (const target of targets.values()) {
    assert.equal(lifecycle.deriveTarget(target, committed, NOW), null);
  }
});

test("the committed ledger retains seven until-revoked candidates for current verification", () => {
  const committed = require("../../docs/production-lifecycle.json");
  const targets = lifecycle.validateProjection(committed);
  const afterIssue = Date.parse("2026-09-02T20:00:00Z");
  const afterThirtyDays = Date.parse("2026-12-01T00:00:00Z");
  const expectedVersion = {
    agent: "2.0.1",
    capture: "1.2.2",
    desktop: "0.16.0",
    flow: "1.34.0",
    openadapt: "1.16.0",
  };

  assert.ok(targets instanceof Map);
  assert.equal(targets.size, 7);
  for (const [id, target] of targets) {
    assert.equal(target.latest_admission.expires_at, null);
    assert.equal(target.latest_admission.verdict, "accepted");
    const derived = lifecycle.deriveTarget(target, committed, afterIssue);
    assert.ok(derived, `${id} should derive an until-revoked admission`);
    assert.ok(
      lifecycle.deriveTarget(target, committed, afterThirtyDays),
      `${id} remains a candidate past the retained 30-day v1 window`,
    );
    if (expectedVersion[id]) {
      assert.equal(derived.releaseVersion, expectedVersion[id]);
    } else {
      assert.equal(target.latest_admission.release.kind, "deployment");
    }
  }
});

test("a timestamped v2 expiry is not until-revoked", () => {
  const committed = require("../../docs/production-lifecycle.json");
  const target = structuredClone(
    committed.targets.find((candidate) => candidate.id === "flow"),
  );
  const now = Date.parse("2026-09-03T12:00:00Z");

  assert.ok(lifecycle.deriveTarget(target, committed, now));
  target.latest_admission.expires_at = "2026-09-09T18:24:25Z";
  assert.equal(lifecycle.deriveTarget(target, committed, now), null);
});

const V2_SPEC = {
  agent: { claimScope: "production_agent", releaseKind: "package" },
  capture: { claimScope: "production_capture", releaseKind: "package" },
  cloud: { claimScope: "production_cloud", releaseKind: "deployment" },
  desktop: { claimScope: "production_desktop", releaseKind: "package" },
  docs: { claimScope: "production_docs", releaseKind: "deployment" },
  flow: { claimScope: "production_flow", releaseKind: "package" },
  openadapt: { claimScope: "production_openadapt", releaseKind: "package" },
};

function v2Admission(targetId, overrides = {}) {
  const spec = V2_SPEC[targetId];
  const release =
    spec.releaseKind === "package"
      ? { kind: "package", version: "1.2.3" }
      : { kind: "deployment", deployment_id: `${targetId}-deploy` };
  return {
    target: targetId,
    claim_scope: spec.claimScope,
    verdict: "accepted",
    expires_at: null,
    revoked_at: null,
    evidence_class: "remote-safe-synthetic",
    issued_at: "2026-09-02T18:24:25Z",
    release_identity: {
      schema_version: "openadapt.monotonic-production-release/v1",
      channel: "production",
      sequence: 1,
      previous_admission_sha256: null,
    },
    release,
    ...overrides,
  };
}

function objectRef(index) {
  return {
    schema_version: "openadapt.production-evidence-object-reference/v2",
    kind: "qualification-release",
    object_path: `production-evidence/objects/sha256/${index}/obj.qualification-release.json`,
  };
}

function makeUntilRevokedFixture(overrides = {}) {
  const histories = Object.fromEntries(
    lifecycle.TARGET_IDS.map((id) => [id, [v2Admission(id, overrides.admissions?.[id])]]),
  );
  const fixture = makeFixture(histories);
  const policy = {
    admission_validity: overrides.admissionValidity ?? "until_revoked",
  };
  const policyBytes = jsonBytes(policy);
  const live = {
    $schema: "schemas/production-lifecycle-admissions.schema.json",
    schema_version: "openadapt.production-lifecycle-admissions/v1",
    policy_sha256: overrides.issuedPolicySha256 ?? `sha256:${"a".repeat(64)}`,
    admissions: overrides.liveAdmissions ?? lifecycle.TARGET_IDS.map((_, index) => objectRef(index)),
  };
  const bytes = jsonBytes(live);
  fixture.live = live;
  fixture.bytes = bytes;
  fixture.policyBytes = policyBytes;
  fixture.projection.source.files.admissions.sha256 = digest(bytes);
  fixture.projection.source.files.policy.sha256 = digest(policyBytes);
  return fixture;
}

function fetchUntilRevoked(fixture, options = {}) {
  return async (url) => {
    if (options.unavailable) return { ok: false };
    if (url.startsWith(`${lifecycle.PROJECTION_URL}?openadapt_lifecycle_request=`)) {
      return { ok: true, json: async () => structuredClone(fixture.projection) };
    }
    if (url.startsWith(`${lifecycle.ADMISSIONS_URL}?openadapt_lifecycle_request=`)) {
      return byteResponse(options.bytes ?? fixture.bytes);
    }
    const policyUrl = fixture.projection.source.files.policy.url;
    if (url === policyUrl || url.startsWith(`${policyUrl}?`)) {
      if (options.policyUnavailable) return { ok: false };
      return byteResponse(options.policyBytes ?? fixture.policyBytes);
    }
    return { ok: false };
  };
}

const AFTER_ISSUE = Date.parse("2026-09-02T20:00:00Z");

test("until-revoked rows without verification cannot bypass current authority checks", async () => {
  const fixture = makeUntilRevokedFixture();
  const state = await lifecycle.load(fetchUntilRevoked(fixture), AFTER_ISSUE);

  assert.ok(state?.activeTargets instanceof Map);
  assert.equal(state.activeTargets.size, 0);
  assert.equal(state.defaultInstallVerified, false);
});

test("until-revoked policy mismatch fails closed without a parseable policy", async () => {
  const fixture = makeUntilRevokedFixture();
  assert.equal(
    await lifecycle.load(
      fetchUntilRevoked(fixture, { policyUnavailable: true }),
      AFTER_ISSUE,
    ),
    null,
  );

  const unparseable = Buffer.from("not-json");
  fixture.projection.source.files.policy.sha256 = digest(unparseable);
  assert.equal(
    await lifecycle.load(
      fetchUntilRevoked(fixture, { policyBytes: unparseable }),
      AFTER_ISSUE,
    ),
    null,
  );

  const bounded = makeUntilRevokedFixture({ admissionValidity: "bounded" });
  assert.equal(await lifecycle.load(fetchUntilRevoked(bounded), AFTER_ISSUE), null);
});

test("until-revoked mismatch fails closed on expiry, revocation, or identity drift", async () => {
  const expired = makeUntilRevokedFixture({
    admissions: { flow: { expires_at: "2026-09-09T18:24:25Z" } },
  });
  assert.equal(await lifecycle.load(fetchUntilRevoked(expired), AFTER_ISSUE), null);

  const revoked = makeUntilRevokedFixture({
    admissions: { flow: { revoked_at: "2026-09-02T19:00:00Z" } },
  });
  assert.equal(await lifecycle.load(fetchUntilRevoked(revoked), AFTER_ISSUE), null);

  const drifted = makeUntilRevokedFixture({
    admissions: { flow: { claim_scope: "production_openadapt" } },
  });
  const driftedState = await lifecycle.load(fetchUntilRevoked(drifted), AFTER_ISSUE);
  assert.equal(driftedState.activeTargets.has("flow"), false);
  assert.equal(driftedState.activeTargets.size, 0);
  assert.equal(driftedState.defaultInstallVerified, false);
});

test("object-ref rows are not product targets and unknown rows fail closed", async () => {
  const fixture = makeUntilRevokedFixture({
    liveAdmissions: [
      ...lifecycle.TARGET_IDS.map((_, index) => objectRef(index)),
      { kind: "not-a-target", object_path: "nope.json" },
    ],
  });
  assert.equal(await lifecycle.load(fetchUntilRevoked(fixture), AFTER_ISSUE), null);

  const valid = makeUntilRevokedFixture();
  assert.equal(
    lifecycle.validateLiveAdmissions(
      valid.live,
      valid.projection,
      lifecycle.validateProjection(valid.projection),
      { admission_validity: "until_revoked" },
    ),
    true,
  );
});

function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map(
    (key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}

function makeVerifiedV2Fixture({ stateExpiry = null, signerExpiry = null, draftMode = false, stateNotBefore = "2026-09-02T18:24:25Z", keyRevokedAt = null, mismatchedState = false, bundleExpiryKind = null, bundleStartKind = null, evidenceKeyRevokedAt = null } = {}) {
  const fixture = makeUntilRevokedFixture();
  const responses = new Map();
  const commit = fixture.projection.source.source_commit;
  const base = `https://raw.githubusercontent.com/OpenAdaptAI/.github/${commit}`;
  const raw = (url, value) => responses.set(url, Buffer.from(`${canonicalJson(value)}\n`));
  const object = (kind, value, subject = null) => {
    const bytes = Buffer.from(`${canonicalJson(value)}\n`);
    const sha = digest(bytes);
    const ref = {
      schema_version: "openadapt.production-evidence-object-reference/v2",
      repository: "OpenAdaptAI/.github", repository_id: "1", repository_owner_id: "2",
      registry_source_commit: commit, registry_revision: 1, registry_head_sha256: `sha256:${"a".repeat(64)}`,
      kind, object_schema_version: value.schema_version ?? "fixture/v1",
      object_path: `production-evidence/objects/sha256/${sha.slice(7, 9)}/${sha.slice(7)}.${kind}.json`,
      object_sha256: sha, size_bytes: bytes.length, object_media_type: "application/json",
      semantic_identity_sha256: value.authority_state_sha256 && kind === "qualification-authority-state-receipt" ? value.authority_state_sha256 :
        (kind === "qualification-revocation-state-receipt" ? value.revocation_state_sha256 : sha), subject_sha256: subject, registry_entry_sha256: sha,
    };
    responses.set(`${base}/${ref.object_path}`, bytes);
    return ref;
  };
  const pair = (kind, value) => {
    const ref = object(kind, value);
    const key = evidenceKeyRevokedAt && !["qualification-authority-state-receipt", "qualification-revocation-state-receipt"].includes(kind)
      ? "evidence-key" : "fixture-key";
    const statement = { schema_version: "openadapt.production-public-trust-signing-statement/v1", key_id: key,
      object_kind: kind, object_sha256: ref.object_sha256, object_size_bytes: ref.size_bytes,
      semantic_identity_sha256: ref.semantic_identity_sha256,
      not_before: kind === bundleStartKind ? "2026-09-02T19:30:00Z" : "2026-09-02T18:24:25Z",
      expires_at: kind === bundleExpiryKind ? "2026-09-02T19:30:00Z" : null };
    return [ref, object(`${kind}-sigstore-bundle`, { dsseEnvelope: { payload: Buffer.from(canonicalJson(statement)).toString("base64"),
      signatures: [{ keyid: key, sig: "synthetic" }] } }, ref.object_sha256)];
  };
  const signer = { generated_at: "2026-09-02T18:24:25Z", expires_at: signerExpiry, revision: 1,
    signers: [{ key_id: "fixture-key", status: "active", revoked_at: keyRevokedAt }] };
  if (evidenceKeyRevokedAt) signer.signers.push({ key_id: "evidence-key", status: "active", revoked_at: evidenceKeyRevokedAt });
  const signerBytes = Buffer.from(`${canonicalJson(signer)}\n`);
  const signerHash = digest(signerBytes);
  const signerIdentity = digest(`OpenAdapt qualification signer registry v2\0${canonicalJson(signer)}`);
  const pointer = { object_sha256: signerHash, registry_identity_sha256: signerIdentity, registry_revision: 1,
    object_path: `production-evidence/signer-registries/sha256/${signerHash.slice(7, 9)}/${signerHash.slice(7)}.qualification-signer-registry.json` };
  responses.set(`${base}/${pointer.object_path}`, signerBytes);
  const authority = { status: "active", not_before: stateNotBefore, expires_at: stateExpiry, issuer_key_id: "fixture-key" };
  const revocation = { status: "current", not_before: stateNotBefore, expires_at: stateExpiry, issuer_key_id: "fixture-key", revocations: [] };
  const authorityIdentity = `sha256:${"2".repeat(64)}`;
  const revocationIdentity = `sha256:${"3".repeat(64)}`;
  Object.assign(authority, { authority_state_sha256: authorityIdentity, signer_registry_sha256: signerHash,
    signer_registry_identity_sha256: signerIdentity, signer_registry_revision: 1 });
  Object.assign(revocation, { revocation_state_sha256: revocationIdentity, authority_state_sha256: authorityIdentity,
    signer_registry_sha256: signerIdentity });
  if (mismatchedState) revocation.authority_state_sha256 = `sha256:${"9".repeat(64)}`;
  const [authorityRef, authorityBundle] = pair("qualification-authority-state-receipt", authority);
  const [revocationRef, revocationBundle] = pair("qualification-revocation-state-receipt", revocation);
  authorityRef.semantic_identity_sha256 = authorityIdentity;
  revocationRef.semantic_identity_sha256 = revocationIdentity;
  const registry = { repository: "OpenAdaptAI/.github", entries: [], signer_registry: pointer };
  const entry = (ref) => Object.fromEntries(["kind", "object_schema_version", "object_path", "object_sha256", "size_bytes", "object_media_type",
    "semantic_identity_sha256", "subject_sha256", "registry_entry_sha256"].map((key) => [key, ref[key]]));
  registry.entries.push(...[authorityRef, authorityBundle, revocationRef, revocationBundle].map(entry));
  const records = [];
  const references = [];
  for (const id of lifecycle.TARGET_IDS.filter((id) => V2_SPEC[id].releaseKind === "package")) {
    const target = fixture.projection.targets.find((item) => item.id === id);
    const a = target.latest_admission;
    const repository = target.source_repository;
    const api = `https://api.github.com/repos/${repository}`;
    const sha = `sha256:${"1".repeat(64)}`;
    const artifact = { name: `${id}-1.2.3-py3-none-any.whl`, kind: "python-wheel", sha256: sha, size_bytes: 12,
      media_type: "application/zip", publish_destinations: ["github-release", "pypi"] };
    a.schema_version = "openadapt.qualification-release/v2";
    a.not_before = "2026-09-02T18:24:25Z";
    for (const key of ["admission_id_sha256", "release_sha256", "artifact_inventory_sha256", "publication_staging_sha256",
      "authority_state_sha256", "revocation_state_sha256", "signer_registry_sha256"]) a[key] = sha;
    a.authority_state_sha256 = authorityIdentity;
    a.revocation_state_sha256 = revocationIdentity;
    a.signer_registry_sha256 = signerIdentity;
    a.release = { kind: "package", version: "1.2.3", tag: "v1.2.3", source_repository: repository,
      source_repository_id: "3", source_commit: COMMIT, artifacts: [artifact], deployment_id: null, deployment_sha256: null };
    const [manifestRef, manifestBundle] = pair("production-acceptance-manifest", { target: id });
    const [decisionRef, decisionBundle] = pair("qualification-evidence-decision-receipt", { target: id, issuer_key_id: "fixture-key" });
    const [qualificationRef, qualificationBundle] = pair("qualification-admission", { target: id, admission_id_sha256: sha,
      workflow_version_id_sha256: sha, bundle_sha256: sha, admitted_runtime_sha256: sha });
    const [summaryRef, summaryBundle] = pair("production-acceptance-summary", {
      target: id, production_acceptance_manifest_reference: manifestRef, production_acceptance_manifest_bundle_reference: manifestBundle,
      qualification_evidence_decision_receipt_reference: decisionRef, qualification_evidence_decision_receipt_bundle_reference: decisionBundle,
      qualification_admission_reference: qualificationRef, qualification_admission_bundle_reference: qualificationBundle,
    });
    a.production_acceptance_summary_reference = summaryRef;
    a.production_acceptance_summary_bundle_reference = summaryBundle;
    a.publication_staging = { publication_mode: draftMode ? "draft-before-tag" : "already-published-pypi", draft_release_id: "42",
      release_author_login: draftMode ? "openadapt-release[bot]" : "prior-author", release_app_bot_user_id: "100",
      assets: [{ ...artifact, asset_id: "43", uploader_id: "100", uploader_login: draftMode ? "openadapt-release[bot]" : "prior-author" }],
      tag_rulesets: [{ ruleset_id: "10", name: "creation", target: "tag", enforcement: "active", conditions: {}, rules: [{ type: "creation" }] },
        { ruleset_id: "11", name: "immutable", target: "tag", enforcement: "active", conditions: {}, rules: [{ type: "update" }] }] };
    target.admission_history = [a];
    const [ref, bundleRef] = pair("qualification-release", a);
    references.push(ref);
    registry.entries.push(entry(ref), entry(bundleRef));
    const receipt = {
      schema_version: `openadapt.qualification-release-verification-receipt/v${id === "flow" ? 1 : 2}`,
      verification_id_sha256: sha, verdict: "verified", evidence_class: a.evidence_class, target: id, claim_scope: a.claim_scope,
      admission_object_sha256: ref.object_sha256, admission_bundle_object_sha256: bundleRef.object_sha256,
      ...Object.fromEntries(["admission_id_sha256", "release_sha256", "artifact_inventory_sha256", "release_identity", "publication_staging_sha256",
        "authority_state_sha256", "revocation_state_sha256", "signer_registry_sha256"].map((key) => [key, a[key]])),
      ...Object.fromEntries(["source_repository", "source_repository_id", "source_commit", "version", "tag"].map((key) => [key, a.release[key]])),
      draft_release_id: "42", acceptance_summary_object_sha256: summaryRef.object_sha256, acceptance_manifest_object_sha256: manifestRef.object_sha256,
      decision_receipt_object_sha256: decisionRef.object_sha256, qualification_admission_object_sha256: qualificationRef.object_sha256, qualification_admission_id_sha256: sha,
      workflow_version_id_sha256: sha, workflow_bundle_sha256: sha, admitted_runtime_sha256: sha,
      verified_at: "2026-09-02T19:00:00Z", expires_at: null, registry_source_commit: commit, registry_revision: 1,
      registry_head_sha256: ref.registry_head_sha256, trust_state_source_commit: commit,
      ...(id === "flow" ? {} : { release_kind: "package", deployment_id: null, deployment_sha256: null }),
    };
    const projection = { ...receipt }; delete projection.verification_id_sha256;
    receipt.verification_id_sha256 = digest(`OpenAdapt qualification release verification receipt v${id === "flow" ? 1 : 2}\0${canonicalJson(projection)}`);
    records.push({ schema_version: "openadapt.public-production-lifecycle-verification/v1", target: id, admission_reference: ref,
      admission_bundle_reference: bundleRef, verification_receipt: receipt,
      current_state: { authority_reference: authorityRef, authority_bundle_reference: authorityBundle, revocation_reference: revocationRef,
        revocation_bundle_reference: revocationBundle, signer_registry_pointer: pointer } });
    raw(`${api}/releases/42`, { id: 42, tag_name: "v1.2.3", draft: false, prerelease: false, immutable: draftMode,
      author: { login: a.publication_staging.release_author_login, id: 100 }, assets: [{ id: 43, name: artifact.name, size: 12,
        digest: sha, state: "uploaded", uploader: { id: 100, login: a.publication_staging.assets[0].uploader_login } }] });
    raw(`${api}/git/ref/tags/v1.2.3`, { ref: "refs/tags/v1.2.3", object: { type: "tag", sha: "e".repeat(40) } });
    raw(`${api}/git/tags/${"e".repeat(40)}`, { sha: "e".repeat(40), object: { type: "commit", sha: COMMIT } });
    raw(`https://pypi.org/pypi/${target.package_index_project}/json`, { info: { version: "1.2.3" }, releases: { "1.2.3": [{
      filename: artifact.name, size: 12, packagetype: "bdist_wheel", yanked: false, digests: { sha256: sha.slice(7) },
    }] } });
    for (const rule of a.publication_staging.tag_rulesets) raw(`${api}/rulesets/${rule.ruleset_id}`, { ...rule, id: Number(rule.ruleset_id) });
  }
  fixture.live.admissions = references;
  fixture.bytes = jsonBytes(fixture.live);
  fixture.projection.source.files.admissions.sha256 = digest(fixture.bytes);
  const document = { schema_version: "openadapt.public-production-lifecycle-verifications/v1", source_commit: commit, records };
  const refresh = () => {
    raw("/production-lifecycle-verifications.json", document);
    raw(`${base}/evidence-registry.json`, registry);
  };
  refresh();
  raw("https://api.github.com/repos/OpenAdaptAI/.github/git/ref/heads/main", { object: { sha: commit } });
  const baseFetch = fetchUntilRevoked(fixture);
  const fetch = async (url, options) => {
    const bytes = responses.get(url.split("?")[0]);
    return bytes ? { ...byteResponse(bytes), json: async () => JSON.parse(bytes) } : baseFetch(url, options);
  };
  const mutate = (url, change) => { const value = JSON.parse(responses.get(url)); change(value); raw(url, value); };
  return { ...fixture, fetch, responses, registry, document, raw, mutate, refresh, base };
}

test("V2 packages require verified records and live authority/artifact checks, including mutable already-published releases", async () => {
  const fixture = makeVerifiedV2Fixture();
  const state = await lifecycle.load(fixture.fetch, AFTER_ISSUE);
  assert.equal(state.activeTargets.size, 5);
  assert.equal(state.activeTargets.get("flow").releaseVersion, "1.2.3");
  assert.equal(state.defaultInstallVerified, true);
  assert.equal(state.activeTargets.has("cloud"), false);
  fixture.document.records = fixture.document.records.filter((record) => record.target !== "flow"); fixture.refresh();
  const missing = await lifecycle.load(fixture.fetch, AFTER_ISSUE);
  assert.equal(missing.activeTargets.has("flow"), false);
  assert.equal(missing.defaultInstallVerified, false);
});

test("unchanged admission ledger cannot hide changed current trust references", async () => {
  for (const kind of ["qualification-authority-state-receipt", "qualification-revocation-state-receipt", "signer_registry"]) {
    const fixture = makeVerifiedV2Fixture();
    if (kind === "signer_registry") fixture.registry.signer_registry = { ...fixture.registry.signer_registry, registry_revision: 2 };
    else fixture.registry.entries.push({ ...fixture.registry.entries.find((entry) => entry.kind === kind), object_sha256: `sha256:${"9".repeat(64)}` });
    fixture.refresh();
    assert.equal((await lifecycle.load(fixture.fetch, AFTER_ISSUE)).activeTargets.size, 0, kind);
  }
  const unrelated = makeVerifiedV2Fixture();
  unrelated.registry.entries.push({ kind: "unrelated-object", object_sha256: "irrelevant" }); unrelated.refresh();
  assert.equal((await lifecycle.load(unrelated.fetch, AFTER_ISSUE)).activeTargets.size, 5);
});

test("exact verified state bytes still expire at consumption time", async () => {
  for (const option of ["stateExpiry", "signerExpiry"]) {
    const fixture = makeVerifiedV2Fixture({ [option]: "2026-09-02T19:30:00Z" });
    assert.equal((await lifecycle.load(fixture.fetch, AFTER_ISSUE)).activeTargets.size, 0, option);
  }
});

test("V2 public controls fail closed without substituting historical release observations", async () => {
  const repo = "https://api.github.com/repos/OpenAdaptAI/openadapt-flow";
  for (const [url, change] of [
    ["https://pypi.org/pypi/openadapt-flow/json", (v) => { v.info.version = "1.2.4"; }],
    ["https://pypi.org/pypi/openadapt-flow/json", (v) => { v.releases["1.2.3"][0].yanked = true; }],
    ["https://pypi.org/pypi/openadapt-flow/json", (v) => { v.releases["1.2.3"][0].size += 1; }],
    [`${repo}/releases/42`, (v) => { v.assets[0].digest = `sha256:${"9".repeat(64)}`; }],
    [`${repo}/releases/42`, (v) => { v.assets[0].id += 1; }],
    [`${repo}/releases/42`, (v) => { v.assets = []; }],
    [`${repo}/git/tags/${"e".repeat(40)}`, (v) => { v.object.sha = "f".repeat(40); }],
    [`${repo}/rulesets/11`, (v) => { v.enforcement = "disabled"; }],
  ]) {
    const fixture = makeVerifiedV2Fixture(); fixture.mutate(url, change);
    const state = await lifecycle.load(fixture.fetch, AFTER_ISSUE);
    assert.equal(state.activeTargets.has("flow"), false, url);
    assert.equal(state.defaultInstallVerified, false, url);
  }
  const unavailable = makeVerifiedV2Fixture(); unavailable.responses.delete(`${repo}/rulesets/11`);
  assert.equal((await lifecycle.load(unavailable.fetch, AFTER_ISSUE)).activeTargets.has("flow"), false);
});

test("draft-before-tag keeps the stronger post-publication immutability requirement", async () => {
  const fixture = makeVerifiedV2Fixture({ draftMode: true });
  assert.equal((await lifecycle.load(fixture.fetch, AFTER_ISSUE)).activeTargets.has("flow"), true);
  fixture.mutate("https://api.github.com/repos/OpenAdaptAI/openadapt-flow/releases/42", (v) => { v.immutable = false; });
  assert.equal((await lifecycle.load(fixture.fetch, AFTER_ISSUE)).activeTargets.has("flow"), false);
});

test("a stale or forged generated result cannot admit a different latest object", async () => {
  for (const change of [
    (f) => { f.document.source_commit = "e".repeat(40); },
    (f) => { f.document.records.find((r) => r.target === "flow").verification_receipt.version = "1.2.4"; },
    (f) => { f.document.records.find((r) => r.target === "flow").admission_bundle_reference.object_sha256 = `sha256:${"9".repeat(64)}`; },
  ]) {
    const fixture = makeVerifiedV2Fixture(); change(fixture); fixture.refresh();
    assert.equal((await lifecycle.load(fixture.fetch, AFTER_ISSUE)).activeTargets.has("flow"), false);
  }
});


test("current state with future activation or an effective key revocation refuses", async () => {
  for (const options of [{ stateNotBefore: "2026-09-03T00:00:00Z" }, { keyRevokedAt: "2026-09-02T19:30:00Z" }]) {
    const fixture = makeVerifiedV2Fixture(options);
    assert.equal((await lifecycle.load(fixture.fetch, AFTER_ISSUE)).activeTargets.size, 0);
  }
});


test("jointly rehashed current objects must still match the admitted trust identities", async () => {
  const fixture = makeVerifiedV2Fixture({ mismatchedState: true });
  const state = await lifecycle.load(fixture.fetch, AFTER_ISSUE);
  assert.equal(state.activeTargets.size, 0);
});


test("every exact dependency statement keeps its independent validity window", async () => {
  for (const kind of ["qualification-release", "production-acceptance-summary", "production-acceptance-manifest",
    "qualification-evidence-decision-receipt", "qualification-admission"]) {
    const fixture = makeVerifiedV2Fixture({ bundleExpiryKind: kind });
    const before = await lifecycle.load(fixture.fetch, Date.parse("2026-09-02T19:15:00Z"));
    assert.equal(before.activeTargets.has("flow"), true, kind);
    const after = await lifecycle.load(fixture.fetch, AFTER_ISSUE);
    assert.equal(after.activeTargets.has("flow"), false, kind);
    const future = makeVerifiedV2Fixture({ bundleStartKind: kind });
    assert.equal((await lifecycle.load(future.fetch, Date.parse("2026-09-02T19:15:00Z"))).activeTargets.has("flow"), false, kind);
  }
});


test("the current signer check includes keys used only by dependent evidence", async () => {
  const fixture = makeVerifiedV2Fixture({ evidenceKeyRevokedAt: "2026-09-02T19:30:00Z" });
  assert.equal((await lifecycle.load(fixture.fetch, Date.parse("2026-09-02T19:15:00Z"))).activeTargets.has("flow"), true);
  assert.equal((await lifecycle.load(fixture.fetch, AFTER_ISSUE)).activeTargets.has("flow"), false);
});
