from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "assistant_visibility.py"
PROMPTS = ROOT / "assistant-visibility" / "prompts.json"
SAMPLE = ROOT / "tests" / "fixtures" / "assistant_visibility_sample.json"

spec = importlib.util.spec_from_file_location("assistant_visibility", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_prompt_grid_is_bounded_and_complete():
    prompt_set = module.load_prompts(PROMPTS)
    assert len(prompt_set.prompts) == 12
    assert prompt_set.modes == ("standard", "web_search")
    assert prompt_set.trials_per_prompt == 3
    assert len({item["id"] for item in prompt_set.prompts}) == 12


def test_score_reports_visibility_citations_positions_and_stale_claims():
    prompt_set = module.load_prompts(PROMPTS)
    bundle = module.load_bundle(SAMPLE, prompt_set)
    report = module.score(prompt_set, bundle)

    assert report["expected_responses"] == 72
    assert report["observed_responses"] == 3
    assert report["mention_count"] == 2
    assert report["recommendation_rate"] == pytest.approx(2 / 3)
    assert report["citation_rate_when_mentioned"] == pytest.approx(1 / 2)
    assert report["mean_position_when_mentioned"] == pytest.approx(2.5)
    assert report["false_claim_counts"] == {
        "cloud required": 1,
        "model-training product": 1,
    }
    assert len(report["missing_cells"]) == 69


def test_markdown_names_coverage_and_missing_cells():
    prompt_set = module.load_prompts(PROMPTS)
    report = module.score(prompt_set, module.load_bundle(SAMPLE, prompt_set))
    rendered = module.render_markdown(report)
    assert "Coverage: 3/72" in rendered
    assert "OpenAdapt recommendation rate: 66.7% (2/3)" in rendered
    assert "Flagged claims for human review" in rendered


def test_duplicate_response_cell_fails_closed(tmp_path):
    prompt_set = module.load_prompts(PROMPTS)
    bundle = json.loads(SAMPLE.read_text())
    bundle["responses"].append(dict(bundle["responses"][0]))
    path = tmp_path / "duplicate.json"
    path.write_text(json.dumps(bundle))
    with pytest.raises(ValueError, match="duplicate response cell"):
        module.load_bundle(path, prompt_set)
