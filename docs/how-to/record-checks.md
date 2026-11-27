---
description: >-
  Configure how OpenAdapt checks the target state after each change on the
  four-level verification ladder, and set the minimum check level a workflow
  needs.
---

# Add record checks

A record check reads the target state after an action that changes a record and
compares the expected values. Not every UI has a Save button, a separate
post-save screen, or a safe page reload, so OpenAdapt supports four confirmed
check levels: a direct read of the system of record (`system_of_record`), a
separate read-only session (`separate_session`), an idempotent same-session
reload or reopen (`reopened`), or a bounded check on the settled current screen
(`same_screen`). Without a record check (`unchecked`), a run never ends
`VERIFIED`. Under the Standard and Regulated profiles, a run refuses an
unchecked write. Under the Demo profile, it needs `--approve-unverified-writes`
and ends `COMPLETED_UNVERIFIED` at best.

There are two halves:

- The **program** declares what must be true after each change, for example
  "one new triage note for this patient", and can set an optional
  `minimum_readback` floor (`same_screen`, `reopened`, `separate_session`, or
  `system_of_record`).
- The **deployment** configures where to read it: a bounded check on the
  settled screen (`same_screen` / `effects.kind: onscreen`), a same-session
  reload or reopen when re-reading is idempotent (`reopened` / `fresh_reload`),
  a separate signed-in browser session (`separate_session` / `ui_readback`), or
  a direct system-of-record read (REST, GraphQL, FHIR, read-only SQL, file,
  email, or document store). This lives in the `effects:` section of a
  deployment file and never in the program.

## 1. Draft the check from the recording

```bash
openadapt flow scaffold-verifier rec --out checks/
```

`scaffold-verifier` takes a recording or a compiled bundle, finds the steps
that look like saves, and writes a draft `checks/effect_contract.yaml`. The
draft verifies nothing until a person who knows the app fills in every
`TODO`: which record each save must create or change, and where that record
can be read. A check must select the record by the identifier the run works
on, such as the patient id, so another record can't satisfy it.

## 2. Say where the record lives

Create a deployment file with an `effects:` section. A REST example:

```yaml
effects:
  kind: rest
  base_url: https://app.example.org
  records_path: /api/records
  records_key: records
  auth:
    bearer_env: SOR_BEARER_TOKEN   # the name of an environment variable
```

