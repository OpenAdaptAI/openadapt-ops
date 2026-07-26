# ROI worksheet

A worksheet for building the economic case with the buyer's own numbers. It
deliberately uses conservative defaults and no invented case data. Fill it in
during qualification scoping; the completed version becomes Section 8 of the
[qualification report](qualification-report-outline.md).

## The formula

```text
Gross monthly savings = runs/month x minutes saved per run / 60 x loaded hourly rate

Net annual value     = (gross monthly savings - monthly operating cost) x 12
                       + recovered value (if the workflow finds money, not just time)
                       - first-year platform and qualification cost
```

## Inputs

| Input | Definition | Conservative guidance |
|---|---|---|
| Runs per month | Actual executions of this workflow, from logs or the operator, not an aspiration. | Use last quarter's average, not the peak month. |
| Minutes saved per run | Manual handle time minus residual human time (review, halt handling). | Time the operator doing it live; subtract 10 to 20% for residual review. |
| Loaded hourly rate | Fully loaded cost of the person doing it today (salary + benefits + overhead). | Use your finance team's loaded rate, not base salary alone. |
| Intervention rate | Fraction of runs expected to halt for a human. | Until your own pilot measures it, budget several percent; halts are a designed outcome, not free. |
| Minutes per intervention | Human time to review a halt and resolve it. | Include context-switch cost; 5 to 15 minutes is typical for a routed halt. |
| Recovered value | Money the workflow finds (missed billables, avoided penalties), separate from labor time. | Only count identified-and-actioned value; see the caveat below. |
| Platform cost | The relevant rung of the [offer ladder](index.md): Cloud at $500/month, or the pilot/production contract. | Use the real quote, not the floor price. |
| Qualification cost | The sprint fee (from $15,000; native/RDP/Citrix typically $25,000 to $40,000). | First-year only; a portion credits toward production, percentage [FOUNDER TO CONFIRM]. |

## Worked structure (fill with your numbers)

```text
A. Runs per month                     = ________
B. Minutes saved per run              = ________
C. Loaded hourly rate ($/h)           = ________
D. Gross monthly savings              = A x B / 60 x C          = ________
E. Intervention cost per month        = A x rate x min/60 x C   = ________
F. Platform cost per month            = ________
G. Net monthly value                  = D - E - F               = ________
H. Recovered value per year (if any)  = ________
I. First-year one-time cost           = sprint (+ pilot)        = ________
J. First-year net value               = G x 12 + H - I          = ________
K. Payback (months)                   = I / G                   = ________
```

A workflow that cannot clear a conservative version of this worksheet is a
[no-go criterion](qualification-sprint.md#no-go-criteria), and the sprint
report will say so.

## What "recovered value" must mean

If the workflow identifies money (for example missed billables), count it as
recovered only at the point your own process actually actions it. Identified
is not submitted, submitted is not approved, approved is not collected. State
which point your number measures.

## A real reference point, with its caveat

The published
[RVU audit case study](https://openadapt.ai/customers/rvu-audit-heart-care)
(a US cardiology electrophysiology practice, customer-controlled Windows
deployment) reports preliminary steady-state figures: roughly 480 governed
runs per month, about 5 hours of manual audit work saved monthly, an estimated
$75,000 per year in recoverable billables **identified** (not booked), a 99.2%
verified rate, 3 halts routed to a human per month, and 0 silent incorrect
successes. **Those figures are preliminary and under review pending final
customer confirmation**, and "recovered" there means identified and queued,
not collected. Use them as an existence proof of the worksheet's shape, not as
your expected result; your numbers come from your own qualification and pilot.
