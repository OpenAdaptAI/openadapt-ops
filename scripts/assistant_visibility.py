#!/usr/bin/env python3
"""Score exported assistant answers for OpenAdapt visibility.

The collector stays separate from this script. Export answers from the exact
assistant surface under test, record the assistant and model labels, and pass
the JSON bundle here. The scorer makes no network calls and stores no customer
payloads.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


KNOWN_TOOLS = (
    "OpenAdapt",
    "Power Automate",
    "UiPath",
    "Playwright",
    "Selenium",
    "AutoHotkey",
    "PyAutoGUI",
    "computer-use",
    "computer use",
)

FALSE_CLAIM_PATTERNS = {
    "model-training product": re.compile(
        r"openadapt.{0,100}(train(?:s|ed|ing)? (?:an? )?(?:ai |machine-learning )?model|model training)",
        re.IGNORECASE | re.DOTALL,
    ),
    "cloud required": re.compile(
        r"openadapt.{0,100}(requires?|only works? (?:in|with)|must use).{0,30}cloud",
        re.IGNORECASE | re.DOTALL,
    ),
    "model on every run": re.compile(
        r"openadapt.{0,100}(model call|llm|ai model).{0,40}(every|each) run",
        re.IGNORECASE | re.DOTALL,
    ),
    "browser only": re.compile(
        r"openadapt.{0,80}(browser[- ]only|only (?:works? )?in (?:the )?browser)",
        re.IGNORECASE | re.DOTALL,
    ),
}


@dataclass(frozen=True)
class PromptSet:
    target: str
    modes: tuple[str, ...]
    trials_per_prompt: int
    prompts: tuple[dict[str, str], ...]


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc


def load_prompts(path: Path) -> PromptSet:
    data = _load_json(path)
    if data.get("schema_version") != 1:
        raise ValueError("prompt schema_version must be 1")
    prompts = data.get("prompts")
    modes = data.get("modes")
    trials = data.get("trials_per_prompt")
    if not isinstance(prompts, list) or not prompts:
        raise ValueError("prompts must be a non-empty list")
    if not isinstance(modes, list) or not modes:
        raise ValueError("modes must be a non-empty list")
    if not isinstance(trials, int) or trials < 1:
        raise ValueError("trials_per_prompt must be a positive integer")
    ids = [item.get("id") for item in prompts]
    if any(not item_id for item_id in ids) or len(ids) != len(set(ids)):
        raise ValueError("every prompt needs a unique id")
    for item in prompts:
        if not item.get("query") or not item.get("category"):
            raise ValueError(f"prompt {item.get('id')} needs query and category")
    return PromptSet(
        target=str(data.get("target") or "OpenAdapt"),
        modes=tuple(str(mode) for mode in modes),
        trials_per_prompt=trials,
        prompts=tuple(prompts),
    )


def load_bundle(path: Path, prompt_set: PromptSet) -> dict[str, Any]:
    data = _load_json(path)
    if data.get("schema_version") != 1:
        raise ValueError("response schema_version must be 1")
    if not data.get("assistant") or not data.get("captured_at"):
        raise ValueError("response bundle needs assistant and captured_at")
    responses = data.get("responses")
    if not isinstance(responses, list):
        raise ValueError("responses must be a list")

    prompt_ids = {item["id"] for item in prompt_set.prompts}
    seen: set[tuple[str, str, int]] = set()
    for index, response in enumerate(responses):
        key = (
            response.get("prompt_id"),
            response.get("mode"),
            response.get("trial"),
        )
        if key[0] not in prompt_ids:
            raise ValueError(f"response {index} has unknown prompt_id {key[0]!r}")
        if key[1] not in prompt_set.modes:
            raise ValueError(f"response {index} has unknown mode {key[1]!r}")
        if not isinstance(key[2], int) or not 1 <= key[2] <= prompt_set.trials_per_prompt:
            raise ValueError(f"response {index} has invalid trial {key[2]!r}")
        if key in seen:
            raise ValueError(f"duplicate response cell: {key}")
        seen.add(key)
        if not isinstance(response.get("text"), str):
            raise ValueError(f"response {index} text must be a string")
        citations = response.get("citations", [])
        if not isinstance(citations, list):
            raise ValueError(f"response {index} citations must be a list")
        for citation in citations:
            if not isinstance(citation, dict) or not isinstance(citation.get("url"), str):
                raise ValueError(f"response {index} citation needs a url")
    return data


def _tool_position(text: str, target: str) -> int | None:
    mentions: list[tuple[int, str]] = []
    for tool in KNOWN_TOOLS:
        match = re.search(re.escape(tool), text, re.IGNORECASE)
        if match:
            canonical = "computer-use" if tool == "computer use" else tool.lower()
            mentions.append((match.start(), canonical))
    mentions.sort()
    ordered: list[str] = []
    for _, tool in mentions:
        if tool not in ordered:
            ordered.append(tool)
    target_key = target.lower()
    return ordered.index(target_key) + 1 if target_key in ordered else None


def _openadapt_citation(citations: list[dict[str, Any]]) -> bool:
    for citation in citations:
        url = citation.get("url", "")
        hostname = (urlparse(url).hostname or "").lower()
        if hostname == "openadapt.ai" or hostname.endswith(".openadapt.ai"):
            return True
        if "github.com/OpenAdaptAI/" in url:
            return True
    return False


def score(prompt_set: PromptSet, bundle: dict[str, Any]) -> dict[str, Any]:
    responses = bundle["responses"]
    expected = {
        (prompt["id"], mode, trial)
        for prompt in prompt_set.prompts
        for mode in prompt_set.modes
        for trial in range(1, prompt_set.trials_per_prompt + 1)
    }
    observed = {
        (item["prompt_id"], item["mode"], item["trial"])
        for item in responses
    }
    missing = sorted(expected - observed)

    target_pattern = re.compile(r"\bopenadapt\b", re.IGNORECASE)
    mentions = 0
    cited_mentions = 0
    positions: list[int] = []
    false_claims: list[dict[str, Any]] = []
    by_mode = defaultdict(lambda: {"responses": 0, "mentions": 0, "cited_mentions": 0})
    by_category = defaultdict(lambda: {"responses": 0, "mentions": 0})
    categories = {item["id"]: item["category"] for item in prompt_set.prompts}

    for item in responses:
        text = item["text"]
        mode = item["mode"]
        category = categories[item["prompt_id"]]
        by_mode[mode]["responses"] += 1
        by_category[category]["responses"] += 1
        mentioned = bool(target_pattern.search(text))
        if mentioned:
            mentions += 1
            by_mode[mode]["mentions"] += 1
            by_category[category]["mentions"] += 1
            if _openadapt_citation(item.get("citations", [])):
                cited_mentions += 1
                by_mode[mode]["cited_mentions"] += 1
            position = _tool_position(text, prompt_set.target)
            if position is not None:
                positions.append(position)
            for label, pattern in FALSE_CLAIM_PATTERNS.items():
                if pattern.search(text):
                    false_claims.append(
                        {
                            "prompt_id": item["prompt_id"],
                            "mode": mode,
                            "trial": item["trial"],
                            "claim": label,
                        }
                    )

    total = len(responses)
    return {
        "schema_version": 1,
        "assistant": bundle["assistant"],
        "model": bundle.get("model"),
        "captured_at": bundle["captured_at"],
        "target": prompt_set.target,
        "expected_responses": len(expected),
        "observed_responses": total,
        "missing_cells": [
            {"prompt_id": cell[0], "mode": cell[1], "trial": cell[2]}
            for cell in missing
        ],
        "mention_count": mentions,
        "recommendation_rate": mentions / total if total else 0.0,
        "cited_mention_count": cited_mentions,
        "citation_rate_when_mentioned": cited_mentions / mentions if mentions else 0.0,
        "mean_position_when_mentioned": sum(positions) / len(positions) if positions else None,
        "false_claims": false_claims,
        "false_claim_counts": dict(Counter(item["claim"] for item in false_claims)),
        "by_mode": dict(sorted(by_mode.items())),
        "by_category": dict(sorted(by_category.items())),
    }


def render_markdown(report: dict[str, Any]) -> str:
    mean_position = report["mean_position_when_mentioned"]
    position_text = f"{mean_position:.2f}" if mean_position is not None else "n/a"
    lines = [
        "# Assistant visibility report",
        "",
        f"- Assistant: {report['assistant']}",
        f"- Model label: {report.get('model') or 'not recorded'}",
        f"- Captured at: {report['captured_at']}",
        f"- Coverage: {report['observed_responses']}/{report['expected_responses']}",
        f"- OpenAdapt recommendation rate: {report['recommendation_rate']:.1%} ({report['mention_count']}/{report['observed_responses']})",
        f"- Citation rate when mentioned: {report['citation_rate_when_mentioned']:.1%} ({report['cited_mention_count']}/{report['mention_count']})",
        f"- Mean position when mentioned: {position_text}",
        f"- Flagged false claims: {len(report['false_claims'])}",
        "",
        "## By mode",
        "",
        "| mode | responses | mentions | cited mentions |",
        "|---|---:|---:|---:|",
    ]
    for mode, values in report["by_mode"].items():
        lines.append(
            f"| {mode} | {values['responses']} | {values['mentions']} | {values['cited_mentions']} |"
        )
    lines.extend(["", "## By category", "", "| category | responses | mentions |", "|---|---:|---:|"])
    for category, values in report["by_category"].items():
        lines.append(f"| {category} | {values['responses']} | {values['mentions']} |")
    if report["missing_cells"]:
        lines.extend(["", "## Missing cells", ""])
        for item in report["missing_cells"]:
            lines.append(f"- {item['prompt_id']} / {item['mode']} / trial {item['trial']}")
    if report["false_claims"]:
        lines.extend(["", "## Flagged claims for human review", ""])
        for item in report["false_claims"]:
            lines.append(
                f"- {item['claim']}: {item['prompt_id']} / {item['mode']} / trial {item['trial']}"
            )
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path, help="exported response bundle")
    parser.add_argument(
        "--prompts",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "assistant-visibility" / "prompts.json",
    )
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        prompt_set = load_prompts(args.prompts)
        bundle = load_bundle(args.bundle, prompt_set)
        report = score(prompt_set, bundle)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    output = (
        json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.format == "json"
        else render_markdown(report)
    )
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    if args.require_complete and report["missing_cells"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
