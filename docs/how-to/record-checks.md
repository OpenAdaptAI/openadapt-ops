---
description: >-
  Tell OpenAdapt where the saved record lives so a run can read it back after
  each save, and choose how strong that check is.
---

# Add record checks

A record check reads the saved record back after a save, through a different
path from the screen that did the work. Without one, a run can't end
`VERIFIED`. Under the Standard and Regulated profiles, a run refuses to
perform a save that has no record check. Under the Demo profile, it needs
`--approve-unverified-writes` and ends `COMPLETED_UNVERIFIED` at best.

There are two halves:

- The **program** says what must be true after each save, for example
  "one new triage note for this patient".
- The **deployment** says where to read it: a REST or FHIR API, a read-only
  SQL query, a file drop, or a separate signed-in browser session. This lives
  in the `effects:` section of a deployment file and never in the program.

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

| Where the record is read | How | Strength |
|---|---|---|
| The system's API, database, or files: REST, GraphQL, FHIR, read-only SQL, a file or report drop, an email capture folder, a document store | `effects.kind` `rest`, `graphql`, `fhir`, `sql`, `file`, `document`, `email`, `document-hash` | Strongest. Reads the system of record, not the screen. |
| The app's own record page, opened by id in a separate, freshly signed-in, read-only browser session | `effects.kind: ui_readback` | Independent of the session that typed, but still a screen |
| The acting session clears what the screen remembers, opens the record again, and reads it | A check you show by demonstration | Can stop a run; never makes one `VERIFIED` on its own |
| The screen the run worked on | `effects.kind: onscreen` | Weakest. A consistency signal, not proof of a save. |

[How a save is checked](../explanation/verification.md#how-strong-a-read-back-is)
maps each one to what it can reach: `VERIFIED`, certification, and a Seal.
When the deployment can read more than one way, list them under
`effects.candidates` instead of `effects.kind`; Flow uses the strongest one
for each save.

### Read the record page in a separate session

Use `ui_readback` for a web app with no API or database to read. Configure
it with a separate read-only account, so the check never uses the session
that did the typing:

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

### Show how you'd check the save

For an app with no API, database, export, or web record page, such as a
desktop app or one reached over RDP or Citrix, show OpenAdapt how you'd
check a save yourself. Record the task, save, then clear what the screen
remembers, open the saved record again, and look at the fields:

```bash
openadapt flow record --with-check --out rec ...
```

After the save, Flow prompts "Now show how you'd check it saved." When you
stop, it lists the recorded events and asks where the check starts and which
regions show the values you typed. It writes them to `check.json` beside the
recording. For a recording made without `--with-check`, write the same file
with `check mark`:

```bash
openadapt flow check mark rec --start-event 14 --field patient_id=410,212,180,24
```

The check must contain a step that clears what the screen remembers: a
reload, a new search, or a window closed and reopened. Flow recognizes those
from the recording. Name one it can't recognize, such as a click on the
browser's reload button or a fresh sign-in, with
`--reset KIND@EVENT`, where `KIND` is `reload`, `new_search`,
`reopen_window`, or `fresh_session`. `compile` refuses a check with no
reset, a marked region that doesn't show the typed value, or a check that
types a secret.

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

### Re-read the acting screen

`onscreen` re-reads the value on the screen the run worked on. It's a
consistency signal: an app can show a value it never stored. Set it with
`effects.kind: onscreen`; `readback_region` and `readback_min_ratio` set the
region to read and the match threshold. Prefer a check you show by
demonstration, which reopens the record first.

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

`lint` reports, for every step that saves, whether it declares a record
check, and warns when a check reads the same screen that did the work.

## Next

[Certify and qualify the workflow](certify-and-qualify.md).
