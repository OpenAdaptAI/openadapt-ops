# Qwen grounder endpoint — deploy / verify / teardown runbook

Self-hosted Qwen VL endpoint on Modal for openadapt-flow's
`OpenAICompatibleGrounder`. OpenAI-compatible, bearer-token auth,
scale-to-zero (idle GPU dies within 120 s, no warm pool).

| What | Value |
|---|---|
| App | `qwen-grounder-endpoint` (`qwen_endpoint/app.py`) |
| Model | `Qwen/Qwen2.5-VL-7B-Instruct` @ `cc594898137f460bfe9f0759e9844b3ce807cfb5` |
| Served model id | `qwen2.5-vl-7b-instruct` |
| Serving | vLLM `0.10.1.1`, bf16, `--max-model-len 16384` |
| GPU | one A10G (24 GB) |
| URL | `https://<workspace>--qwen-grounder-endpoint-serve.modal.run/v1` (printed by `modal deploy`; workspace `abrichr`) |
| Auth | Modal secret `qwen-endpoint-token`, key `TOKEN`; unauthed requests get HTTP 401 from vLLM `--api-key` |
| Scale-to-zero | `scaledown_window=120`, no `min_containers` (guarded by `tests/test_qwen_endpoint.py`) |

## 0. One-time: create the auth secret (FOUNDER ONLY)

Agents never create, read, or copy this token. The founder runs, once:

```bash
python3 -c "import secrets;print(secrets.token_urlsafe(32))" | { read t; modal secret create qwen-endpoint-token TOKEN="$t"; security add-generic-password -s oa-qwen-endpoint-token -a modal -w "$t"; }
```

This mints the token, stores it as the Modal secret `qwen-endpoint-token`
(read only by the serving container) and as the macOS Keychain item
`oa-qwen-endpoint-token` (read only by `with_token.sh` at client runtime).
The value itself is never displayed.

Everything below assumes `modal secret list` shows `qwen-endpoint-token`.

## 1. Deploy

```bash
cd /Users/abrichr/oa/src/openadapt-ops
modal deploy qwen_endpoint/app.py
```

`modal deploy` prints the web URL. The FIRST-ever cold start additionally
downloads ~16 GB of weights into the `qwen-grounder-endpoint-hf-cache`
volume (one-time, a few minutes); later cold starts load from the volume.

## 2. Verify

All authed calls go through the launcher so the token stays in the Keychain:

```bash
cd /Users/abrichr/oa/src/openadapt-ops/qwen_endpoint
BASE=https://abrichr--qwen-grounder-endpoint-serve.modal.run/v1
```

1. **Unauthed => 401** (no launcher, no token):

   ```bash
   curl -s -o /dev/null -w '%{http_code}\n' "$BASE/models"        # expect 401
   curl -s -o /dev/null -w '%{http_code}\n' -X POST "$BASE/chat/completions" \
     -H 'Content-Type: application/json' \
     -d '{"model":"qwen2.5-vl-7b-instruct","messages":[{"role":"user","content":"hi"}]}'   # expect 401
   ```

2. **Cold-start latency** (first authed call after idle; time it):

   ```bash
   time ./with_token.sh sh -c 'curl -s -H "Authorization: Bearer $OPENADAPT_FLOW_GROUNDING_API_KEY" "$0/models"' "$BASE"
   ```

3. **Warm latency + well-formed vision output** — repeat the same call, then
   run the grounder smoke (5 image requests through the real flow client):

   ```bash
   ./with_token.sh uv run --project /Users/abrichr/oa/src/openadapt-flow \
     python3 smoke_grounder.py --base-url "$BASE" \
     --flow-repo /Users/abrichr/oa/src/openadapt-flow --gpu-usd-per-hour 1.10
   ```

   Paste the printed table into `RESULTS.md`.

4. **Scale-to-zero**: wait >2 minutes with no traffic, then:

   ```bash
   modal app list          # qwen-grounder-endpoint shows 0 running containers
   modal container list    # no container for the app
   ```

## 3. Teardown

```bash
modal app stop qwen-grounder-endpoint     # removes the deployment + URL
# optional, reclaims ~16 GB of weight-cache storage:
modal volume delete qwen-grounder-endpoint-hf-cache
modal volume delete qwen-grounder-endpoint-vllm-cache
```

Founder-only, if retiring the endpoint for good: `modal secret delete
qwen-endpoint-token` and `security delete-generic-password -s
oa-qwen-endpoint-token -a modal`.

## 4. Cost math

Rates are the Modal list prices as of 2026-08 — re-check
`https://modal.com/pricing` before trusting a forecast.

| Item | Math | Cost |
|---|---|---|
| A10G GPU-second | ~$1.10/h | ~$0.000306/s |
| Cold start (volume-cached weights) | ~120–240 s | $0.04–0.08 |
| First-ever cold start (HF download) | +~180 s | +~$0.06 |
| Warm grounding request | ~2–6 s | <$0.002 |
| Idle tail after a burst | exactly 120 s | $0.037 |
| **Idle deployment (steady state)** | 0 GPU-s | **$0.00 GPU** + volume storage (~16 GB, order of $0.50/mo; confirm in dashboard) |
| Full verification pass (steps 1–4 above) | ~10–15 min GPU | **~$0.20–0.30** (cap: $5.00) |

Example month — 500 grounding calls in 50 bursts: 50 × (cold 180 s + calls
~30 s + idle 120 s) ≈ 4.6 GPU-hours ≈ **$5/mo**. The same calls against a
hosted per-token API are the sibling Together effort's numbers; compare
before committing either way.

## 5. Pinned-version upgrade path (do NOT bump casually)

* Any bump of `MODEL_REVISION`, `VLLM_VERSION`, or the model itself requires
  a full section-2 verification pass in the same PR, with measured numbers.
* Designated next model: `Qwen/Qwen3-VL-8B-Instruct` @
  `0c351dd01ed87e9c1b53cbc748cba10e6187ff3b` — needs `vllm>=0.11.0`, and at
  ~17 GB bf16 it is tight on 24 GB: expect to lower `--max-model-len`, or
  use the official FP8 checkpoint on an L4/Ada GPU (A10G/Ampere has no
  native FP8).
* `tests/test_qwen_endpoint.py` pins the safety invariants (auth secret
  name, 120 s scaledown, no warm pool, pinned revision); it must keep
  passing untouched.

## 6. Client wiring

`deployment.snippet.yaml` in this directory is the operator-facing flow
config. Run flow under the launcher so the env var named by `api_key_env`
exists: `./with_token.sh openadapt-flow run --config deployment.yaml ...`.
