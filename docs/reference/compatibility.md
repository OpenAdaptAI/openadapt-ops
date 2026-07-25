# Versions and compatibility

Most users install one product package:

```bash
pip install openadapt
openadapt flow --help
```

`openadapt` is the launcher and unified CLI. Its dependency metadata selects a
compatible `openadapt-flow`, the canonical compiler and runtime. Installing the
engine package directly is supported for contributors and embedders, but it is
not a separate product onboarding path.

## Current compatibility contract

| Component | Compatible range | Role |
|---|---|---|
| `openadapt` 1.x | `openadapt-flow >=1.7,<2` | Public installer and `openadapt flow …` CLI |
| `openadapt-flow` 1.x + native capture | `openadapt-capture >=1.1.0` | Canonical native demonstration recording for Windows, macOS, Linux, RDP, and Citrix |
| Windows action-time UIA handoff | `openadapt-flow >=1.22,<2` + `openadapt-capture >=1.1.0` | Retains the nearest actionable UIA node for native Windows compilation; RDP and Citrix remain externally black-box |
| `openadapt-flow` 1.x + privacy extra | `openadapt-privacy[presidio] >=1.0` | Configured local scrub/redaction paths |
| `openadapt-flow` interoperability extra | `openadapt-types >=0.2,<0.4` | Contributor-facing schema boundary |
| Python | 3.10-3.12 | Supported runtime range for the current 1.x line |

The package metadata is the executable source of truth for these ranges. CI
installs the real optional packages at the bounded edges used by the engine,
and release archives are validated before publication.

## Version policy

- Public launcher and engine APIs follow semantic versioning. Breaking CLI,
  bundle, or runtime-contract changes are reserved for a major release.
- Optional 0.x schema packages may break at a minor release, so the engine pins
  an upper bound and raises it only after its interoperability suite passes.
- Patch releases may ship immediately for security, safety, packaging, or
  installation defects. Routine capability changes should be consolidated so
  adopters see product releases rather than repository-level merge noise.
- The supported open-source line is the latest stable 1.x launcher and a
  compatible 1.x engine. Production deployments should pin the exact versions
  that passed their workflow qualification, then rerun that qualification
  before an upgrade.

Release history is filtered into the product [changelog](../changelog.md).
Workflow-specific deployment records should additionally retain the exact
launcher, engine, backend, policy, and bundle versions used for each accepted
run.

## Upgrade workflow

```bash
python -m pip install --upgrade openadapt
openadapt flow --version
openadapt flow lint bundle
openadapt flow certify bundle --config deployment.yaml
openadapt flow run bundle --config deployment.yaml --dry-run
```

Promote an upgrade only after the same task, environment, identity/effect
oracles, and refusal cases used for the original workflow qualification pass.
