#!/usr/bin/env python3
"""Smoke-prove openadapt-flow's OpenAICompatibleGrounder against the endpoint.

Runs 5 grounding requests through ``openadapt_flow.runtime.grounder.
OpenAICompatibleGrounder`` (the real client class, not a re-implementation)
against 2 screenshot fixtures COMMITTED in the openadapt-flow repo:

* ``benchmark/dense_surface/record_seed1.png``            (2240x3702, hi-dpi)
* ``benchmark/dense_surface/replay_native_arial_seed1.png`` (1120x1858, 1x)

Both show the MockMed patient-records list (demo, all data fake). Each case
asks for the "Open" button on one named patient's row and judges the proposal
against a hand-verified expected rectangle for that row's Open button:

* abstain -> the grounder returned None (fail-safe path exercised)
* hit     -> proposed point inside the expected rectangle
* miss    -> proposed point outside it

This is a SMOKE test (does the wire work end-to-end), not the accuracy probe.
The full accuracy probe runs against Together in a sibling effort. Note:
Qwen VL models answer in the coordinate frame of the (possibly resized)
image the server preprocessed, so a systematic offset on the hi-dpi fixture
shows up here as `miss` — record it, do not tune around it.

Usage (token comes from the Keychain via the launcher; never passed on argv):

    ./with_token.sh python3 smoke_grounder.py \
        --base-url https://<workspace>--qwen-grounder-endpoint-serve.modal.run/v1 \
        --model qwen2.5-vl-7b-instruct \
        --flow-repo /Users/abrichr/oa/src/openadapt-flow \
        --gpu-usd-per-hour 1.10

Requires ``openadapt_flow`` importable (run under the flow repo's venv, e.g.
``uv run --project <flow-repo> ...``) plus ``httpx`` (a flow dependency).
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
from pathlib import Path

# Each case: (fixture relative path, intent, ocr_text, expected rect x0,y0,x1,y1)
# Rectangles are in ORIGINAL fixture pixels, hand-verified 2026-08-12 against
# the committed PNGs; they cover the Open button on the named patient's row
# with a few pixels of margin.
CASES = [
    (
        "benchmark/dense_surface/record_seed1.png",
        "Click Open in the row for patient Halloran, Karen (MRN MG584224)",
        "Open",
        (1975, 195, 2140, 260),
    ),
    (
        "benchmark/dense_surface/record_seed1.png",
        "Click Open in the row for patient Delgado, Edward (MRN MG901312)",
        "Open",
        (1975, 1415, 2140, 1485),
    ),
    (
        "benchmark/dense_surface/record_seed1.png",
        "Click Open in the row for patient Kowalski, Maria (MRN RC571054)",
        "Open",
        (1975, 3245, 2140, 3320),
    ),
    (
        "benchmark/dense_surface/replay_native_arial_seed1.png",
        "Click Open in the row for patient Ferreira, Susan (MRN PT994939)",
        "Open",
        (1000, 170, 1100, 215),
    ),
    (
        "benchmark/dense_surface/replay_native_arial_seed1.png",
        "Click Open in the row for patient Whitfield, Philip (MRN PT560165)",
        "Open",
        (1000, 1800, 1100, 1850),
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help=".../v1 root of the endpoint")
    parser.add_argument("--model", default="qwen2.5-vl-7b-instruct")
    parser.add_argument("--flow-repo", required=True, help="openadapt-flow checkout")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--gpu-usd-per-hour",
        type=float,
        default=1.10,
        help="GPU price used for the per-request cost column (A10G default)",
    )
    args = parser.parse_args()

    api_key = os.environ.get("OPENADAPT_FLOW_GROUNDING_API_KEY", "")
    if not api_key:
        print(
            "OPENADAPT_FLOW_GROUNDING_API_KEY is not set. Run via ./with_token.sh "
            "so the token is sourced from the Keychain at runtime.",
            file=sys.stderr,
        )
        return 2

    try:
        from openadapt_flow.runtime.grounder import OpenAICompatibleGrounder
    except ImportError as exc:
        print(
            f"Cannot import openadapt_flow ({exc}). Run under the flow repo's "
            "environment, e.g.: ./with_token.sh uv run --project "
            f"{args.flow_repo} python3 {Path(__file__).name} ...",
            file=sys.stderr,
        )
        return 2

    flow_repo = Path(args.flow_repo)
    grounder = OpenAICompatibleGrounder(
        base_url=args.base_url,
        model=args.model,
        api_key=api_key,
        timeout=args.timeout,
    )

    rows = []
    latencies = []
    for fixture, intent, ocr_text, rect in CASES:
        png_path = flow_repo / fixture
        screen_png = png_path.read_bytes()
        t0 = time.monotonic()
        match = grounder.locate(screen_png, intent, ocr_text=ocr_text)
        dt = time.monotonic() - t0
        latencies.append(dt)
        if match is None:
            verdict, point = "abstain", "-"
        else:
            x, y = match.point
            x0, y0, x1, y1 = rect
            verdict = "hit" if (x0 <= x <= x1 and y0 <= y <= y1) else "miss"
            point = f"({x}, {y})"
        rows.append((fixture.rsplit("/", 1)[-1], intent, verdict, point, dt))
        print(f"[{verdict:7s}] {dt:6.2f}s  {point:16s}  {intent}")

    # GPU-time cost attribution: wall latency plus the amortized share of the
    # 120 s post-burst idle window, at the given hourly rate.
    usd_per_s = args.gpu_usd_per_hour / 3600.0
    idle_share_s = 120.0 / len(CASES)
    print("\n| fixture | intent | verdict | point | latency_s | est_cost_usd |")
    print("|---|---|---|---|---|---|")
    for name, intent, verdict, point, dt in rows:
        cost = (dt + idle_share_s) * usd_per_s
        print(f"| {name} | {intent} | {verdict} | {point} | {dt:.2f} | {cost:.4f} |")

    n = len(rows)
    hits = sum(1 for r in rows if r[2] == "hit")
    misses = sum(1 for r in rows if r[2] == "miss")
    abstains = sum(1 for r in rows if r[2] == "abstain")
    total_cost = (sum(latencies) + 120.0) * usd_per_s
    print(
        f"\n{n} requests: {hits} hit / {misses} miss / {abstains} abstain; "
        f"latency median {statistics.median(latencies):.2f}s "
        f"(min {min(latencies):.2f}s, max {max(latencies):.2f}s); "
        f"burst GPU cost incl. one 120s idle window ~${total_cost:.4f} "
        f"(${total_cost / n:.4f}/request)"
    )
    # Smoke PASSES when the wire works: every request either grounded or
    # cleanly abstained, and at least one call actually grounded.
    return 0 if (hits + misses + abstains == n and hits > 0) else 1


if __name__ == "__main__":
    sys.exit(main())
