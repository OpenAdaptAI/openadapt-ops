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

| Where the record is read | `effects.kind` | Strength |
|---|---|---|
| The system's API or database: REST, GraphQL, FHIR, read-only SQL, a file or report drop, an email capture folder, a document store | `rest`, `graphql`, `fhir`, `sql`, `file`, `document`, `email`, `document-hash` | Strongest. Reads the system of record, not the screen. |
| The app's own record page, opened by id in a separate, freshly signed-in, read-only browser session | `ui_readback` | Weaker. Independent of the session that typed, but it is still a screen. |
| The screen the run worked on | `onscreen` | Weakest. A consistency signal, not proof of a save. |

Use `ui_readback` when there is no API or database to read. Configure it
with a separate read-only account so the check never uses the session that
did the typing:

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
    row_selector: "tr.encounter"
    fields:
      id: { attribute: data-id }
      note: { selector: "td.note" }
    identity:
      reader: { selector: "#patient-mrn" }
      value: { param: patient_id }
      field: patient_id
```

How strength affects outcomes and certification is explained in
[How a save is checked](../explanation/verification.md).

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
