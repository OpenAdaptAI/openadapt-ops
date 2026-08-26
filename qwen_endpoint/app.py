"""Modal app: Qwen VL grounding endpoint (OpenAI-compatible, scale-to-zero).

Serves ``Qwen/Qwen2.5-VL-7B-Instruct`` (pinned revision) via vLLM behind an
OpenAI-compatible ``/v1/chat/completions`` route, sized for one 24 GB GPU.

Design constraints (enforced by ``tests/test_qwen_endpoint.py``):

* Scale-to-zero: ``scaledown_window`` is at most 120 s; no container floor,
  no warm pool. An idle deployment costs $0 in GPU time.
* Auth: every request must carry ``Authorization: Bearer <token>`` where the
  token comes from the Modal secret ``qwen-endpoint-token`` (key ``TOKEN``).
  vLLM's ``--api-key`` flag rejects anything else with HTTP 401. The token is
  read INSIDE the container from the secret; it never appears in this repo,
  in logs, or in the deploy output.
* Pinned model: the exact HuggingFace revision is pinned below so a re-deploy
  serves byte-identical weights.

Deploy / verify / teardown: see ``qwen_endpoint/RUNBOOK.md``.

Client wiring: openadapt-flow's ``OpenAICompatibleGrounder`` points at
``https://<workspace>--qwen-grounder-endpoint-serve.modal.run/v1`` — see
``qwen_endpoint/deployment.snippet.yaml``.
"""

import subprocess

import modal

APP_NAME = "qwen-grounder-endpoint"

# -- model pin ---------------------------------------------------------------
# Qwen2.5-VL-7B-Instruct: the largest Qwen VL known to serve reliably on one
# 24 GB GPU under vLLM in bf16 (~15.5 GB weights + KV cache at 16k context).
# Revision = HF main as read on 2026-08-12 (last modified 2025-04-06).
#
# Qwen3-VL-8B-Instruct (revision 0c351dd01ed87e9c1b53cbc748cba10e6187ff3b) is
# the designated upgrade once a deploy can be GPU-verified: it needs
# vllm>=0.11.0 and is tighter on 24 GB (~17 GB bf16 weights); see RUNBOOK.md.
MODEL_NAME = "Qwen/Qwen2.5-VL-7B-Instruct"
MODEL_REVISION = "cc594898137f460bfe9f0759e9844b3ce807cfb5"
# The model id clients put in the request body ("model": ...). Matches the
# example already shipped in openadapt-flow docs/deployment.example.yaml.
SERVED_MODEL_NAME = "qwen2.5-vl-7b-instruct"

# -- serving pin -------------------------------------------------------------
# vLLM 0.10.1.1: a version attested to serve Qwen2.5-VL with exactly the flags
# used below. Bump ONLY together with a verified deploy (RUNBOOK.md).
VLLM_VERSION = "0.10.1.1"

GPU = "A10G"  # 24 GB. "L4" (24 GB, cheaper, slower) is a drop-in alternative.
PORT = 8000
SCALEDOWN_WINDOW_S = 120  # hard cap per ops policy: idle GPU dies within 120 s
STARTUP_TIMEOUT_S = 20 * 60  # first-ever cold start downloads ~16 GB of weights
MAX_MODEL_LEN = 16384  # one full-desktop screenshot is ~2.7k vision tokens
GPU_MEMORY_UTILIZATION = 0.90
MAX_CONCURRENT_INPUTS = 8

image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install(
        f"vllm=={VLLM_VERSION}",
        "huggingface_hub[hf_transfer]",
        # openai>=1.100 imports httpx_aiohttp, which needs aiohttp>=3.12
        # (SocketTimeoutError). vllm pins an older aiohttp; pin ours newer.
        "aiohttp>=3.12,<4",
        # vllm 0.10.1.1 rejects Qwen2.5-VL's mrope rope_scaling when a
        # newer transformers remaps it to the modern field set
        # ("conflicts between rope_type=default and type=mrope").
        # Pin the transformers line contemporary with this vllm.
        "transformers>=4.55,<4.56",
    )
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)

# Weights cache: survives scale-to-zero, so only the FIRST cold start ever
# pays the HuggingFace download. Subsequent cold starts load from the volume.
hf_cache = modal.Volume.from_name(
    "qwen-grounder-endpoint-hf-cache", create_if_missing=True
)
# torch.compile / vLLM artifact cache: shaves repeat cold-start work.
vllm_cache = modal.Volume.from_name(
    "qwen-grounder-endpoint-vllm-cache", create_if_missing=True
)

app = modal.App(APP_NAME)


@app.function(
    image=image,
    gpu=GPU,
    scaledown_window=SCALEDOWN_WINDOW_S,
    timeout=60 * 60,
    volumes={
        "/root/.cache/huggingface": hf_cache,
        "/root/.cache/vllm": vllm_cache,
    },
    secrets=[modal.Secret.from_name("qwen-endpoint-token")],
)
@modal.concurrent(max_inputs=MAX_CONCURRENT_INPUTS)
@modal.web_server(port=PORT, startup_timeout=STARTUP_TIMEOUT_S)
def serve() -> None:
    """Launch the vLLM OpenAI-compatible server.

    The bearer token is read from the environment injected by the Modal
    secret ``qwen-endpoint-token`` (key ``TOKEN``). It is passed to vLLM as
    ``--api-key`` and never printed. A missing secret key fails loudly here
    rather than starting an unauthenticated server.
    """
    import os

    token = os.environ["TOKEN"]  # KeyError => refuse to start without auth
    if not token.strip():
        raise RuntimeError(
            "Secret qwen-endpoint-token has an empty TOKEN; refusing to start "
            "an unauthenticated server."
        )

    cmd = [
        "vllm",
        "serve",
        MODEL_NAME,
        "--revision",
        MODEL_REVISION,
        "--served-model-name",
        SERVED_MODEL_NAME,
        "--host",
        "0.0.0.0",
        "--port",
        str(PORT),
        "--api-key",
        token,
        "--gpu-memory-utilization",
        str(GPU_MEMORY_UTILIZATION),
        "--max-model-len",
        str(MAX_MODEL_LEN),
    ]
    # Popen, not run: web_server expects the function to return once the
    # port is (eventually) listening; vLLM keeps serving in this process.
    subprocess.Popen(cmd)
