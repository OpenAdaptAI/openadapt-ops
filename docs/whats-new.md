# What's New

> *Pull requests merged in the last 7 days across the OpenAdapt repositories, grouped by the release that contains them.*
> *Last updated: 2026-11-25 04:09 UTC*

Items under **Merged, not released yet** are on a repository's `main` branch only. They are not in any published package or installer yet.

## OpenAdapt

### Released in openadapt-types 0.24.2

- [docs(types): list #2495's additions in v0.24.2 and restart its publish](https://github.com/OpenAdaptAI/OpenAdapt/pull/2640) (#2640), merged 2026-11-24

### Released in openadapt-flow 4.0.0

- [fix(flow): guard __main__.py entrypoints with if __name__ == '__main__'](https://github.com/OpenAdaptAI/OpenAdapt/pull/2639) (#2639), merged 2026-11-24
- [fix(flow): require openadapt-types>=0.24.2 for Flow 4.0.0](https://github.com/OpenAdaptAI/OpenAdapt/pull/2637) (#2637), merged 2026-11-24
- [fix(flow): fail closed on crashed rechecks, shared secret-field names, refuse forged --check (fix-forward #2438)](https://github.com/OpenAdaptAI/OpenAdapt/pull/2635) (#2635), merged 2026-11-24
- [fix(extension): camelCase-aware secret field names in every redaction layer (fix-forward for #2575)](https://github.com/OpenAdaptAI/OpenAdapt/pull/2621) (#2621), merged 2026-11-24
- [fix(flow): green main after #2594 and re-trigger the types and verify publish](https://github.com/OpenAdaptAI/OpenAdapt/pull/2616) (#2616), merged 2026-11-24

### Released in openadapt-agent 2.2.4

- [docs(agent): note openadapt-flow 4.0.0 on PyPI and restart v2.2.4 publish](https://github.com/OpenAdaptAI/OpenAdapt/pull/2649) (#2649), merged 2026-11-25

### Released in OpenAdapt 1.24.0

- [test(desktop): distinguish bundled Flow pin vs in-tree Flow in dependency compat test](https://github.com/OpenAdaptAI/OpenAdapt/pull/2648) (#2648), merged 2026-11-25
- [fix(seal-view): validate predicate.evidence_scope in JS receipt verifier](https://github.com/OpenAdaptAI/OpenAdapt/pull/2643) (#2643), merged 2026-11-24
- [ci(packages): raise flow core unit timeout to 60m on main pushes](https://github.com/OpenAdaptAI/OpenAdapt/pull/2642) (#2642), merged 2026-11-24
- [fix(desktop): open() lands on the requested URL; skip real-Chrome test without Chrome (fix-forward #2358)](https://github.com/OpenAdaptAI/OpenAdapt/pull/2636) (#2636), merged 2026-11-24
- [feat(verify): add local JIT compiler (openadapt_verify.jit) and mcpify --from-compiled](https://github.com/OpenAdaptAI/OpenAdapt/pull/2633) (#2633), merged 2026-11-25
- [chore(security): allowlist two synthetic esp-scripted record ids in gitleaks](https://github.com/OpenAdaptAI/OpenAdapt/pull/2628) (#2628), merged 2026-11-24
- [fix(verify): bind reload read-back to visible field values and cap declared producers](https://github.com/OpenAdaptAI/OpenAdapt/pull/2623) (#2623), merged 2026-11-24

### Merged, not released yet

- [chore(release): record published openadapt 1.24.0 in platform-manifest.json](https://github.com/OpenAdaptAI/OpenAdapt/pull/2654) (#2654), merged 2026-11-25
- [feat(desktop): add local Before/After step screenshot preview to WatchRun](https://github.com/OpenAdaptAI/OpenAdapt/pull/2653) (#2653), merged 2026-11-25
- [feat(desktop): redesign desktop app UI for modern native-grade clarity and polish](https://github.com/OpenAdaptAI/OpenAdapt/pull/2651) (#2651), merged 2026-11-25
- [feat(types,verify,flow): add first-class agent_used and verifier_adapter receipt fields](https://github.com/OpenAdaptAI/OpenAdapt/pull/2650) (#2650), merged 2026-11-25, openadapt-types
- [test(desktop): fail closed when the bundled Flow is required but not installed](https://github.com/OpenAdaptAI/OpenAdapt/pull/2646) (#2646), merged 2026-11-25
- [fix(seal-view): reject null and missing evidence_scope fields that Python rejects (follow-up #2643)](https://github.com/OpenAdaptAI/OpenAdapt/pull/2644) (#2644), merged 2026-11-24, openadapt-types

