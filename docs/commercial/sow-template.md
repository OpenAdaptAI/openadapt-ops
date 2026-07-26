# Statement of Work template: Workflow Qualification Sprint

Template for the fixed-scope sprint described in the
[one-pager](qualification-sprint.md). Bracketed fields are filled per
engagement. This template is a starting structure, not legal advice.
**[LEGAL REVIEW REQUIRED]** before first use.

---

## 1. Parties and effective date

- Provider: MLDSAI Inc. (OpenAdapt) [entity details]
- Customer: [legal name, address]
- Effective date: [date]
- Governing agreement: [MSA / mutual NDA reference, or standalone terms]

## 2. Scope

Provider will qualify exactly one workflow:

- Workflow name and business purpose: [description]
- Target application and version: [application, version, tenant]
- Execution substrate: [browser / Windows native / macOS / Linux / RDP /
  Citrix]
- Environment: [test / sandbox / customer-controlled production boundary]
- Business effect to verify and its system of record: [effect, read path]
- In scope: suitability assessment, qualified prototype, identity and
  effect-verification contract, failure and exception analysis, deployment
  analysis, ROI model, signed go/no-go report.
- Out of scope: production writes without written authorization, changes to the
  target application, additional workflows or environments, compliance
  certification, ongoing operation.

## 3. Timeline

- Target duration: ten business days of engineering work from clock start,
  typically two to four weeks elapsed including access setup and review.
- Clock start: the first business day on which SOW signature, verified
  application access, representative test data, and named contacts are all
  confirmed in writing (see Section 5).
- Clock pause: days on which required access or data is unavailable.
- Checkpoints: kickoff [date], midpoint findings review [date], final
  walkthrough [date].

## 4. Responsibilities (RACI)

| Activity | Provider | Customer |
|---|---|---|
| Demonstrate the workflow end to end | C | R/A |
| Provide application access and test data | C | R/A |
| Record, compile, and qualify the workflow | R/A | C/I |
| Author identity and effect contracts | R/A | C |
| Provide the verification read path | C | R/A |
| Seed and adjudicate fault cases | R | C/A |
| Security and data-boundary review | C | R/A |
| Go/no-go recommendation | R/A | C/I |
| Acceptance of deliverables | C | R/A |

R = responsible, A = accountable, C = consulted, I = informed.

## 5. Access prerequisites

Customer provides before clock start (full list in the
[scope and prerequisite checklist](scope-checklist.md)):

- [ ] Named workflow owner able to demonstrate the workflow.
- [ ] Working credentials for the target application in the agreed environment.
- [ ] Representative test data safe to create, modify, and delete.
- [ ] Verifier read path (API credentials, database read access, report export,
      or read-only session).
- [ ] Security contact and any required access approvals.

## 6. Data boundary

- Execution location: [customer workstation / customer VM / customer cloud /
  OpenAdapt-managed browser runner (non-regulated data only)].
- Sensitive data (including any PHI/PII) remains inside the customer-controlled
  boundary; artifacts cross a boundary only as reviewed, sanitized derivatives
  per the [deployment boundaries](deployment-boundaries.md) page.
- Recordings, bundles, and evidence storage location and retention: [location,
  retention period, deletion at termination yes/no].
- Model usage: healthy replay makes no model calls; any compilation or repair
  model endpoint is [named endpoint / none / customer-approved].
- Credentials are never stored in artifacts; secret fields are injected at run
  time from the customer's environment.

## 7. Deliverables

1. Qualification report per the
   [qualification report outline](qualification-report-outline.md).
2. Coverage matrix (identity arming, effect contracts, verification strength,
   gaps).
3. Signed go/no-go decision with boundary and requalification triggers.
4. Evidence pack: run reports, fault-case results, hashes, and (on "go") the
   qualified prototype bundle.

## 8. Acceptance

- Deliverables are accepted at the final walkthrough unless Customer identifies
  a material gap against Sections 2 and 7 in writing within [5] business days.
- A "no-go" recommendation is a complete, accepted deliverable. The sprint fee
  is not contingent on a "go" outcome.
- Acceptance of the sprint does not constitute acceptance of any production
  deployment; production acceptance uses the
  [acceptance matrix](acceptance-matrix.md) under a separate pilot SOW.

## 9. Fees and payment

- Fixed fee: $[15,000+ per scope; native/RDP/Citrix typically $25,000 to
  $40,000].
- Invoicing: [50% at signature, 50% at delivery / net terms].
- Expenses: none without prior written approval.
- Conversion credit: [X]% of the sprint fee credits toward the first production
  year if executed within [N] months. Percentage **[FOUNDER TO CONFIRM]**.

## 10. No-go and termination

- Early no-go: if Provider concludes before day ten that automation should not
  proceed, Provider delivers the report early; the fixed fee stands.
- Blocked access: if prerequisites remain unmet [15] business days after
  signature, either party may terminate; work performed is invoiced pro rata
  against the fixed fee.
- Termination for convenience by Customer: fee for work performed plus
  deliverables completed to date.
- Confidentiality, IP in pre-existing materials, and liability terms per the
  governing agreement. **[LEGAL REVIEW REQUIRED]**

---

Signatures: [Provider] / [Customer], name, title, date.
