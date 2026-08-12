# Qwen grounder endpoint — verification results

Status: **NOT DEPLOYED — blocked on the auth secret.**

Preflight on 2026-08-12 found Modal auth present (`~/.modal.toml`, profile
`abrichr`) but no Modal secret named `qwen-endpoint-token`. Per policy the
agent does not create or handle the token; the founder command is in
`RUNBOOK.md` section 0 (and in `NEEDS_YOU.md`). Once the secret exists, run
RUNBOOK sections 1–2 and fill this file in.

## Endpoint

| What | Value |
|---|---|
| Deployed | no (pending secret) |
| Model | `Qwen/Qwen2.5-VL-7B-Instruct` @ `cc594898137f460bfe9f0759e9844b3ce807cfb5`, bf16 (no quantization) |
| GPU | A10G 24 GB |
| Cold-start latency | _(measure: RUNBOOK 2.2)_ |
| Warm request latency | _(measure: RUNBOOK 2.3)_ |
| Unauthed request | _(expect 401: RUNBOOK 2.1)_ |
| Scaled to zero after idle | _(expect yes: RUNBOOK 2.4)_ |
| Verification GPU spend | _(cap $5.00; expected ~$0.20–0.30)_ |

## Grounder smoke (5 requests, 2 committed flow fixtures)

Produced by `smoke_grounder.py` through openadapt-flow's real
`OpenAICompatibleGrounder`. Fixtures: `benchmark/dense_surface/
record_seed1.png` (2240x3702) and `benchmark/dense_surface/
replay_native_arial_seed1.png` (1120x1858) from the openadapt-flow repo.

| fixture | intent | verdict | point | latency_s | est_cost_usd |
|---|---|---|---|---|---|
| _(pending deploy)_ | | | | | |

Summary: _(hit / miss / abstain counts, median latency, cost per request)_

Interpretation notes, fixed in advance:

* This is a smoke (wire works end-to-end), not an accuracy claim. The full
  accuracy probe runs against Together in a sibling effort — compare cost
  and hit rate there before choosing a default grounding backend.
* Qwen VL models answer in the coordinate frame of the server-side
  (possibly resized) image; a systematic offset on the hi-dpi fixture is
  recorded as `miss`, not tuned away.
* `abstain` (grounder returns None) is the fail-safe path working: any
  transport error, non-200, or `{"x": null}` reply must halt the ladder,
  never click.
