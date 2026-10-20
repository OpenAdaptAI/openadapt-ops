# What's New

> *Pull requests merged in the last 7 days across the OpenAdapt repositories, grouped by the release that contains them.*
> *Last updated: 2026-10-20 20:44 UTC*

Items under **Merged, not released yet** are on a repository's `main` branch only. They are not in any published package or installer yet.

## OpenAdapt

### Released in openadapt-flow 2.3.0

- [chore(release): openadapt-flow 2.3.0](https://github.com/OpenAdaptAI/OpenAdapt/pull/1427) (#1427), merged 2026-10-20
- [batch: teach scope, run authorizations, redaction, merge queue, main dedupe, Desktop program map, tray fold](https://github.com/OpenAdaptAI/OpenAdapt/pull/1421) (#1421), merged 2026-10-20
- [test(flow): pin the clock in two deferred-report assertions](https://github.com/OpenAdaptAI/OpenAdapt/pull/1418) (#1418), merged 2026-10-20
- [flow: authorization follow-ups: one count per report, closed item labels](https://github.com/OpenAdaptAI/OpenAdapt/pull/1416) (#1416), merged 2026-10-20

### Released in OpenAdapt 1.18.0

- [fix(cli): the PATH version check never runs inside the check it starts](https://github.com/OpenAdaptAI/OpenAdapt/pull/1432) (#1432), merged 2026-10-20
- [docs: public copy states what was measured, not what wasn't](https://github.com/OpenAdaptAI/OpenAdapt/pull/1430) (#1430), merged 2026-10-20
- [chore(release): openadapt 1.18.0](https://github.com/OpenAdaptAI/OpenAdapt/pull/1429) (#1429), merged 2026-10-20
- [feat(manifest): bind components released from the monorepo](https://github.com/OpenAdaptAI/OpenAdapt/pull/1428) (#1428), merged 2026-10-20
- [chore(deps): Bump click from 8.4.2 to 8.5.0 in /packages/tray](https://github.com/OpenAdaptAI/OpenAdapt/pull/1426) (#1426), merged 2026-10-20
- [chore(deps): Bump pynput from 1.8.1 to 1.8.2 in /packages/tray](https://github.com/OpenAdaptAI/OpenAdapt/pull/1425) (#1425), merged 2026-10-20
- [chore(deps): Bump pygments from 2.20.0 to 2.21.0 in /packages/tray](https://github.com/OpenAdaptAI/OpenAdapt/pull/1424) (#1424), merged 2026-10-20
- [chore(deps): Bump pyobjc-framework-cocoa from 12.1 to 12.2.2 in /packages/tray](https://github.com/OpenAdaptAI/OpenAdapt/pull/1423) (#1423), merged 2026-10-20
- [chore(deps): Bump ruff from 0.16.0 to 0.17.1 in /packages/tray](https://github.com/OpenAdaptAI/OpenAdapt/pull/1422) (#1422), merged 2026-10-20
- [ci(desktop): resume a release that reached PyPI but not its published release](https://github.com/OpenAdaptAI/OpenAdapt/pull/1417) (#1417), merged 2026-10-20
- [ci: cancel superseded Packages runs on main unless the push changes Desktop](https://github.com/OpenAdaptAI/OpenAdapt/pull/1415) (#1415), merged 2026-10-20

### Merged, not released yet

- [Qualify an already-qualified, encrypted or sealed bundle](https://github.com/OpenAdaptAI/OpenAdapt/pull/1454) (#1454), merged 2026-10-20, openadapt-flow
- [Seal a qualified bundle: drop its authorization template with its certification](https://github.com/OpenAdaptAI/OpenAdapt/pull/1453) (#1453), merged 2026-10-20, openadapt-flow
- [Run an API step under a managed dispatch that names it](https://github.com/OpenAdaptAI/OpenAdapt/pull/1444) (#1444), merged 2026-10-20, openadapt-flow
- [verify-run: frame conditions (nothing outside the declared delta changed)](https://github.com/OpenAdaptAI/OpenAdapt/pull/1443) (#1443), merged 2026-10-20, openadapt-flow
- [docs: record checks that cover their own blind spots (design)](https://github.com/OpenAdaptAI/OpenAdapt/pull/1434) (#1434), merged 2026-10-20, openadapt-flow

## openadapt-desktop

### Released in openadapt-desktop 0.20.0

- [test(shadow): make the shadow-mode tests pass on Windows](https://github.com/OpenAdaptAI/openadapt-desktop/pull/213) (#213), merged 2026-10-18
- [feat(portal): one swipe card per decision for paused runs and saves](https://github.com/OpenAdaptAI/openadapt-desktop/pull/212) (#212), merged 2026-10-18
- [Portal: relay Flow's save-approval tasks to the paired phone](https://github.com/OpenAdaptAI/openadapt-desktop/pull/207) (#207), merged 2026-10-18
- [feat: opt-in, local shadow mode with a notice, status indicators, and draft offers](https://github.com/OpenAdaptAI/openadapt-desktop/pull/205) (#205), merged 2026-10-18

### Released in openadapt-desktop 0.19.0

- [feat(teach): offer a branch once one step's halt is resolved twice](https://github.com/OpenAdaptAI/openadapt-desktop/pull/194) (#194), merged 2026-10-17

### Released in openadapt-desktop 0.18.0

- [feat(needs-you): show the field diff on a Check the record stop](https://github.com/OpenAdaptAI/openadapt-desktop/pull/203) (#203), merged 2026-10-17
- [copy: drop 'once' from show-the-task text](https://github.com/OpenAdaptAI/openadapt-desktop/pull/202) (#202), merged 2026-10-17
- [build: pin openadapt-flow 2.1.0](https://github.com/OpenAdaptAI/openadapt-desktop/pull/200) (#200), merged 2026-10-17
- [docs(readme): an agent can drive recording in native Windows apps and over RDP/Citrix](https://github.com/OpenAdaptAI/openadapt-desktop/pull/199) (#199), merged 2026-10-17
- [build: upgrade to React 19](https://github.com/OpenAdaptAI/openadapt-desktop/pull/198) (#198), merged 2026-10-17
- [build: bump Tauri JS and Rust dependencies together](https://github.com/OpenAdaptAI/openadapt-desktop/pull/197) (#197), merged 2026-10-17

### Released in openadapt-desktop 0.17.1

- [fix(deps): upgrade zip to 9.0 for RUSTSEC-2026-0367/0368/0369](https://github.com/OpenAdaptAI/openadapt-desktop/pull/195) (#195), merged 2026-10-17

### Released in openadapt-desktop 0.17.0

- [ci(release): publish engine releases automatically on green main](https://github.com/OpenAdaptAI/openadapt-desktop/pull/193) (#193), merged 2026-10-16
- [build: set the package author to MLDSAI Inc.](https://github.com/OpenAdaptAI/openadapt-desktop/pull/192) (#192), merged 2026-10-16
- [README: a person or an agent shows the task](https://github.com/OpenAdaptAI/openadapt-desktop/pull/191) (#191), merged 2026-10-16
- [fix!: keep local data private; package imports as openadapt_desktop](https://github.com/OpenAdaptAI/openadapt-desktop/pull/190) (#190), merged 2026-10-14
- [fix(tests): keep bundle and qualification keys off the real keychain](https://github.com/OpenAdaptAI/openadapt-desktop/pull/189) (#189), merged 2026-10-14
- [fix: make the source quick start work, and rewrite the README for developers](https://github.com/OpenAdaptAI/openadapt-desktop/pull/188) (#188), merged 2026-10-14
- [chore: sync the published source policy](https://github.com/OpenAdaptAI/openadapt-desktop/pull/187) (#187), merged 2026-10-14
- [fix: never call a saving task read-only; run Check it signed in](https://github.com/OpenAdaptAI/openadapt-desktop/pull/185) (#185), merged 2026-10-14

## openadapt-ml

### Released in openadapt-ml 0.17.0

- [feat(cloud): Kaggle GPU training path and a guard against Modal GPU on production](https://github.com/OpenAdaptAI/openadapt-ml/pull/82) (#82), merged 2026-10-17
- [docs(readme): shorten the research banner to two lines](https://github.com/OpenAdaptAI/openadapt-ml/pull/81) (#81), merged 2026-10-16
- [chore: sync the published source policy](https://github.com/OpenAdaptAI/openadapt-ml/pull/80) (#80), merged 2026-10-14

## openadapt-evals

### Released in openadapt-evals 0.98.0

- [fix: run on openadapt-types 0.19 through 0.21](https://github.com/OpenAdaptAI/openadapt-evals/pull/352) (#352), merged 2026-10-16
- [docs(readme): organize by benchmark, local vs cloud VM, known limitations](https://github.com/OpenAdaptAI/openadapt-evals/pull/351) (#351), merged 2026-10-16
- [feat(evidence): publish the Flow 1.35.1 comparison; supersede 1.34.0](https://github.com/OpenAdaptAI/openadapt-evals/pull/349) (#349), merged 2026-10-14
- [feat: add audit-verifier to find wrong side effects a checker accepts](https://github.com/OpenAdaptAI/openadapt-evals/pull/348) (#348), merged 2026-10-14
- [fix: score live Flow replays with WAA's evaluator; plain README](https://github.com/OpenAdaptAI/openadapt-evals/pull/347) (#347), merged 2026-10-14
- [chore: sync the published source policy](https://github.com/OpenAdaptAI/openadapt-evals/pull/346) (#346), merged 2026-10-14
- [chore(release): prepare 0.98.0](https://github.com/OpenAdaptAI/openadapt-evals/pull/345) (#345), merged 2026-10-17
- [fix: stale evidence notice, fresh-clone installs, RL instruction](https://github.com/OpenAdaptAI/openadapt-evals/pull/344) (#344), merged 2026-10-14

## openadapt-capture

### Released in openadapt-capture 1.3.0

- [ci(release): gate releases on a hosted Linux Xvfb lane](https://github.com/OpenAdaptAI/openadapt-capture/pull/166) (#166), merged 2026-10-17
- [chore(release): finish 1.3.0 with shadow mode](https://github.com/OpenAdaptAI/openadapt-capture/pull/160) (#160), merged 2026-10-17
- [chore(deps): let Dependabot update uv.lock by using the uv ecosystem](https://github.com/OpenAdaptAI/openadapt-capture/pull/159) (#159), merged 2026-10-17
- [fix(recorder): keep late progress updates from rewriting the state being sealed](https://github.com/OpenAdaptAI/openadapt-capture/pull/158) (#158), merged 2026-10-17
- [test(input-observer): stop charging a deliberate setup wait to a 0.2s readiness deadline](https://github.com/OpenAdaptAI/openadapt-capture/pull/157) (#157), merged 2026-10-17
- [feat(shadow): local, opt-in detection of repeated work](https://github.com/OpenAdaptAI/openadapt-capture/pull/156) (#156), merged 2026-10-17
- [chore(deps-dev): update pytest-timeout requirement from >=2.0.0 to >=2.4.0](https://github.com/OpenAdaptAI/openadapt-capture/pull/154) (#154), merged 2026-10-17
- [chore(deps): update sqlalchemy requirement from >=2.0.0 to >=2.0.54](https://github.com/OpenAdaptAI/openadapt-capture/pull/153) (#153), merged 2026-10-17
- [chore(deps): update alembic requirement from >=1.0.0 to >=1.20.0](https://github.com/OpenAdaptAI/openadapt-capture/pull/152) (#152), merged 2026-10-17
- [chore(deps): update matplotlib requirement from >=3.10.8 to >=3.10.9](https://github.com/OpenAdaptAI/openadapt-capture/pull/151) (#151), merged 2026-10-17
- [chore(deps-dev): update pytest requirement from >=7.0.0 to >=9.1.1](https://github.com/OpenAdaptAI/openadapt-capture/pull/150) (#150), merged 2026-10-17
- [chore(deps): ignore PyGObject >=3.51 in dependabot](https://github.com/OpenAdaptAI/openadapt-capture/pull/149) (#149), merged 2026-10-17
- [docs(readme): add a status line and platform table](https://github.com/OpenAdaptAI/openadapt-capture/pull/148) (#148), merged 2026-10-16
- [fix(deps): patch Dependabot security alerts](https://github.com/OpenAdaptAI/openadapt-capture/pull/147) (#147), merged 2026-10-14
- [fix: record native input through the authentication gate](https://github.com/OpenAdaptAI/openadapt-capture/pull/146) (#146), merged 2026-10-14
- [ci: name the failed release step in the release-health issue](https://github.com/OpenAdaptAI/openadapt-capture/pull/145) (#145), merged 2026-10-14
- [docs: lead the README with a quick start; fix Linux X RECORD startup and CLI setup errors](https://github.com/OpenAdaptAI/openadapt-capture/pull/144) (#144), merged 2026-10-14
- [chore(deps): bump actions/download-artifact from 8.0.1 to 8.0.2](https://github.com/OpenAdaptAI/openadapt-capture/pull/142) (#142), merged 2026-10-17

### Merged, not released yet

- [docs: say this repository moved to the OpenAdapt monorepo](https://github.com/OpenAdaptAI/openadapt-capture/pull/168) (#168), merged 2026-10-18
- [ci(release): publish GitHub Releases with gh and the release App](https://github.com/OpenAdaptAI/openadapt-capture/pull/167) (#167), merged 2026-10-18

## openadapt-privacy

### Merged, not released yet

- [fix(scan): remove site-specific tokens from the forbidden-path list](https://github.com/OpenAdaptAI/openadapt-privacy/pull/24) (#24), merged 2026-10-18
- [docs: lead the README with what the package does and a quick start](https://github.com/OpenAdaptAI/openadapt-privacy/pull/23) (#23), merged 2026-10-14
- [chore: sync the published source policy](https://github.com/OpenAdaptAI/openadapt-privacy/pull/22) (#22), merged 2026-10-14
- [fix: fail the PHI scan closed and drop the pip runtime dependency](https://github.com/OpenAdaptAI/openadapt-privacy/pull/21) (#21), merged 2026-10-14

## openadapt-grounding

### Merged, not released yet

- [docs(readme): mark as archived research](https://github.com/OpenAdaptAI/openadapt-grounding/pull/13) (#13), merged 2026-10-16
- [docs(readme): shorten the research banner to two lines](https://github.com/OpenAdaptAI/openadapt-grounding/pull/12) (#12), merged 2026-10-16
- [README: a person or an agent shows the task](https://github.com/OpenAdaptAI/openadapt-grounding/pull/11) (#11), merged 2026-10-16

## openadapt-retrieval

### Merged, not released yet

- [docs(readme): mark as archived research](https://github.com/OpenAdaptAI/openadapt-retrieval/pull/12) (#12), merged 2026-10-16
- [docs(readme): shorten the research banner to two lines](https://github.com/OpenAdaptAI/openadapt-retrieval/pull/11) (#11), merged 2026-10-16

