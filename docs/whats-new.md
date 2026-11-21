# What's New

> *Pull requests merged in the last 7 days across the OpenAdapt repositories, grouped by the release that contains them.*
> *Last updated: 2026-11-21 14:44 UTC*

Items under **Merged, not released yet** are on a repository's `main` branch only. They are not in any published package or installer yet.

## OpenAdapt

### Merged, not released yet

- [fix(flow): keep ir within its import-time budget (main is red)](https://github.com/OpenAdaptAI/OpenAdapt/pull/2466) (#2466), merged 2026-11-21, openadapt-flow
- [refactor(flow): move the replayer's asset, healing and step-evidence helpers to a mixin, unchanged](https://github.com/OpenAdaptAI/OpenAdapt/pull/2459) (#2459), merged 2026-11-21, openadapt-flow
- [refactor(flow): move the replayer's qualification fault injection to a mixin, unchanged](https://github.com/OpenAdaptAI/OpenAdapt/pull/2456) (#2456), merged 2026-11-21, openadapt-flow
- [refactor(flow): move the replayer's module-level helpers to runtime/replay/_shared.py, re-exported unchanged](https://github.com/OpenAdaptAI/OpenAdapt/pull/2455) (#2455), merged 2026-11-21, openadapt-flow
- [refactor(flow): move the qualification data model to qualification/models.py, re-exported unchanged](https://github.com/OpenAdaptAI/OpenAdapt/pull/2454) (#2454), merged 2026-11-21, openadapt-flow
- [refactor(flow): the package loads its ir re-exports on first use](https://github.com/OpenAdaptAI/OpenAdapt/pull/2451) (#2451), merged 2026-11-21, openadapt-flow
- [refactor(flow): qualification imports execution_profiles where it uses it, breaking the ir import cycle](https://github.com/OpenAdaptAI/OpenAdapt/pull/2439) (#2439), merged 2026-11-21, openadapt-flow
- [fix(scripts): verify_moved_code sees a module that became a package](https://github.com/OpenAdaptAI/OpenAdapt/pull/2431) (#2431), merged 2026-11-21
- [ci(ratchet): size budgets never rise; dropping the row of an existing file fails](https://github.com/OpenAdaptAI/OpenAdapt/pull/2430) (#2430), merged 2026-11-21, openadapt-flow
- [test: Flow layers import downward only, with import-time budgets for low modules](https://github.com/OpenAdaptAI/OpenAdapt/pull/2427) (#2427), merged 2026-11-21, openadapt-flow
- [test: pin the JSON schema of every model in ir and the qualification modules](https://github.com/OpenAdaptAI/OpenAdapt/pull/2424) (#2424), merged 2026-11-21, openadapt-flow
- [test: pin every Flow import path that Desktop, the launcher, Verify, Agent and Cloud use](https://github.com/OpenAdaptAI/OpenAdapt/pull/2422) (#2422), merged 2026-11-21, openadapt-flow
- [Halt connector runs whose callback is refused after child handoff](https://github.com/OpenAdaptAI/OpenAdapt/pull/2399) (#2399), merged 2026-11-21, openadapt-flow
- [ci(flow): four PR shards; move 31 slow non-safety cases out of the PR lane](https://github.com/OpenAdaptAI/OpenAdapt/pull/2398) (#2398), merged 2026-11-21, openadapt-flow
- [fix(tx): relay same-origin redirects through the wire tap](https://github.com/OpenAdaptAI/OpenAdapt/pull/2392) (#2392), merged 2026-11-21, openadapt-flow
- [ci: drop pull-request lanes that never failed and batch CodeQL on main](https://github.com/OpenAdaptAI/OpenAdapt/pull/2387) (#2387), merged 2026-11-21
- [feat(flow): send the stored report's SHA-256 from the connector](https://github.com/OpenAdaptAI/OpenAdapt/pull/2386) (#2386), merged 2026-11-21, openadapt-flow
- [fix(flow): read the connector's read-back labels from the v1 effect receipt](https://github.com/OpenAdaptAI/OpenAdapt/pull/2384) (#2384), merged 2026-11-21, openadapt-flow
- [build(deps): lift Pillow, aiohttp, filelock and other locked dependencies to fixed releases](https://github.com/OpenAdaptAI/OpenAdapt/pull/2383) (#2383), merged 2026-11-21, openadapt-flow
- [feat(quickstart): offer the checked and the stopped run's Seals in one question](https://github.com/OpenAdaptAI/OpenAdapt/pull/2381) (#2381), merged 2026-11-21

