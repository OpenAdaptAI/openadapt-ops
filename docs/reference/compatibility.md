---
description: >-
  Which package versions work together, the supported Python versions, and
  how versions change.
---

# Versions and compatibility

Most people install one package, `openadapt`. Its metadata picks compatible
versions of the engine and the MCP server:

```bash
python -m pip install --upgrade openadapt
openadapt version
```

## Current compatibility contract

These are the ranges the newest `openadapt` and `openadapt-flow` releases on
PyPI require. A daily check compares this table with that metadata.

| Component | Compatible range | Role |
|---|---|---|
| `openadapt` 1.x | `openadapt-flow >=2.0.0,<3` | The `openadapt` command and its `openadapt flow` commands |
| `openadapt` 1.x | `openadapt-agent >=2.1.0,<3` | The `openadapt agent` commands and the MCP server |
| `openadapt-flow` 2.x with desktop recording | `openadapt-capture >=1.2.0,<2` | Recording on Windows, macOS, Linux, RDP, and Citrix |
| Windows control details at recording time | `openadapt-flow >=2.0.0,<3` + `openadapt-capture >=1.2.0,<2` | Keeps the UI Automation details of each clicked control for native Windows apps |
| `openadapt-flow` 2.x with the `privacy` extra | `openadapt-privacy[presidio] >=1.0` | Local scrubbing and redaction |
| `openadapt-flow` 2.x and its interop, console, execute, and reward extras | `openadapt-types >=0.18,<0.19` | Shared data models, including the Execute request, status, webhook, and receipt |
| Python | 3.10-3.12 | Supported runtime range |

On Python 3.13 and later, `pip install openadapt` installs only the launcher,
because the engine and the MCP server require Python 3.12 or earlier. Use a
3.12 environment or `uvx --python 3.12 openadapt`.

## Version policy

- The launcher and engine follow semantic versioning. Breaking changes to the
  commands, the bundle format, or run contracts wait for a major release.
- 0.x schema packages such as `openadapt-types` may break at a minor
  release. Each package that uses one pins the exact minor version it tests,
  so the newest `openadapt-types` can be ahead of the range above. Install the
  range Flow names.
- Patch releases can ship at any time for security, safety, or installation
  fixes.
- Pin the exact versions a workflow was qualified on in production, and
  qualify again before an upgrade.

Release history is in the [changelog](../changelog.md).
