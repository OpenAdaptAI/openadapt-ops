---
title: Quick Start moved
description: Record a GUI workflow, compile it, and replay the program with openadapt flow.
canonical: https://docs.openadapt.ai/get-started/
redirect_to: /get-started/
hide:
  - navigation
  - toc
---

# Quick Start moved

The current first run is at [Get started](/get-started/).

```bash
pip install openadapt
openadapt quickstart
```

That records a bundled demonstration, compiles a program, and replays it locally. A healthy run makes no model API call.

To record your own application:

```bash
openadapt flow record --backend web --url https://your.app --out rec
openadapt flow compile rec --out bundle --name my-task
openadapt flow replay bundle --url https://your.app --headed
```

[Continue to Get started](/get-started/){ .md-button .md-button--primary }
