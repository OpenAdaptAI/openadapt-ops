# Reference

Exact descriptions of the command line, run results, the deployable artifact,
and configuration. The canonical engine is `openadapt-flow`, installed with
the `openadapt` package and run as `openadapt flow`.

| Page | What it describes |
|---|---|
| [openadapt flow CLI](cli.md) | Every verb and its key flags: record, compile, replay, lint, certify, and the rest. |
| [Run outcomes and halt reasons](run-outcomes.md) | Every execution outcome, transaction outcome, effect-verifier verdict, halt reason, hosted Execute state, and CLI exit code. |
| [The bundle format](bundle-format.md) | What a compiled workflow bundle contains, and schema v2's manifest, digest, and load-time validation. |
| [Deployment configuration](deployment-config.md) | The `deployment.yaml` schema that wires backend, effects, actuation, durability, and policy in one file. |
| [Configuration and env vars](configuration.md) | Secrets, scrubbing, the VLM appliance, and auto-install controls. |
| [Backends, where it runs](../concepts/backends.md) | Browser, native Windows, native macOS, native Linux, RDP, and Citrix/VDI behind one backend protocol, with each one's status. |
| [Integrate OpenAdapt Execute](../commercial/execute-api.md) | The Execute request, poll, Seal-shaped receipt, and webhook contract for approved private-pilot partners. |
| [Versions and compatibility](compatibility.md) | The public install identity, tested component ranges, version policy, and upgrade qualification. |
| [Glossary](glossary.md) | The canonical definitions of OpenAdapt terms, including qualify, certify, certification policy, and admission. |
| [What's New](../whats-new.md) and [Changelog](../changelog.md) | Recent product changes and the aggregated release history. |

The package and repository catalog, the documentation source of truth, and the
technical paper are under [Contributing & research](../contributing/index.md).
