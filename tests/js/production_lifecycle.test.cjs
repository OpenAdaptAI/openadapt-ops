"use strict";

const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");
const test = require("node:test");

const lifecycle = require("../../docs/javascripts/production-lifecycle.js");

const NOW = Date.parse("2026-08-20T12:00:00Z");
const TARGET_CONFIG = {
  agent: ["qualified_agent_bridge_release", "public_package"],
  capture: ["qualified_native_recorder_release", "public_package"],
  cloud: ["qualified_workflow_control_plane_deployment", "private_deployment"],
  desktop: ["qualified_native_workflow_desktop_release", "public_package"],
  docs: ["production_documentation_deployment", "public_deployment"],
  flow: ["qualified_workflow_runtime_release", "public_package"],
  openadapt: ["qualified_workflow_launcher_release", "public_package"],
};

function release(kind) {
  if (kind === "public_package") return { kind, version: "1.2.3" };
  if (kind === "public_deployment") return { kind, deployment_id: "docs-123" };
  return { kind, deployment_release_id: "cloud-123" };
}

function admission(targetId, sequence = 1, overrides = {}) {
  const [claimScope, releaseKind] = TARGET_CONFIG[targetId];
  return {
    admission_id: `production:${targetId}:${sequence}`,
    target: targetId,
    claim_scope: claimScope,
    release_identity: {
      schema_version: "openadapt.monotonic-production-release/v1",
      channel: "production",
      sequence,
      previous_admission_sha256: null,
    },
    policy_revision: 1,
    release: release(releaseKind),
    acceptance_evidence: {
      summary_url: `https://evidence.openadapt.ai/${targetId}.json`,
      summary_sha256: `sha256:${"a".repeat(64)}`,
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
  const bytes = Buffer.from(JSON.stringify(live));
  const digest = `sha256:${createHash("sha256").update(bytes).digest("hex")}`;
  const projection = {
    $schema: "schemas/production-lifecycle-public.schema.json",
    schema_version: "openadapt.public-production-lifecycle/v1",
    source: source(digest),
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
      const [claimScope, releaseKind] = TARGET_CONFIG[targetId];
      return {
        id: targetId,
        display_name: targetId,
        lifecycle_scope: targetId === "docs" ? "public_surface" : "repository",
        lifecycle_subject: targetId,
        source_repository: `OpenAdaptAI/${targetId}`,
        required_claim_scope: claimScope,
        release_kind: releaseKind,
        required_artifact_kinds: [],
        package_index_project: null,
        artifact_authority_by_kind: {},
        admission_history: history,
        latest_admission: history.at(-1) ?? null,
      };
    }),
  };
  return { bytes, live, projection };
}

function fetchFixture(fixture, options = {}) {
  return async (url) => {
    if (options.unavailable) return { ok: false };
    if (url.startsWith(`${lifecycle.PROJECTION_URL}?openadapt_lifecycle_request=`)) {
      return { ok: true, json: async () => structuredClone(fixture.projection) };
    }
    if (url.startsWith("https://pypi.org/pypi/")) {
      const project = url.split("/")[4];
      const version = options.pypiVersions?.[project] ?? "1.2.3";
      const hasYankedValue = Object.prototype.hasOwnProperty.call(
        options.pypiYankedValues ?? {},
        project,
      );
      const yanked = hasYankedValue
        ? options.pypiYankedValues[project]
        : (options.pypiYanked?.includes(project) ?? false);
      const artifact = (packagetype) =>
        options.pypiMissingYanked?.includes(project)
          ? { packagetype }
          : { packagetype, yanked };
      return {
        ok: !options.pypiUnavailable,
        json: async () => ({
          info: { version },
          releases: {
            [version]: [
              artifact("bdist_wheel"),
              artifact("sdist"),
            ],
          },
        }),
      };
    }
    const bytes = options.bytes ?? fixture.bytes;
    return {
      ok: true,
      arrayBuffer: async () => bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
    };
  };
}

test("a current digest-bound admission renders every target as Production", async () => {
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

test("each validation requests uncached projection and live-record URLs", async () => {
  const fixture = makeFixture();
  const urls = [];
  const fetchImpl = fetchFixture(fixture);
  const recordingFetch = async (url, options) => {
    urls.push(url);
    assert.equal(options.cache, "no-store");
    return fetchImpl(url, options);
  };

  await lifecycle.load(recordingFetch, NOW);
  await lifecycle.load(recordingFetch, NOW);

  assert.equal(urls.length, 14);
  assert.notEqual(urls[0], urls[7]);
  assert.notEqual(urls[1], urls[8]);
  assert.match(urls[0], /^\/production-lifecycle\.json\?openadapt_lifecycle_request=/);
  assert.match(
    urls[1],
    /^https:\/\/raw\.githubusercontent\.com\/OpenAdaptAI\/\.github\/main\/production-lifecycle-admissions\.json\?openadapt_lifecycle_request=/,
  );
});

test("PyPI drift or a yanked default artifact blocks only product-wide Production", async () => {
  const fixture = makeFixture();
  const drifted = await lifecycle.load(
    fetchFixture(fixture, { pypiVersions: { "openadapt-flow": "1.2.4" } }),
    NOW,
  );
  assert.equal(drifted.activeTargets.size, 7);
  assert.equal(drifted.defaultInstallVerified, false);

  const yanked = await lifecycle.load(
    fetchFixture(fixture, { pypiYanked: ["openadapt-agent"] }),
    NOW,
  );
  assert.equal(yanked.activeTargets.size, 7);
  assert.equal(yanked.defaultInstallVerified, false);

  const missingYanked = await lifecycle.load(
    fetchFixture(fixture, { pypiMissingYanked: ["openadapt-capture"] }),
    NOW,
  );
  assert.equal(missingYanked.defaultInstallVerified, false);

  const malformedYanked = await lifecycle.load(
    fetchFixture(fixture, {
      pypiYankedValues: { "openadapt-desktop": "false" },
    }),
    NOW,
  );
  assert.equal(malformedYanked.defaultInstallVerified, false);
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

test("product-wide Production requires all seven active targets", () => {
  const product = { textContent: "" };
  const document = {
    querySelectorAll(selector) {
      if (selector === "[data-openadapt-production-product]") return [product];
      return [];
    },
  };
  const six = new Map(lifecycle.TARGET_IDS.slice(0, 6).map((id) => [id, {}]));
  lifecycle.render(document, { activeTargets: six, defaultInstallVerified: true });
  assert.equal(product.textContent, lifecycle.PRODUCT_REQUIREMENT);

  const seven = new Map(lifecycle.TARGET_IDS.map((id) => [id, {}]));
  lifecycle.render(document, {
    activeTargets: seven,
    defaultInstallVerified: false,
  });
  assert.equal(product.textContent, lifecycle.PRODUCT_REQUIREMENT);
  lifecycle.render(document, {
    activeTargets: seven,
    defaultInstallVerified: true,
  });
  assert.equal(product.textContent, "Production");
});

test("the committed admission-free projection keeps every label neutral", async () => {
  const committed = require("../../docs/production-lifecycle.json");
  const targets = lifecycle.validateProjection(committed);

  assert.ok(targets instanceof Map);
  for (const target of targets.values()) {
    assert.equal(lifecycle.deriveTarget(target, committed, NOW), null);
  }
});
