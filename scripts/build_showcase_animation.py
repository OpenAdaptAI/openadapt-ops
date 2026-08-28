#!/usr/bin/env python3
"""Build docs/assets/showcase/demo.gif from a published reference evidence pack.

The showcase animation on the get-started pages must show a real application
running synthetic data. OpenAdaptAI/openadapt-web publishes the reference packs
that satisfy that: each one carries the runtime's own saved recording and replay
media plus a manifest that names the pinned application images, the runtime
commit, and the measured outcome of every trial. This script composes frames
from one of those packs; it invents nothing and it renders no claim that the
manifest does not state.

Usage::

    uv run --with pillow python scripts/build_showcase_animation.py \
        --pack ../openadapt-web/public/reference/openimis-eligibility-standard-synthetic-v1

ffmpeg decodes the pack's H.264 media and quantises the result, so both it and
Pillow must be on PATH. Neither is a project dependency: like
scripts/measure_asset_palette.py, this runs at vendoring time and CI enforces
only the committed bytes, through docs/assets/visual-palette.json and
tests/test_design_tokens.py.

Every colour below is a canonical design token, read from the vendored copy at
docs/stylesheets/vendor/openadapt-web/tokens.json. The dark inset ground keeps
the animation's dominant colour cool, which the palette guard requires.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOKENS = REPO / "docs" / "stylesheets" / "vendor" / "openadapt-web" / "tokens.json"
OUTPUT = REPO / "docs" / "assets" / "showcase" / "demo.gif"

CANVAS = (1272, 596)
SHOT = (800, 500)  # the pack's 1280x800 media scales to this exactly
SHOT_ORIGIN = (36, 64)
PANEL = (872, 64, 1236, 564)  # left, top, right, bottom
HEADER_BASELINE = 18
FOOTER_BASELINE = 570

FONT_REGULAR = "/System/Library/Fonts/Menlo.ttc"
FONT_BOLD_INDEX = 1

# Frames sampled from each mode's media, and how long each sampled frame holds.
# The recording is 25fps footage of a person working, so it needs more samples
# than the replays, whose media retains one frame per runtime observation.
BEATS = [
    {"mode": "recording", "samples": 8, "hold_ms": 300, "tail_ms": 1000},
    {"mode": "verified_replay", "samples": 7, "hold_ms": 320, "tail_ms": 1600},
    {"mode": "fail_safe_halt", "samples": 7, "hold_ms": 320, "tail_ms": 2200},
]

# The opening card. It holds on the canvas ground, so it is also the frame that
# scripts/measure_asset_palette.py samples: an animation's recorded dominant
# colour is its first frame's, and the first frame here is the composition's own
# --inset-bg rather than whichever application screen happens to open the
# footage. docs/assets/showcase/PROVENANCE.txt says so beside the measurement.
CARD_HOLD_MS = 1600
CARD_TITLE = "One demonstration, compiled once and replayed twice."
CARD_LINES = [
    "openIMIS 25.10, running synthetic data on a local browser.",
    "A read-only SQL query verifies one replay. The other halts.",
]

# Panel copy. Every line restates a field of the pack manifest or a value legible
# in the frame beside it. Nothing here is an inference.
PANEL_COPY = {
    "recording": {
        "step": "1 of 3",
        "badge": None,
        "body": [
            "A person does the task once.",
            "",
            "Task: insurance eligibility check.",
            "Look up a policyholder and a",
            "service, then read the result.",
            "",
            "This recording compiles into",
            "the program that runs below.",
        ],
    },
    "verified_replay": {
        "step": "2 of 3",
        "badge": ("VERIFIED", "ok"),
        "body": [
            "The compiled program repeats it.",
            "",
            "Policy BCUL0001, status Active,",
            "expiry 2027-06-30.",
            "",
            "A read-only SQL query confirms",
            "the result independently.",
            "",
            "3 of 3 trials verified.",
            "0 model calls.",
        ],
    },
    "fail_safe_halt": {
        "step": "3 of 3",
        "badge": ("HALTED", "warn"),
        "body": [
            "The same screen. Another record.",
            "",
            "Policy BCUL0001, status Expired,",
            "expiry 2026-05-31.",
            "",
            "The SQL query disagrees with the",
            "screen, so the run stops.",
            "",
            "3 of 3 trials halted.",
            "0 silent incorrect successes.",
        ],
    },
}


def _tokens() -> dict[str, str]:
    """Read the vendored colour tokens as a ``inset-bg``-style name map."""
    raw = json.loads(TOKENS.read_text(encoding="utf-8"))["color"]
    return {name.lstrip("-"): value for name, value in raw.items()}


def _require(binary: str) -> str:
    found = shutil.which(binary)
    if not found:
        sys.exit(f"{binary} is not on PATH. This script runs at vendoring time.")
    return found


def _decode(media: Path, into: Path) -> list[Path]:
    into.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [_require("ffmpeg"), "-loglevel", "error", "-i", str(media),
         "-vsync", "0", str(into / "%04d.png"), "-y"],
        check=True,
    )
    frames = sorted(into.glob("*.png"))
    if not frames:
        sys.exit(f"ffmpeg decoded no frames from {media}")
    return frames


def _sample(frames: list[Path], count: int) -> list[Path]:
    if len(frames) <= count:
        return frames
    last = len(frames) - 1
    return [frames[round(i * last / (count - 1))] for i in range(count)]


def _compose(pack: Path, manifest: dict, colors: dict[str, str]) -> list:
    from PIL import Image, ImageDraw, ImageFont

    if not Path(FONT_REGULAR).exists():
        sys.exit(f"{FONT_REGULAR} is missing. Point FONT_REGULAR at a mono face.")

    regular = ImageFont.truetype(FONT_REGULAR, 15)
    small = ImageFont.truetype(FONT_REGULAR, 13)
    title = ImageFont.truetype(FONT_REGULAR, 22, index=FONT_BOLD_INDEX)
    badge_font = ImageFont.truetype(FONT_REGULAR, 14, index=FONT_BOLD_INDEX)

    ground = colors["inset-bg"]
    raised = colors["inset-raised"]
    border = colors["inset-border"]
    text = colors["inset-text"]
    muted = colors["hairline-strong"]
    ok = colors["inset-ok"]
    warn = colors["inset-warn"]
    badge_colors = {"ok": ok, "warn": warn}

    application = manifest["application"]
    header_left = f"{application['name']} {application['version']}  ·  synthetic data"
    header_right = "openadapt-flow  ·  local browser  ·  0 model calls"
    footer = (
        "Every frame is media the runtime saved during the run. "
        f"Reference pack {manifest['pack_id']}."
    )

    modes = {mode["id"]: mode for mode in manifest["modes"]}
    composed: list[tuple] = []

    card = Image.new("RGB", CANVAS, ground)
    card_draw = ImageDraw.Draw(card)
    card_title_font = ImageFont.truetype(FONT_REGULAR, 26, index=FONT_BOLD_INDEX)
    card_y = CANVAS[1] // 2 - 54
    card_width = card_draw.textlength(CARD_TITLE, font=card_title_font)
    card_draw.text(((CANVAS[0] - card_width) / 2, card_y), CARD_TITLE,
                   font=card_title_font, fill=text)
    card_y += 52
    for line in CARD_LINES:
        width = card_draw.textlength(line, font=regular)
        card_draw.text(((CANVAS[0] - width) / 2, card_y), line,
                       font=regular, fill=muted)
        card_y += 26
    composed.append((card, CARD_HOLD_MS))

    with tempfile.TemporaryDirectory() as workspace:
        for beat in BEATS:
            mode = modes[beat["mode"]]
            frames = _decode(pack / mode["media"]["path"], Path(workspace) / mode["id"])
            chosen = _sample(frames, beat["samples"])

            for position, frame_path in enumerate(chosen):
                canvas = Image.new("RGB", CANVAS, ground)
                draw = ImageDraw.Draw(canvas)

                draw.text((SHOT_ORIGIN[0], HEADER_BASELINE), header_left,
                          font=regular, fill=text)
                right_width = draw.textlength(header_right, font=small)
                draw.text((PANEL[2] - right_width, HEADER_BASELINE + 2),
                          header_right, font=small, fill=muted)

                shot = Image.open(frame_path).convert("RGB").resize(SHOT, Image.LANCZOS)
                canvas.paste(shot, SHOT_ORIGIN)
                draw.rectangle(
                    [SHOT_ORIGIN[0] - 1, SHOT_ORIGIN[1] - 1,
                     SHOT_ORIGIN[0] + SHOT[0], SHOT_ORIGIN[1] + SHOT[1]],
                    outline=border,
                )

                draw.rectangle(list(PANEL), fill=raised, outline=border)
                copy = PANEL_COPY[mode["id"]]
                x = PANEL[0] + 22
                y = PANEL[1] + 24
                draw.text((x, y), copy["step"], font=small, fill=muted)
                y += 26
                draw.text((x, y), mode["label"], font=title, fill=text)
                y += 40

                if copy["badge"]:
                    label, tone = copy["badge"]
                    tone_color = badge_colors[tone]
                    width = draw.textlength(label, font=badge_font)
                    draw.rectangle([x, y, x + width + 20, y + 26], outline=tone_color)
                    draw.text((x + 10, y + 5), label, font=badge_font, fill=tone_color)
                    y += 42

                for line in copy["body"]:
                    if line:
                        draw.text((x, y), line, font=small, fill=text)
                    y += 20

                draw.text((SHOT_ORIGIN[0], FOOTER_BASELINE), footer,
                          font=small, fill=muted)

                is_last = position == len(chosen) - 1
                duration = beat["tail_ms"] if is_last else beat["hold_ms"]
                composed.append((canvas, duration))

    return composed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pack",
        type=Path,
        required=True,
        help="path to a reference pack directory in a local openadapt-web checkout",
    )
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument(
        "--max-colors",
        type=int,
        default=48,
        help=(
            "palette size handed to ffmpeg palettegen. The composition is flat "
            "UI chrome, so 48 is visually indistinguishable from 256 and costs "
            "roughly half the bytes."
        ),
    )
    arguments = parser.parse_args()

    pack = arguments.pack.resolve()
    manifest = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))
    if manifest["data_classification"] != "synthetic":
        sys.exit(
            f"{pack.name} is classified {manifest['data_classification']!r}. "
            "The showcase animation ships only synthetic data."
        )

    frames = _compose(pack, manifest, _tokens())

    with tempfile.TemporaryDirectory() as workspace:
        staging = Path(workspace)
        durations = []
        for index, (image, duration) in enumerate(frames):
            image.save(staging / f"{index:04d}.png")
            durations.append(duration)

        concat = staging / "concat.txt"
        concat.write_text(
            "".join(
                f"file '{staging / f'{i:04d}.png'}'\nduration {d / 1000:.3f}\n"
                for i, d in enumerate(durations)
            )
            # ffmpeg's concat demuxer ignores the final entry's duration unless
            # the last file is repeated.
            + f"file '{staging / f'{len(durations) - 1:04d}.png'}'\n",
            encoding="utf-8",
        )

        palette = staging / "palette.png"
        ffmpeg = _require("ffmpeg")
        subprocess.run(
            [ffmpeg, "-loglevel", "error", "-f", "concat", "-safe", "0",
             "-i", str(concat), "-vf",
             f"palettegen=max_colors={arguments.max_colors}:stats_mode=diff",
             str(palette), "-y"],
            check=True,
        )
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [ffmpeg, "-loglevel", "error", "-f", "concat", "-safe", "0",
             "-i", str(concat), "-i", str(palette), "-lavfi",
             "paletteuse=dither=none:diff_mode=rectangle",
             "-loop", "0", str(arguments.output), "-y"],
            check=True,
        )

    size = arguments.output.stat().st_size
    try:
        shown = arguments.output.relative_to(REPO)
    except ValueError:
        shown = arguments.output
    print(f"wrote {shown}: {len(frames)} frames, {size:,} bytes")
    print("Now run: uv run --with pillow python scripts/measure_asset_palette.py --write")
    return 0


if __name__ == "__main__":
    sys.exit(main())
