# Procurement FAQ

Answers for procurement, legal, and vendor-risk teams evaluating an OpenAdapt
engagement. Security depth lives in the
[security packet](security-packet.md); prices match the public
[pricing page](https://openadapt.ai/pricing).

## Commercial

**What are we actually buying in a Qualification Sprint?**
A fixed-scope engineering assessment of one workflow, from $15,000 (native,
RDP, and Citrix scopes typically $25,000 to $40,000), delivering a signed
go/no-go report, coverage matrix, and evidence pack. It is paid regardless of
outcome; "do not automate" is a full-value deliverable. See the
[Qualification Sprint one-pager](qualification-sprint.md).

**Is there a subscription?**
OpenAdapt Cloud is $500.00/month for managed browser execution of approved
workflows on non-regulated data, up to 10,000 runs/month. It is a self-service
developer and team offering, separate from enterprise qualification, and does
not include a production SLA or regulated deployment.

**What does production cost?**
Supervised Production Pilots are typically $30,000 to $60,000; production
contracts typically $48,000 to $120,000 per year depending on workflow family,
environment, runners, evidence, support, and requalification scope. OEM
embedding is typically $75,000 to $150,000 per year plus integration.

**Does the sprint fee credit toward production?**
Any production credit is stated in the customer-specific written proposal. No
credit is implied by this public documentation.

**What are the payment terms?**
The customer-specific written proposal and agreement state the payment terms.

## Licensing and lock-in

**What license is the software under?**
The engine and runtime are MIT-licensed open source, publicly auditable. The
hosted control plane is proprietary. Compiled workflow bundles and evidence
generated for you are yours.

**What happens if we stop paying?**
The MIT engine keeps running locally; you lose the commercial services around
it (managed execution, support, requalification, hosted control plane). There
is no license key that turns your local runtime off.

**Can we self-host everything?**
Yes. Fully local and air-gapped on-prem deployment shapes exist, including an
operator-verifiable no-egress posture. See
[deployment boundaries](deployment-boundaries.md).

## Security and compliance

**Are you SOC 2 certified?**
No. OpenAdapt does not hold a SOC 2 report and does not claim certification.
See the [security packet](security-packet.md).

**Will you sign a BAA / process PHI in your cloud?**
The managed cloud lane is for non-regulated data. PHI-bearing workflows run in
a customer-controlled boundary where PHI does not leave your environment; BAA
and counsel review are engagement-specific.

**Where does our data live?**
By lane: see [deployment boundaries](deployment-boundaries.md). In the
customer-controlled lanes, raw recordings, live frames, and verifier values
stay inside your boundary; only reviewed, sanitized, hash-bound derivatives
cross, and a fully local deployment sends nothing.

**How do we audit what it did?**
Every run writes a human-readable and a machine-readable report with identity
coverage, effect verdicts, heals, model calls, and halt reasons; on-prem adds
an append-only hash-chained audit log
([run reports](../guides/run-reports.md)).

## Seal, modes, and embedding

**What is a Seal?**
`ExecuteEvidenceReceiptV1`. It is the signed proof of one run. Production
`verified` requires oracle tier 2 (system of record) or 3 (counterparty
artifact). Visual/OCR (tier 0) and a second-session UI read (tier 1) never
mint a production Seal. See [The Seal](seal.md).

**Is a Seal a physician signature?**
No. The human remains the legal actor. A Seal records that the configured
identity, policy, and effect checks passed for that run.

**Do you sell attended and unattended as one product?**
No. Attended is the mode you can buy now: a person is in session, and a phone
or console answer releases each consequential write. Unattended needs a
dedicated agent identity, privileged access management, and session recording,
and it is qualified separately. One statement of work covers one mode.
OpenAdapt does not type a person's password.

**Does this need a health-system IT procurement?**
No. OpenAdapt embeds into your product through Execute and MCP, and your
company holds that integration. The health system is the environment where the
transaction runs.

**Can Copilot or Power Automate still do the click?**
Yes. OpenAdapt can emit a Seal from another actuator when asked. The
consequential MCP contract is `requires_seal: true`. Unsigned success is
failure.

## Delivery and risk

**What if the software gets it wrong silently?**
The acceptance target for silent incorrect successes (the run says done, the
system of record disagrees) is zero, contractually, per the
[acceptance matrix](acceptance-matrix.md). The mechanism is out-of-band effect
verification with halt on any non-confirmed verdict. Published bounded
qualifications to date report zero silent incorrect successes on their
fixtures ([evidence appendix](../get-started/what-works-today.md)); your
workflow's numbers come from your own qualification.

**What are the known limitations?**
Published and maintained in the engine's
[LIMITS.md](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/docs/LIMITS.md).
Identity checks cover armed steps; screen-only verification is labeled as
same-surface; qualification evidence is bounded to the exact environment it
names.

**Who are the subprocessors?**
Depends on the lane. A fully local deployment has none in the run path. For
hosted lanes, request the current subprocessor list directly.

**What support and requalification do we get?**
Defined per production contract: support channel and response targets,
requalification triggers (application upgrades, drift past healing coverage),
and evidence refresh. The pilot's acceptance report sets the operational
baseline.

**Insurance, indemnity, liability?**
Per the governing agreement; request current certificates and terms directly.
This documentation does not create contractual terms.
