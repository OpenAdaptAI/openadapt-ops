# Guides

Task-focused, how-to guides for real deployments. Each one assumes you have
[installed OpenAdapt](../get-started/index.md) and understand the
[core concepts](../concepts/index.md).

<div class="grid cards" markdown>

-   [__Record your own app__](record-your-app.md)

    Point the recorder at your web app and compile a real workflow.

-   [__Parameters and secrets__](parameters-and-secrets.md)

    Vary values per run, and inject secrets that are never persisted.

-   [__Induce a program from multiple traces__](induce-a-program.md)

    Recover a parameterized program from several demonstrations, and run it
    over a worklist.

-   [__Write and enforce a policy__](policy-and-certification.md)

    Use `lint` and `certify` to make "runnable" distinct from "safe."

-   [__Run a deployment__](run-a-deployment.md)

    Wire a real backend, effect verification, actuation, and durability from
    one `deployment.yaml`, then run and resume it.

-   [__Run fail-closed for regulated work__](regulated-run.md)

    Every safety gate on: verify writes, refuse the unverifiable, pause and
    approve — and the compliance gate before any PHI lane.

-   [__The halt → teach loop__](halt-and-teach.md)

    Resolve a halted run: demonstrate the fix once, and `teach` compiles it
    back in — governed, so a bad fix is refused.

-   [__Desktop and Citrix__](desktop-and-citrix.md)

    Drive native Windows and pixel-only Citrix/RDP apps with the same bundle
    and run report (target state).

-   [__Choose a deployment__](deployment-models.md)

    The deployment spectrum: on-prem, BYOC-in-your-VPC, our cloud — where the
    data lives and who runs it.

-   [__Deploy on-prem__](deploy-on-prem.md)

    Keep data in the building: PHI scrubbing and the on-prem VLM appliance.

-   [__Deploy BYOC (in your VPC)__](deploy-byoc.md)

    Managed orchestration with the data plane in your own cloud account
    (target state).

-   [__The hosted option__](hosted.md)

    When a managed our-cloud deployment makes sense, and how to think about it.

-   [__Read and audit run reports__](run-reports.md)

    What the report tells you, per step, and how to audit a run.

</div>
