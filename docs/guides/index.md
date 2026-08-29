# Guides

How-to guides for real deployments. Each assumes you have
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

-   [__Sequence work across two applications__](compose-multi-application.md)

    Record one program per surface, sequence the compiled recordings with
    `compose`, then after admission author a ProcessContract parent. The
    parent graph shows two child nodes and the handoff.

-   [__Write and enforce a policy__](policy-and-certification.md)

    Use `lint` to find gaps and `certify` to refuse a bundle that violates the
    selected policy.

-   [__Qualify a workflow__](qualify-a-workflow.md)

    Review the graph and risk, bind identity and effects, run representative
    and fault cases, certify, seal, export, and deploy from Desktop or CLI.

-   [__Run a deployment__](run-a-deployment.md)

    Wire a real backend, effect verification, actuation, and durability from
    one `deployment.yaml`, then run and resume it.

-   [__Deploy on-prem__](deploy-on-prem.md)

    Keep data in the building: PHI/PII scrubbing and the on-prem VLM appliance.

-   [__The hosted option__](hosted.md)

    Review the managed subscription lifecycle, sanitize and review artifacts,
    run browser workflows, and understand trusted execution boundaries.

-   [__Security and data handling__](security-and-data-handling.md)

    Review the local data flow, PHI/PII boundary, secrets, verification,
    audit evidence, and IT questions.

-   [__Security and deployment review__](security-review.md)

    Data boundaries, secrets, audit integrity, encryption, updates, and the
    enterprise review checklist.

-   [__Read and audit run reports__](run-reports.md)

    What the report tells you, per step, and how to audit a run.

</div>
