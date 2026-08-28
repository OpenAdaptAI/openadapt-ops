#!/usr/bin/env python3
"""Measure the dominant colours of every image the docs site ships.

The published docs went warm once because nobody measured. Reading a
screenshot with your eyes cannot separate ``#f2f1ec`` from ``#f5f7fa``, and a
grep for token names finds neither. This script measures, and
``docs/assets/visual-palette.json`` records what it measured.

Usage::

    uv run --with pillow python scripts/measure_asset_palette.py           # check
    uv run --with pillow python scripts/measure_asset_palette.py --write   # rewrite

Pillow is deliberately not a project dependency: the ledger is written by hand
at vendoring time and enforced offline by ``tests/test_design_tokens.py``,
which needs only ``hashlib``. Nothing in CI installs an image library.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ASSET_ROOT = REPO / "docs" / "assets"
LEDGER = ASSET_ROOT / "visual-palette.json"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".ico"}
# SVG is deliberately absent. It is text, so its colours are literal hex in the
# file, and tests/test_design_tokens.py greps every shipped text asset for the
# retired values instead of measuring pixels.

# How many of the most common colours the ledger records for each image. Three
# is enough to describe a ground, a raised surface, and a hairline, which is
# what tells a warm palette from a cool one.
TOP_N = 3


def image_paths() -> list[Path]:
    return sorted(
        path
        for path in ASSET_ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measure(path: Path) -> dict:
    from PIL import Image, ImageSequence  # imported lazily; see the docstring

    image = Image.open(path)
    if getattr(image, "is_animated", False):
        # One frame is enough to describe an animation's ground, and the
        # frames of a terminal recording differ only in their text.
        frames = [next(ImageSequence.Iterator(image)).convert("RGB")]
    else:
        frames = [image.convert("RGB")]

    counter: Counter = Counter()
    for frame in frames:
        sample = frame.copy()
        sample.thumbnail((400, 400))
        counter.update(sample.getdata())

    total = sum(counter.values())
    return {
        "sha256": sha256(path),
        "width": image.width,
        "height": image.height,
        "dominant_colors": [
            {
                "hex": "#%02x%02x%02x" % rgb,
                "share_percent": round(100 * count / total, 2),
            }
            for rgb, count in counter.most_common(TOP_N)
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="rewrite the measured fields in docs/assets/visual-palette.json",
    )
    arguments = parser.parse_args()

    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    recorded = ledger["assets"]
    failures: list[str] = []

    on_disk = {
        str(path.relative_to(REPO)).replace("docs/assets/", "", 1)
        for path in image_paths()
    }
    for missing in sorted(on_disk - set(recorded)):
        failures.append(f"{missing}: on disk but absent from visual-palette.json")
    for extra in sorted(set(recorded) - on_disk):
        failures.append(f"{extra}: in visual-palette.json but absent from disk")

    for name in sorted(on_disk & set(recorded)):
        measured = measure(ASSET_ROOT / name)
        entry = recorded[name]
        if arguments.write:
            entry.update(measured)
            print(f"measured {name}: {entry['dominant_colors'][0]['hex']}")
            continue
        for field, value in measured.items():
            if entry.get(field) != value:
                failures.append(
                    f"{name}: recorded {field} is {entry.get(field)!r}, "
                    f"measured {value!r}"
                )

    if arguments.write:
        LEDGER.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {LEDGER.relative_to(REPO)}")
        return 0

    if failures:
        print("The recorded visual palette does not match the images on disk:\n")
        for failure in failures:
            print(f"  - {failure}")
        print(
            "\nRe-run: uv run --with pillow python scripts/measure_asset_palette.py"
            " --write"
        )
        return 1

    print(f"{len(on_disk)} images match their recorded measurements.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
