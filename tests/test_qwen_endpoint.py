"""Pin the safety invariants of the Qwen grounder endpoint (qwen_endpoint/).

The Modal app must stay scale-to-zero, bearer-token-authenticated, and
version-pinned. These tests read the app source with ``ast`` (the ``modal``
package is deliberately NOT a docs-CI dependency), so a PR that weakens an
invariant fails here rather than silently deploying an expensive or
unauthenticated endpoint.
"""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "qwen_endpoint" / "app.py"
APP_SOURCE = APP_PATH.read_text()
APP_TREE = ast.parse(APP_SOURCE)


def _constant(name):
    """Return the value of a module-level ``NAME = <literal>`` assignment."""
    for node in APP_TREE.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"{name} is not a module-level literal in app.py")


def test_scale_to_zero_idle_window_at_most_120s():
    assert _constant("SCALEDOWN_WINDOW_S") <= 120


def test_no_warm_pool_or_minimum_containers():
    # Any of these would keep a GPU container (and its bill) alive while idle.
    for forbidden in ("min_containers", "keep_warm", "buffer_containers"):
        assert forbidden not in APP_SOURCE, f"{forbidden} defeats scale-to-zero"


def test_auth_comes_from_the_named_modal_secret():
    assert 'modal.Secret.from_name("qwen-endpoint-token")' in APP_SOURCE
    # The serving code must pass the token to vLLM's built-in auth gate.
    assert '"--api-key"' in APP_SOURCE
    assert 'os.environ["TOKEN"]' in APP_SOURCE


def test_no_token_literal_in_source():
    # The token is 32 url-safe random bytes (~43 chars). Nothing resembling
    # a long secret literal may appear in the app source.
    for match in re.findall(r'"([A-Za-z0-9_\-]{40,})"', APP_SOURCE):
        if re.fullmatch(r"[0-9a-f]{40}", match):
            continue  # a git/HF commit pin, not a secret
        raise AssertionError(f"suspicious long literal in app.py: {match[:8]}...")


def test_model_revision_is_a_full_commit_pin():
    assert re.fullmatch(r"[0-9a-f]{40}", _constant("MODEL_REVISION"))
    assert _constant("MODEL_NAME") == "Qwen/Qwen2.5-VL-7B-Instruct"


def test_vllm_version_is_exact_pinned():
    assert re.fullmatch(r"[0-9]+(\.[0-9]+)+", _constant("VLLM_VERSION"))
    assert 'f"vllm=={VLLM_VERSION}"' in APP_SOURCE


def test_gpu_is_a_single_24gb_class_card():
    assert _constant("GPU") in {"A10G", "L4"}


def test_flow_snippet_names_the_served_model_and_env_reference():
    snippet = (ROOT / "qwen_endpoint" / "deployment.snippet.yaml").read_text()
    assert f'model: "{_constant("SERVED_MODEL_NAME")}"' in snippet
    assert 'api_key_env: "OPENADAPT_FLOW_GROUNDING_API_KEY"' in snippet
    assert "allow_model_grounding: true" in snippet
