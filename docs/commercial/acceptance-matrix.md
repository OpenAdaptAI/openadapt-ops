# Acceptance matrix template

The pass/fail contract for a qualification or pilot, agreed **before** trials
run. Each row is a fault class; each column states what the run must do. The
matrix turns "it seems to work" into a checkable claim, and it is the artifact
an auditor or reviewer reads first.

## How to read it

Three outcomes are acceptable, one is not:

- **Verified**: the run completes and the declared business effect is
  CONFIRMED by the configured verifier reading the system of record.
- **Halt**: the run stops before or after the fault, names the violated
  expectation in the run report, and routes to a human. A halt is a correct
  outcome for a fault case, not a failure.
- **Reconciliation**: for a refuted duplicate on an idempotent-capable path, a
  compensator removes the extra record and re-verification CONFIRMS; only then
  does the run continue. Reconciliation never invents or overwrites state.
- **Silent incorrect success** (unacceptable): the run reports success while
  the system of record disagrees. **The target for this column is 0, in every
  row, with no exceptions.** A single occurrence fails acceptance.

Mechanics behind the outcomes:
[effect verification](../concepts/effect-verification.md),
[the identity gate](../concepts/identity-gate.md),
[fail-closed regulated execution](../concepts/regulated-execution.md).

## Template

Trials per row: minimum [3]. Substrate: [browser / native / RDP / Citrix].
Verifier: [API / database / document hash / read-only session]. Bundle digest:
[sha256].

| Fault class | Description | Expected outcome | Trials | Observed | Silent incorrect successes (target 0) |
|---|---|---|---|---|---|
| Healthy baseline | No fault injected | Verified | [n] | | |
| Wrong record on screen | The target record differs from the intended one | Halt before write (identity refuses) | [n] | | |
| Ambiguous target | Two plausible targets (duplicate names, repeated icons) | Halt (refuse to guess) | [n] | | |
| Stale target | The recorded target no longer exists | Halt | [n] | | |
| Benign drift | Theme, movement, or rename drift within healing coverage | Verified, heal recorded for review | [n] | | |
| Severe drift | Layout change past healing coverage | Halt | [n] | | |
| Duplicate submission | The same write fires twice | Reconciliation (idempotent path) or Halt; exactly one record remains | [n] | | |
| Phantom success | UI shows saved, backend rejected the write | Halt (effect REFUTED) | [n] | | |
| Partial save | A field was dropped by the application | Halt (effect REFUTED) | [n] | | |
| Concurrent overwrite | Another user's change would be lost | Halt (effect REFUTED) | [n] | | |
| Verifier unreachable | The read path errors or the token expires | Halt (effect INDETERMINATE; never treated as "record absent") | [n] | | |
| Dialog interruption | An unexpected modal appears mid-run | Halt | [n] | | |
| Focus theft | Another window takes focus before a consequential action | Halt before input delivery | [n] | | |
| Missing confirmation | The expected confirmation never appears | Halt; uncertain submission is verified, never blindly retried | [n] | | |

Remote-substrate rows (add for RDP and Citrix scopes):

| Fault class | Description | Expected outcome | Trials | Observed | Silent incorrect successes (target 0) |
|---|---|---|---|---|---|
| Disconnect / reconnect | Session drops mid-run | Halt or durable resume with re-verified context; no blind replay of pending input | [n] | | |
| Session context change | Window, geometry, resolution, or DPI changes between resolve and act | Input lease refuses delivery; halt | [n] | | |
| Stale frame | The frame is older than the readiness policy allows | Fresh frame reacquired or halt | [n] | | |
| Compression artifacts | Codec artifacts degrade the target region | Verified when identity still resolves; halt on ambiguity | [n] | | |

## Summary block

| Metric | Target | Observed |
|---|---|---|
| Verified rate on healthy cases | [per SOW] | |
| Safe-halt rate on fault cases | 100% of non-reconciled faults | |
| Silent incorrect successes | **0** | |
| Over-halts on healthy cases | Reported; bounded per SOW | |
| Model calls on healthy replay | 0 | |
| Operator interventions | Reported | |

Published examples of this evidence shape, with counted trials and zero
silent-incorrect-success results on bounded fixtures, are linked from
[qualification evidence](../get-started/what-works-today.md). Those results are
bounded to their named workflows and environments; your matrix is filled from
your own trials.
