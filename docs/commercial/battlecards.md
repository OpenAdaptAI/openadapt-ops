# Competitive battlecards

Positioning against the four alternatives a buyer actually weighs. Same rules
as the public [comparison page](https://openadapt.ai/compare): credit real
strengths, recommend the alternative when it fits better, and differentiate
only on what OpenAdapt genuinely does differently: verification against the
system of record, transaction outcomes, the external no-install lane,
customer-controlled data, and an open MIT runtime.

One rule above all: **if a direct API exists for the task, say so and lose the
deal gracefully.** An API beats GUI automation of any kind.

## UiPath (and enterprise RPA generally)

**Where they are genuinely strong.** Mature platform: hundreds of packaged
connectors, orchestration, scheduling, credential vaults, governance tooling,
a large partner and talent ecosystem, and years of enterprise deployments.
For broad multi-application automation programs with dedicated CoE staffing,
RPA platforms are a defensible default.

**Where OpenAdapt differs.**

- **Verification, not just execution.** RPA success typically means the
  selector matched and the click landed. OpenAdapt verifies the business
  effect out of band against the system of record and halts on any
  non-confirmed verdict; the acceptance target for silent incorrect successes
  is zero, in the contract.
- **Demonstration, not development.** A workflow is recorded from a human
  demonstration and compiled, rather than built and maintained as a bot
  project by RPA developers.
- **External no-install lane.** OpenAdapt drives Citrix/RDP externally through
  pixels with nothing installed in the session
  ([brief](citrix-external-brief.md)). RPA vendors also offer computer-vision
  automation for Citrix; the difference is the fail-closed identity and
  effect-verification contract wrapped around it, not the pixels themselves.
- **Open runtime, customer-controlled data.** MIT engine, local-first
  execution, no per-bot licensing meter on your own hardware.

**When to concede.** Large-scale orchestration across dozens of workflows,
deep packaged-connector needs, or an established CoE standardized on the
platform.

**Buyer question to plant.** "When the bot reports success, what read of the
system of record backs that up, and what happens when they disagree?"

## Microsoft Power Automate

**Where they are genuinely strong.** Unbeatable distribution and price inside
Microsoft 365: cloud flows, deep Office/Teams/Dataverse integration, licensing
most enterprises already own, and a citizen-developer model IT already
tolerates. For API-connected flows in the Microsoft ecosystem it is usually
the right answer, and we say so.

**Where OpenAdapt differs.**

- **The workflows Power Automate reaches worst.** Desktop flows (RPA) on
  legacy, non-Microsoft, or Citrix-published applications are where attended
  selectors get brittle. That GUI-only remainder is OpenAdapt's entire focus.
- **Transaction outcomes.** A flow that ran is not a verified effect.
  OpenAdapt returns verified/halted outcomes with evidence, designed for
  consequential writes.
- **Customer-controlled and air-gapped shapes.** Regulated execution without
  routing through a shared cloud, with an operator-verifiable no-egress
  posture.

**When to concede.** The task has a connector or API path in the Microsoft
graph; anything cloud-flow shaped.

**Buyer question to plant.** "For the desktop flows on your legacy or Citrix
apps: who maintains the selectors, and what verifies the write actually
landed?"

## Computer-use agents (LLM-driven GUI agents)

**Where they are genuinely strong.** Novel, exploratory, one-off tasks with no
prior demonstration; natural-language task specification; improving fast.
For "figure out how to do this thing I have never scripted," an agent is the
right tool and we recommend one.

**Where OpenAdapt differs.**

- **Determinism on the repeat path.** A compiled workflow replays
  deterministically with zero model calls on the healthy path: no
  per-run token spend, no stochastic variation on run 4,000. Model spend is
  reserved for compilation and governed repair.
- **Fail-closed rather than best-effort.** Agents are optimized to complete
  the task; OpenAdapt is optimized to refuse when identity, postconditions, or
  effects cannot verify. For consequential writes, halting is the cheap
  direction to be wrong.
- **Auditability.** Every step records its resolution, identity check, effect
  verdict, and any model call; evidence is hash-bound. Agent traces are
  improving but are not verification.
- **Published honest benchmark.** The public comparison measures repeat cost
  and latency on one bundled task with the caveats stated; we do not claim
  general agent-benchmark superiority.

**When to concede.** Truly novel or constantly varying tasks, low-consequence
work, research and exploration.

**Buyer question to plant.** "What is the agent's silent wrong-action rate on
your workflow, measured against the system of record rather than its own
self-report?"

## Scripts and browser recorders (Playwright, Selenium, macro tools)

**Where they are genuinely strong.** Free or cheap, fully controlled,
excellent for developers on stable web apps; Playwright in particular is a
superb engineering tool. A capable developer with a stable DOM and time to
maintain the script needs nothing else.

**Where OpenAdapt differs.**

- **Maintenance is the product.** Scripts encode selectors by hand and break
  silently or loudly with UI drift; OpenAdapt compiles from demonstration,
  heals benign drift deterministically with the heal recorded for review, and
  halts on severe drift.
- **No DOM required.** Native desktop, RDP, and Citrix surfaces where
  Playwright and Selenium do not reach.
- **Verification and governance built in.** Identity gates, effect contracts,
  fail-closed admission, and audit evidence are engine features, not per-team
  disciplines that erode under deadline pressure.
- **Complement, not only competitor.** The external-executor design lets a
  customer-controlled script perform an action while OpenAdapt's
  authorization, verification, and evidence stay authoritative
  ([OEM brief](oem-brief.md)).

**When to concede.** Stable web app, engineering team owns it, low consequence
of a wrong write, no audit requirement.

**Buyer question to plant.** "Who is on the hook when the script clicks the
wrong patient, and how would you find out it happened?"
