---
description: >-
  Run a certified workflow under a named profile, choose how saves are
  approved, and pause and resume long runs.
---

# Run a workflow

`openadapt flow replay` is for rehearsal: it runs every step, never checks
the record, and ends `COMPLETED_UNVERIFIED` at best. `openadapt flow run` is
the governed path. Before the first step it checks the program against its
policy and, under the Standard and Regulated profiles, its seal and
production admission. It refuses to start when a check fails.

## 1. Write a deployment file

Draft a deployment file bound to the bundle, then fill in every field listed
under `unresolved`:

```bash
python -m openadapt_flow.cli_config init bundle --out deploy.yaml
```

`certify` and `run` refuse the draft until `unresolved` is empty. The fields
are described in [Configuration](../reference/configuration.md). Don't put
secret values in the file; it takes environment variable names.

## 2. Choose a profile

| Profile | Use it for | What it requires | Best result |
|---|---|---|---|
| `demo` | Trying things out | A bundle. Screen evidence is allowed. | `COMPLETED_UNVERIFIED` |
| `standard` | Production inside a qualified, encrypted storage boundary | Certification, a sealed program, durable checkpoints, a right-record check on every save, a record check that doesn't go through the acting session, and a production admission | `VERIFIED` |
| `regulated` | Production with regulated data, such as patient records | Everything in Standard, plus an encrypted program (`OPENADAPT_BUNDLE_KEY`), sealed evidence files, and encrypted checkpoints, in a deployment you control | `VERIFIED` |

Flags can make a profile stricter but never weaker. Select the profile with
`--profile` or `runtime.profile` in the deployment file.

```bash
openadapt flow certify bundle --config deploy.yaml
openadapt flow run bundle --profile standard --config deploy.yaml \
  --qualification-authority-file /secure/admission.json
```

## 3. Choose how saves are approved

Each run has an approval mode. It decides whether the run waits for an
answer before each save.

| Mode | Before each save |
|---|---|
| `each_item` | The run waits until a person approves that save in OpenAdapt Desktop, then saves exactly what the person saw. |
| `problems_only` | Only problems go to a person. This mode isn't available to customers yet: until it is configured, every save still asks. |
| `not_gated` | No pause. The run report records that the run wasn't gated. |

`openadapt flow run` uses `each_item` unless `--approval-mode` or
`runtime.approval_mode` names another mode. The MCP server passes the mode its
operator set with `serve --approval-mode`; callers can't change it. Runs that
OpenAdapt Cloud dispatches pass `not_gated` explicitly, and their reports say
so. A run that waits
longer than `--approval-wait` (default 900 seconds, at most 14,400) stops
before the save.

## 4. Read the result

`run` prints a one-line result and writes `REPORT.md` and `report.json` to
the run directory. The outcome in `report.json` is one of the values in
[Run outcomes](../reference/outcomes.md).

| Exit code | Meaning |
|---|---|
| 0 | Under Standard or Regulated, the run ended `VERIFIED`. Under Demo, the steps finished. |
| 1 | The run started and didn't end as above: it stopped, needs a record checked, or failed. |
| 2 | The run was refused before any step ran, for example for a missing admission or a failed policy check. |

Under Demo, exit 0 doesn't mean the save was checked. Read
`transaction_outcome` in `report.json`.

For a plain-language account of any run:

```bash
openadapt flow explain runs/<run-dir>
```

To check a run before it touches anything, add `--dry-run`. It prints which
gates pass and exits without running.

## Pause and resume long runs

With `--durable` (on by default under Standard and Regulated), the run
checkpoints each confirmed step. When it stops, it pauses instead of ending,
and writes the reason to `pending_escalation.json`.

```bash
openadapt flow approve runs/<run-dir> --approver "jane@clinic.example"
openadapt flow resume runs/<run-dir> --require-approval
```

`resume` never performs a confirmed save again. It keeps the run's own
approval mode. A run that ended `RECONCILIATION_REQUIRED` isn't retried by an
ordinary approval: after a person checks the record, `approve
--authorize-uncertain-retry` allows one retry of the uncertain step.

## Run in a browser you're already signed in to

Start Chromium with remote debugging and pass its local endpoint:

```bash
openadapt flow run bundle --browser-cdp-endpoint http://127.0.0.1:9222 \
  --url https://app.example.org ...
```

The run uses the one open tab on that origin, starts from the screen it
shows, and never navigates or closes the browser. Open the task's first
screen before each run.

## Run on a desktop or remote surface

Pass the same surface options you recorded with, for example
`--backend macos --macos-app TextEdit`, `--backend windows --agent-url
http://localhost:5001`, or `--backend citrix`. A governed Citrix run also
needs `--rdp-readiness-text`, a stable text that must be visible in the
remote frame before any input.
