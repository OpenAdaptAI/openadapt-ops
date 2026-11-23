# What's New

> *Pull requests merged in the last 7 days across the OpenAdapt repositories, grouped by the release that contains them.*
> *Last updated: 2026-11-22 06:20 UTC*

Items under **Merged, not released yet** are on a repository's `main` branch only. They are not in any published package or installer yet.

## OpenAdapt

### Released in openadapt-flow 3.4.0

- [release(flow): 3.4.0 requires openadapt-privacy 1.1.4](https://github.com/OpenAdaptAI/OpenAdapt/pull/2470) (#2470), merged 2026-11-21
- [fix(flow): keep ir within its import-time budget (main is red)](https://github.com/OpenAdaptAI/OpenAdapt/pull/2466) (#2466), merged 2026-11-21
- [refactor(flow): move the replayer's asset, healing and step-evidence helpers to a mixin, unchanged](https://github.com/OpenAdaptAI/OpenAdapt/pull/2459) (#2459), merged 2026-11-21
- [refactor(flow): move the replayer's qualification fault injection to a mixin, unchanged](https://github.com/OpenAdaptAI/OpenAdapt/pull/2456) (#2456), merged 2026-11-21
- [refactor(flow): move the replayer's module-level helpers to runtime/replay/_shared.py, re-exported unchanged](https://github.com/OpenAdaptAI/OpenAdapt/pull/2455) (#2455), merged 2026-11-21
- [refactor(flow): move the qualification data model to qualification/models.py, re-exported unchanged](https://github.com/OpenAdaptAI/OpenAdapt/pull/2454) (#2454), merged 2026-11-21
- [refactor(flow): the package loads its ir re-exports on first use](https://github.com/OpenAdaptAI/OpenAdapt/pull/2451) (#2451), merged 2026-11-21
- [refactor(flow): qualification imports execution_profiles where it uses it, breaking the ir import cycle](https://github.com/OpenAdaptAI/OpenAdapt/pull/2439) (#2439), merged 2026-11-21
- [ci(ratchet): size budgets never rise; dropping the row of an existing file fails](https://github.com/OpenAdaptAI/OpenAdapt/pull/2430) (#2430), merged 2026-11-21

### Merged, not released yet

- [fix(hooks): emit #2410-compliant StepResult fields in hooks receipt reports](https://github.com/OpenAdaptAI/OpenAdapt/pull/2496) (#2496), merged 2026-11-22, openadapt-flow
- [feat(flow): compose novel field-set contracts with planted-fault admission (P6)](https://github.com/OpenAdaptAI/OpenAdapt/pull/2490) (#2490), merged 2026-11-21, openadapt-flow
- [fix(flow): bind null SQL verification read params as IS NULL (fail closed)](https://github.com/OpenAdaptAI/OpenAdapt/pull/2489) (#2489), merged 2026-11-21, openadapt-flow
- [refactor(flow): extract Stedi 270/271 eligibility client into optional connector package](https://github.com/OpenAdaptAI/OpenAdapt/pull/2488) (#2488), merged 2026-11-21, openadapt-flow
- [refactor(flow): generalize Execute seeding, reward bundles, and identity chrome](https://github.com/OpenAdaptAI/OpenAdapt/pull/2486) (#2486), merged 2026-11-22, openadapt-flow
- [feat(flow): Global-to-Local (GOLD) ROI cropping and unified VetoOnlyVLMGuard](https://github.com/OpenAdaptAI/OpenAdapt/pull/2485) (#2485), merged 2026-11-22, openadapt-flow
- [build(deps): bump the github-actions group across 1 directory with 2 updates](https://github.com/OpenAdaptAI/OpenAdapt/pull/2436) (#2436), merged 2026-11-21
- [build(deps): bump zip from 9.5.1 to 9.7.0 in /packages/desktop/src-tauri in the cargo-desktop group](https://github.com/OpenAdaptAI/OpenAdapt/pull/2435) (#2435), merged 2026-11-21
- [build(deps): bump boto3 from 1.44.4 to 1.44.5 in /packages/desktop in the uv-desktop group](https://github.com/OpenAdaptAI/OpenAdapt/pull/2434) (#2434), merged 2026-11-21
- [build(deps-dev): bump the npm-desktop group in /packages/desktop with 2 updates](https://github.com/OpenAdaptAI/OpenAdapt/pull/2433) (#2433), merged 2026-11-21
- [fix(scripts): verify_moved_code sees a module that became a package](https://github.com/OpenAdaptAI/OpenAdapt/pull/2431) (#2431), merged 2026-11-21

