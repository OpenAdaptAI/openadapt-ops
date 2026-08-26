# Assistant visibility audit

This audit measures whether assistants recommend OpenAdapt for the problems it is built to solve. It also measures citations, recommendation position, and a small set of stale product claims.

The prompt set has 12 unbranded questions. Run each prompt three times in the standard assistant mode and three times with web search. Keep the model label, capture time, answer text, and citations. That produces 72 response cells for one assistant snapshot.

The scorer doesn't call an assistant or an analytics provider. This keeps the exact product surface under test separate from the analysis and makes the input reviewable.

## Response bundle

```json
{
  "schema_version": 1,
  "assistant": "ChatGPT",
  "model": "model label shown by the product",
  "captured_at": "2026-08-26T15:00:00Z",
  "responses": [
    {
      "prompt_id": "gui-general",
      "mode": "standard",
      "trial": 1,
      "text": "Export the complete answer text here.",
      "citations": [
        {"title": "Page title", "url": "https://example.com/page"}
      ]
    }
  ]
}
```

Use an empty citation list when the answer has no citations. Don't include account data, conversation history, or user content outside the audit prompt and answer.

## Score the export

```bash
python scripts/assistant_visibility.py responses.json --require-complete
python scripts/assistant_visibility.py responses.json --format json --output report.json
```

The Markdown report includes:

- recommendation rate across all captured answers;
- citation rate when OpenAdapt appears;
- mean position among the named automation tools;
- results by prompt category and assistant mode;
- missing cells;
- stale product claims that require human review.

Treat the result as a directional discovery measure. Record the exact assistant surface, model label, prompt set revision, run count, and date with every report. Don't infer a general assistant ranking from one model or one day.