Credentials are always the names of environment variables, never values.
Each `kind` and its fields are listed in
[Configuration](../reference/configuration.md#effects).

For a quick test you can also pass the kind on the command line:

```bash
openadapt flow run bundle --effects-kind rest --effects-base-url https://app.example.org ...
```

## 3. Pick the strongest check you can reach

| `checked_how` | Where the target state is read | How | What it reaches |
|---|---|---|---|
| `system_of_record` (Tier 1) | The system's API, database, or files: REST, GraphQL, FHIR, read-only SQL, a file or report drop, an email capture folder, or a document store | `effects.kind` `rest`, `graphql`, `fhir`, `sql`, `file`, `document`, `email`, `document-hash` | `VERIFIED` under `Standard` and `Regulated`, `qualify` certification, and Cloud countersignature |
| `separate_session` (Tier 2) | The app's view opened in a separate, freshly signed-in, read-only browser or app session | `effects.kind: ui_readback` or `fresh_session` | `VERIFIED` under `Standard` and `Regulated` (minimum floor for `Regulated`, unless policy requires Tier 1) |
| `reopened` (Tier 3) | Same-session reload, state reset, or reopened record view when re-reading is idempotent | `fresh_reload` or a demonstrated reopen check | `VERIFIED` under `Standard`; `COMPLETED_UNVERIFIED` under `Regulated` |
| `same_screen` (Tier 4) | A bounded region or element on the current screen after the action settles | `effects.kind: onscreen` or auto-derived `same_screen` | Default baseline for in-place UIs and non-idempotent flows; reaches `VERIFIED` under `Standard` (`checked_how: "same_screen"`) and `COMPLETED_UNVERIFIED` under `Regulated` |

[How a save is checked](../explanation/verification.md#how-strong-a-read-back-is)
maps each level to `VERIFIED`, `qualify` certification, and Cloud's
countersignature. A workflow can set `minimum_readback` to `"same_screen"`,
`"reopened"`, `"separate_session"`, or `"system_of_record"` when a task must
enforce a stricter floor than the profile's default. When the deployment can
read more than one way, list them under `effects.candidates` instead of
`effects.kind`; Flow uses the strongest one for each write.

### Check a bounded region on the current screen

Many UIs change state in place without opening a post-save page or exposing an
idempotent reload: spreadsheet and grid cell edits, auto-saving fields,
toggles, `Apply` or `Ctrl+S` dialogs that stay on the same view, queue items
that leave a list, and non-idempotent `POST` or multi-step wizard flows where
reloading would re-submit or break session state.

Bounded same-screen verification (`same_screen`, Tier 4, labeled `"Checked on
the screen"`) checks that a bounded region or element on the current screen
stabilizes with the expected state after the action settles:

- Auto-derived out of the box when a bounded region settles on the expected
  value, or configured explicitly with `effects.kind: onscreen`
  (`readback_region` and `readback_min_ratio` set the region and match
  threshold).
- Reaches `VERIFIED` under the `Standard` profile (unless the workflow sets a
  stricter `minimum_readback`), stamping `checked_how: "same_screen"` and
  `effect_assurance: "screen_readback"` on the run report and receipt.
- Under the `Regulated` profile, ends `COMPLETED_UNVERIFIED` with
  `below_minimum: true` in `report.json` so regulated workloads require at
  least `separate_session` (Tier 2) or `system_of_record` (Tier 1).

<span id="reload-the-record-page-in-the-same-session"></span>

### Reload or reopen in the same session

When a web page supports safe, idempotent `GET` reloads, OpenAdapt can perform
a **fresh page reload** (`fresh_reload`, `checked_how: "reopened"`), discarding
client-side form memory and reading the record back from the server's rendered
response:

- No second account, API token, or database credential is required.
- A confirmed `fresh_reload` check reaches `VERIFIED` under `Standard` (unless
  `minimum_readback` requires `separate_session` or `system_of_record`) and
  records `checked_how: "reopened"` on the report and receipt.
- Skip `fresh_reload` on non-idempotent `POST` pages or multi-step wizards
  where a reload would re-submit or lose wizard progress; use `same_screen`,
  `ui_readback`, or a backend verifier instead.
- If the reloaded page omits the expected field or shows a different record,
  the run stops with `RECONCILIATION_REQUIRED` and refuses a blind retry.

### Read the record page in a separate session

Use `ui_readback` (`checked_how: "separate_session"`, Tier 2) when you want a
check outside the acting session without an API or database connection,
including as the minimum floor under the `Regulated` profile. Configure it with
a separate read-only account, so the check never uses the session that
performed the action:

```yaml
effects:
  kind: ui_readback
  ui_readback:
    record_url: "https://app.example.org/patients/{patient}/encounters"
    url_params: { patient: { param: patient_id } }
    sign_in:
      url: https://app.example.org/login
      username_selector: "#username"
      password_selector: "#password"
      submit_selector: "button[type=submit]"
      signed_in_selector: "#user-menu"
      username_env: APP_READER_USERNAME
      password_env: APP_READER_PASSWORD
    ready_selector: "#encounters"
    empty_selector: "#no-encounters"
    row_selector: "tr.encounter"
    fields:
      id: { attribute: data-id }
      note: { selector: "td.note", attribute: title }
    identity:
      reader: { selector: "#patient-mrn" }
      value: { param: patient_id }
      field: patient_id
```

After it signs in, the session can only read: requests other than GET, HEAD,
and OPTIONS are refused, which makes the read uncertain and stops the run.
`read_post_paths` lists read endpoints that use POST. Read full values from
attributes where the page shortens text, declare `empty_selector`, and set
the effect's `timeout_s` above any replica lag; each of those otherwise
stops the run. A field's `date_format` and `casefold` change how it's
compared. Single sign-on and multi-factor sign-in aren't supported.

A confirmed `ui_readback` counts as the record check while each save is
approved (`each_item`, the default). Under `problems_only`, a save checked
only this way still goes to a person.

### Show how you'd reopen and check the record

When a desktop, RDP, or Citrix app supports closing and reopening a record by
its identifier, you can demonstrate a Tier 3 (`reopened`) or Tier 2
(`fresh_session`) check directly:

```bash
openadapt flow record --with-check --out rec ...
```

After the action, Flow prompts "Now show how you'd check it saved." When you
stop, it lists the recorded events and asks where the check starts and which
regions show the values you typed. It writes them to `check.json` beside the
recording. For a recording made without `--with-check`, write the same file
with `check mark`:

```bash
openadapt flow check mark rec --start-event 14 --field patient_id=410,212,180,24
```

This demonstrated reopen path expects a state-reset step: a reload, a new
search, or a window closed and reopened. Flow recognizes those from the
recording. Name one it can't recognize, such as a click on the browser's reload
button or a fresh sign-in, with `--reset KIND@EVENT`, where `KIND` is `reload`,
`new_search`, `reopen_window`, or `fresh_session`. `compile` refuses a
demonstrated reopen check with no reset, a marked region that doesn't show the
typed value, or a check that types a secret. When reopening is not possible or
not idempotent, use a bounded `same_screen` check (`effects.kind: onscreen`)
instead.

A compiled check confirms nothing until a person admits it, at a terminal:

```bash
openadapt flow check show bundle
openadapt flow check admit bundle
```

`check admit` prints each check, its reset, and its fields, and asks you to
type `admit`. It records who admitted it, when, and a digest of the check, so
a check that changes needs admitting again. An admission in the name of an
agent or a service is refused.

At run time the check replays the navigation with this run's values and reads
each field from the page structure where the app exposes it (browser,
macOS, Linux), or by OCR (always on RDP and Citrix). Each field is compared
by kind, inferred from the typed value or set with `--kind PARAM=KIND`:

| Kind | Compared after | Matches |
|---|---|---|
| `text` | lowercasing and collapsing whitespace | `Chest pain` and `chest  pain` |
| `code` | lowercasing and removing spaces, hyphens, dots, and slashes | `MG-44-08` and `mg4408` |
| `date` | reading it as a calendar date | `Mar 4, 2026` and `2026-03-04` |
| `currency` | reading it as an amount | `$1,250.00` and `1250` |

A numeric date such as `03/04/2026` is uncertain unless `--date-order`
sets `dmy` or `mdy`. An OCR read that differs only in characters OCR can't
tell apart, such as `O` and `0` or `l` and `1`, is uncertain, never a match.
A blank or unreadable field is uncertain too, and an uncertain check stops
the run.

### Write your own verifier

A package can add an `effects.kind` by registering a factory under the
`openadapt_flow.effect_verifiers` entry-point group. A plugin can't replace a
built-in kind. See the
[effect-verifier kit](https://github.com/OpenAdaptAI/OpenAdapt/blob/main/packages/flow/docs/EFFECT_KIT.md#shipping-your-own-adapter-plugin-sdk).

## 4. Attach the checks to the compiled program

```bash
openadapt flow bind-record-checks bundle --binding record-checks.yaml --check
openadapt flow bind-record-checks bundle --binding record-checks.yaml --out bundle-checked
```

The binding file names each save step and the checks it gets:

```yaml
schema: openadapt.record-check-binding/v1
workflow_name: claim-intake
steps:
  - step: step_012
    intent: "click 'Save'"
    effects:
      - {kind: record_written, match: {code: {param: claim_no}}, expected_count: 1, count_new_only: true}
      - {kind: field_equals, match: {code: {param: claim_no}}, field: member_no, value: {param: member_no}}
not_compared:
  visit_note: "free text the system stores in a different form"
```

Rules the command enforces:

- Each save needs a check that proves something changed (`record_written`
  with `count_new_only`, or `exact_new_set`).
- Each check selects its record through a run input.
- Every typed input is either compared by a check or listed under
  `not_compared` with a reason. `--check` prints that coverage and writes
  nothing.
- A check can't reference a secret.

With `--out`, it writes a new bundle and leaves the original unchanged.
Binding changes the program, so an earlier certification or qualification no
longer applies to the new bundle.

## 5. Confirm coverage

```bash
openadapt flow lint bundle-checked
```

`lint` reports, for every step that changes a record, whether it declares a
record check and which check level it reaches (surfacing same-screen checks so
you can raise `minimum_readback` where needed).

## Next

[Certify and qualify the workflow](certify-and-qualify.md).
