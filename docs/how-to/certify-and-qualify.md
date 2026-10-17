---
description: >-
  Check a compiled program against a policy, then test it against normal and
  faulty cases in the environment where it will run.
---

# Certify and qualify a workflow

Before a workflow saves data without someone watching each step, it goes
through three gates. Each one answers a different question.

| Gate | Question | Command |
|---|---|---|
| Lint | What does the program not cover yet? | `openadapt flow lint` |
| Certify | Does the program meet the policy's rules? | `openadapt flow certify` |
| Qualify | Does it do the right thing on normal and faulty cases, in this environment? | `openadapt flow qualify` |

Certification is a property of the program. Qualification is a property of
the program in one environment: a pass covers the environment it ran in and
nothing more.

## Lint

```bash
openadapt flow lint bundle
```

`lint` lists gaps as `error`, `warning`, or `info`. It exits 1 on an error.
Pass `--strict` to exit 1 on warnings too.

## Certify

```bash
openadapt flow certify bundle --policy clinical-write
```

A policy is a set of rules a program must meet before it may run, for
example "every step that saves has a right-record check". Two policies ship
with OpenAdapt:

- `clinical-write`, the default for `run`, for programs that change records.
- `permissive`, for local experiments.

You can also pass a path to your own policy YAML file, or read the policy from
a deployment file with `--config`.

## Qualify

Qualification runs the program against a test copy of the application that
can be reset between trials. It runs six cases, three trials each by default:

| Case | What changes | Required result |
|---|---|---|
| `representative` | Nothing | Completes, confirmed by reading the system of record |
| `fault-ambiguity` | A second copy of the save button appears | Stops |
| `fault-wrong-identity` | The save button is relabeled to a different action | Stops |
| `fault-stale-identity` | The screen goes blank at the save | Stops |
| `fault-weak-effect` | The record check is swapped for one that only reads the screen | Stops |
| `fault-missing-effect` | The record check is removed | Stops |

After each trial, a separate read of the system of record checks that the
normal case wrote exactly one correct record and that no fault case wrote
anything.

A fault case passes only when the engine stopped and the read-back shows
nothing was written. A run that reports success while the record shows
nothing counts as a silent wrong success, and one is enough to fail.

### What qualification needs

1. A compiled bundle.
2. A test copy of the application that you can reset.
3. A read-back that doesn't go through the screen: REST, SQL, FHIR, GraphQL,
   or a file export. A workflow whose only check is `ui_readback` can run the
   cases but can't be certified by qualification.

### Run a campaign in one command

On the `main` branch, one command runs every case from a `verify.yaml` file
that says how to sign in, reset, and read the record back:

```bash
openadapt-flow qualify bundle --verify verify.yaml --out runs/qual-1 --certify clinical-write
```

This form isn't in `openadapt-flow` 2.1.0; it is unreleased. A
shortened `verify.yaml`:

```yaml
schema_version: openadapt.verify/v1
minimum_effect_strength: independent_system_of_record
app:
  target: web
  name: OpenAdapt MockMed synthetic reference
  url: ${MOCKMED_BASE_URL}
  entry_url: ${MOCKMED_BASE_URL}?fault=ok&idempotency=demo#tasks
  version: sha256:${MOCKMED_APP_VERSION}
  reset:
    http: {method: POST, url: "${MOCKMED_BASE_URL}api/reset", body: {}}
verifier:
  kind: rest
  base_url: ${MOCKMED_BASE_URL}
  records_path: /api/db
  records_key: records
save_step: auto
inputs:
  source: recorded
campaign:
  id: public-demo-mockmed-qualified-campaign-v1
  trials: 3
  policy: clinical-write
```

This is `packages/flow/public-demo/mockmed-verify.yaml`, the file for the
MockMed test app. It has no `effects` list because the compiler took the
save's record checks from the demonstration. For your own app, add `effects`
or the shorter `record` block to say which record the save must create.
`${NAME}` reads an environment variable.

`reset` takes exactly one of `command`, `http`, or `python`. Before it runs
anything, `qualify` lists every problem it finds, such as a save step with no
right-record check.

Run against MockMed with the quickstart's bundle, this campaign produced:

```text
qualify PASS: 18 trial(s) in 71.2 s
```

with every representative trial `VERIFIED` by an exact record match, every
fault trial stopped with no write, and zero model calls (`main`, MockMed, a
Mac, 17 October 2026). The output directory holds:

```text
runs/qual-1/
  bundle/                             the certified bundle
  cases/<case>/trial-NN/              each trial's run report and read-back
  qualification/result.json           one entry per trial
  qualification/admission.local.json  the result bound into a local admission
  qualification/verdict.txt           the result, or why certification refused
  campaign-summary.json
  timing.json
  QUALIFICATION.md                    a summary to read
```

### With openadapt-flow 2.1.0

In the released version, the same cases run one at a time:

- `qualify from-demo` proposes the record, identity, and record-check pins
  from the demonstration and accepts them.
- `qualify drills` adds the five fault drills for the save.
- `qualify run-case` runs one case or drill, and `qualify run` imports case
  results.
- `qualify certify` combines the qualification and policy decisions.

OpenAdapt Desktop prepares the inputs that `qualify run-case` takes.

## Admission

`qualify --certify` signs a *local* admission with a local test key, and
production trust lists refuse that key. A run under the Standard or
Regulated profile needs a production admission for that exact program
version, passed to `run` with `--qualification-authority-file`.

On 14 October 2026, every entry in the
[public list of workflow admissions](https://openadapt.ai/production-workflow-admissions.json)
came from synthetic tests. To qualify a workflow in your own environment, see
[Engagements](../security/engagements.md).

## Next

[Run the workflow](run.md).
