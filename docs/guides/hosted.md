# The hosted option

OpenAdapt is open source and designed to run [on your own
infrastructure](deploy-on-prem.md). That is the default and, for regulated data,
usually the right choice. A hosted, managed deployment is an option for teams
that would rather not operate the stack themselves.

## When self-hosting is the right call

- Your data cannot leave your environment (PHI, PII, contractual data
  residency).
- You already run the infrastructure and want full control of the model tiers.
- You want the deterministic replay path with no external dependency at all.

Everything OpenAdapt does on the healthy replay path runs locally with zero model
calls, so self-hosting has no functional penalty. See
[Deploy on-prem](deploy-on-prem.md).

## When a managed deployment helps

A managed deployment can make sense when a team wants the outcome (compiled,
governed workflows) without standing up and maintaining the recording,
compilation, and appliance infrastructure themselves, and when the data policy
permits a managed environment. The engine, bundle format, and CLI are identical;
what changes is who operates them.

## How to think about it

The unit of value is the same either way: a compiled workflow that replays
deterministically, verifies effects, and halts rather than guesses. Pricing for
managed deployments is engagement-based rather than per-run or per-seat, because
the whole point of the compiler is that a run costs $0.

To discuss a hosted or pilot deployment, reach the team via
[openadapt.ai](https://openadapt.ai) or the
[GitHub organization](https://github.com/OpenAdaptAI).
