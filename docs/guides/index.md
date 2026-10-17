# How-to guides

Step-by-step guides for one task each. They assume you have
[installed OpenAdapt](../get-started/index.md). The
[concepts](../concepts/index.md) explain why each step exists.

## Record and compile

| Guide | What you do |
|---|---|
| [Record your own app](record-your-app.md) | Point the recorder at your web app and compile a real workflow. |
| [Recording on Windows, RDP and Citrix](record-windows-rdp-citrix.md) | Let a person or an agent show the task in a native Windows app or a remote session, using the Windows agent server and its token. |
| [Induce a program from multiple traces](induce-a-program.md) | Recover a parameterized program from several demonstrations. |
| [Run a workflow for each record](data-driven-loops.md) | Bind a worklist to a loop and run every record with its gates. |
| [A task that spans two apps](compose-multi-application.md) | Record one program per surface, sequence them with `compose`, then author a process parent after admission. |
| [Parameters and secrets](parameters-and-secrets.md) | Vary values per run, and inject secrets that are never persisted. |

## Qualify and certify

| Guide | What you do |
|---|---|
| [Write and enforce a policy](policy-and-certification.md) | Use `lint` to find gaps and `certify` to refuse a bundle that violates the policy. |
| [Qualify a workflow](qualify-a-workflow.md) | Review the graph, bind identity and effects, run representative and fault cases, certify, and publish one exact version. |

## Run and operate

| Guide | What you do |
|---|---|
| [Run a deployment](run-a-deployment.md) | Wire a backend, effect verification, actuation, and durability from one `deployment.yaml`, then run and resume. |
| [Read and audit run reports](run-reports.md) | Read what the report says per step, and audit a run. |
| [Workflow catalog and halt map](workflow-catalog.md) | See which workflows exist and where each one stops. |
| [Deploy on-prem](deploy-on-prem.md) | Keep runtime data in your network, with PHI/PII scrubbing and the on-prem VLM appliance. |
| [The hosted option](hosted.md) | Use the managed browser subscription, and sanitize and review artifacts before they leave. |
| [Connect to a cloud workspace](../desktop/connect-to-cloud.md) | Sign in from Desktop and push a recording to your workspace. |
| [Troubleshooting](troubleshooting.md) | Fix blank capture, over-halting, a stuck queue, and the Windows session-0 case. |

Security reviews, data handling, and account security are under
[Security & procurement](security-review.md).
