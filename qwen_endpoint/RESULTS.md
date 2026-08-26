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
| record_seed1.png | Click Open in the row for patient Halloran, Karen (MRN MG584224) | hit | (2069, 197) | 26.75 | 0.0155 |
| record_seed1.png | Click Open in the row for patient Delgado, Edward (MRN MG901312) | hit | (2068, 1470) | 1.33 | 0.0077 |
| record_seed1.png | Click Open in the row for patient Kowalski, Maria (MRN RC571054) | hit | (2086, 3294) | 1.37 | 0.0078 |
| replay_native_arial_seed1.png | Click Open in the row for patient Ferreira, Susan (MRN PT994939) | miss | (806, 107) | 2.09 | 0.0080 |
| replay_native_arial_seed1.png | Click Open in the row for patient Whitfield, Philip (MRN PT560165) | miss | (879, 2345) | 1.01 | 0.0076 |

Summary: 5 requests: 3 hit / 2 miss / 0 abstain; latency median 1.37 s
(min 1.01 s, max 26.75 s incl. one cold engine warm-up); burst GPU cost
incl. one 120 s idle window ~$0.0466 ($0.0093/request).

Run record 2026-08-25 (deploy of #143+#144 image pins, founder-minted
`qwen-endpoint-token`): unauthed /models and /chat/completions return
401 as required; authed smoke through the real flow client completed
end to end. The two misses are on the alternate-font replay fixture
and are recorded as measurement, not tuned away, per the interpretation
notes above.

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
