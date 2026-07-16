# What's New

> *Auto-generated digest of recent changes across the OpenAdapt ecosystem.*
> *Last updated: 2026-07-16 00:32 UTC*



## OpenAdapt


- [fix: align launcher lifecycle metadata with beta](https://github.com/OpenAdaptAI/OpenAdapt/pull/1016) (#1016) — merged 

- [chore: keep release lock version synchronized](https://github.com/OpenAdaptAI/OpenAdapt/pull/1015) (#1015) — merged 

- [feat: make OpenAdapt the canonical openadapt-flow launcher](https://github.com/OpenAdaptAI/OpenAdapt/pull/1014) (#1014) — merged 

- [fix: version reads from metadata + doctor core/optional sets + pyproject description](https://github.com/OpenAdaptAI/OpenAdapt/pull/1013) (#1013) — merged 

- [docs: refocus OpenAdapt on the demonstration compiler (remove package-zoo / old platform framing)](https://github.com/OpenAdaptAI/OpenAdapt/pull/1012) (#1012) — merged 

- [fix: Discord badge 'invalid server' (switch to static badge)](https://github.com/OpenAdaptAI/OpenAdapt/pull/1011) (#1011) — merged 

- [feat: mount `openadapt flow demo-record`](https://github.com/OpenAdaptAI/OpenAdapt/pull/1010) (#1010) — merged 

- [feat: mount the demonstration compiler as `openadapt flow …` and lead the CLI with it](https://github.com/OpenAdaptAI/OpenAdapt/pull/1009) (#1009) — merged 

- [docs: refresh README (accurate positioning + demonstration compiler prominence)](https://github.com/OpenAdaptAI/OpenAdapt/pull/1007) (#1007) — merged 

- [feat: expose openadapt-flow as the [flow] extra (demonstration compiler under the core brand)](https://github.com/OpenAdaptAI/OpenAdapt/pull/1006) (#1006) — merged 



## openadapt-flow


- [fix: build releases without unsupported lock resolution](https://github.com/OpenAdaptAI/openadapt-flow/pull/126) (#126) — merged 

- [fix: restore supported Python release matrix](https://github.com/OpenAdaptAI/openadapt-flow/pull/124) (#124) — merged 

- [feat: govern hosted artifact activation and runtime validation](https://github.com/OpenAdaptAI/openadapt-flow/pull/119) (#119) — merged 

- [feat: desktop recording via record --backend windows|rdp (record->compile->replay on desktop)](https://github.com/OpenAdaptAI/openadapt-flow/pull/118) (#118) — merged 

- [feat: auto-provision win_agent TLS cert on launch + fix pre-existing factory token test](https://github.com/OpenAdaptAI/openadapt-flow/pull/117) (#117) — merged 

- [chore: wire sealed-templates+resume through the new seams; fix pre-existing OCR benchmark test](https://github.com/OpenAdaptAI/openadapt-flow/pull/116) (#116) — merged 

- [feat: CLI backend selector (--backend web|windows|rdp) — unblock the desktop/Citrix path](https://github.com/OpenAdaptAI/openadapt-flow/pull/115) (#115) — merged 

- [chore: pin ruff==0.15.21 (stop CI/local formatter drift)](https://github.com/OpenAdaptAI/openadapt-flow/pull/114) (#114) — merged 

- [feat: seal template screenshot crops in the AEAD bundle (close at-rest image-PHI gap)](https://github.com/OpenAdaptAI/openadapt-flow/pull/113) (#113) — merged 

- [feat: TLS + cert-pinning on the win_agent channel (PHI-in-transit encryption)](https://github.com/OpenAdaptAI/openadapt-flow/pull/112) (#112) — merged 

- [ci: make E2E/wheel/CLI-smoke/docs/coverage merge-blocking + mypy-strict on safety path + CODEOWNERS](https://github.com/OpenAdaptAI/openadapt-flow/pull/111) (#111) — merged 

- [feat: claim->evidence validation harness (maturity claims backed by tests + reproducible report)](https://github.com/OpenAdaptAI/openadapt-flow/pull/110) (#110) — merged 

- [feat: fail-closed 'openadapt-flow run' for regulated execution (cert+identity+effect+crypto gates)](https://github.com/OpenAdaptAI/openadapt-flow/pull/109) (#109) — merged 

- [docs: remove agent-partition build notes, honest backend status, claims-consistency with LIMITS](https://github.com/OpenAdaptAI/openadapt-flow/pull/108) (#108) — merged 

- [docs(on-prem): reconcile at-rest note with shipped AEAD encryption](https://github.com/OpenAdaptAI/openadapt-flow/pull/107) (#107) — merged 

- [feat: Citrix/remote-display pixel-only e2e proof (UIA-off, on-screen verify, identity-gate + halt)](https://github.com/OpenAdaptAI/openadapt-flow/pull/106) (#106) — merged 

- [feat: on-prem (air-gapped) clinic deployment package + docs](https://github.com/OpenAdaptAI/openadapt-flow/pull/105) (#105) — merged 

- [feat: integrated OpenEMR end-to-end harness (compiled arm, cost-capped agent arm gated off)](https://github.com/OpenAdaptAI/openadapt-flow/pull/104) (#104) — merged 

- [feat: opt-in encryption-at-rest for bundles + checkpoints (AEAD)](https://github.com/OpenAdaptAI/openadapt-flow/pull/103) (#103) — merged 

- [fix: desktop e2e targets a reliable app (repeatable structural-rung proof, not flaky Calculator)](https://github.com/OpenAdaptAI/openadapt-flow/pull/102) (#102) — merged 



## openadapt-desktop


- [fix: remove stale package version claim](https://github.com/OpenAdaptAI/openadapt-desktop/pull/15) (#15) — merged 

- [fix: keep desktop releases version-consistent](https://github.com/OpenAdaptAI/openadapt-desktop/pull/14) (#14) — merged 

- [feat: align desktop with the hosted workflow loop](https://github.com/OpenAdaptAI/openadapt-desktop/pull/13) (#13) — merged 



## openadapt-ml


- [refactor: make openadapt-ml a leaf; break ml<->evals import cycle](https://github.com/OpenAdaptAI/openadapt-ml/pull/65) (#65) — merged 



## openadapt-evals


- [fix: keep release lock metadata consistent](https://github.com/OpenAdaptAI/openadapt-evals/pull/267) (#267) — merged 

- [feat: lightweight meta-benchmark harness (unify Environment/verify + metrics; OSWorld/BrowserGym stubs for phase 2)](https://github.com/OpenAdaptAI/openadapt-evals/pull/266) (#266) — merged 

- [feat: evaluate openadapt-flow on WAA (demonstrate-then-replay + hybrid-as-agent) with cost-guarded dry-run](https://github.com/OpenAdaptAI/openadapt-evals/pull/265) (#265) — merged 

- [refactor: source Benchmark* types from openadapt-types; break ml<->evals cycle](https://github.com/OpenAdaptAI/openadapt-evals/pull/264) (#264) — merged 

- [fix: decouple oa-vm from the ML training stack via lazy package imports](https://github.com/OpenAdaptAI/openadapt-evals/pull/263) (#263) — merged 



## openadapt-capture


- [fix: importable headless (no screenshot at import) + persist pixel_ratio on the recording model](https://github.com/OpenAdaptAI/openadapt-capture/pull/24) (#24) — merged 



## openadapt-privacy


- [chore: declare privacy release line](https://github.com/OpenAdaptAI/openadapt-privacy/pull/6) (#6) — merged 

- [fix(ci): release through protected main](https://github.com/OpenAdaptAI/openadapt-privacy/pull/5) (#5) — merged 

- [fix: remove vulnerable transformer dependency from Presidio scrubber](https://github.com/OpenAdaptAI/openadapt-privacy/pull/4) (#4) — merged 



## openadapt-types


- [fix: keep release lock metadata consistent](https://github.com/OpenAdaptAI/openadapt-types/pull/6) (#6) — merged 

- [feat: add canonical Benchmark* types (Task/Observation/Action/Agent)](https://github.com/OpenAdaptAI/openadapt-types/pull/5) (#5) — merged 




