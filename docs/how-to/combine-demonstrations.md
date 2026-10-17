---
description: >-
  Turn inputs into parameters, learn a program from several demonstrations,
  loop over a worklist, and chain programs across applications.
---

# Build a program from several demonstrations

One demonstration compiles into a straight list of steps with fixed values.
This page covers the ways to turn that into a program that takes inputs,
handles more than one path, repeats over a list, or crosses applications.

## Make typed values into inputs

When you type into a labeled field, `compile` proposes an input named after
the label, for example "Insurance No." becomes `insurance_no`. Nothing is
applied silently. On a terminal, `compile` asks you to confirm, rename, mark
as secret, or keep each one as a fixed value. In a script:

```bash
openadapt flow compile rec --out bundle --name intake --accept-params insurance_no,dob
openadapt flow compile rec --out bundle --name intake --params-from decisions.json
```

`decisions.json` maps each proposed name to
`{"action": "confirm" | "rename" | "secret" | "constant", "name": "..."}`.
Proposals you don't list stay fixed values. A `--param` given at recording
time always wins over a proposal.

At run time, pass values with `--param NAME=VALUE` or, to keep them out of
the process list, `--params-file params.json`.

## Learn from several demonstrations

Record the same task two or more times with different data, or along
different paths, then induce one program from the recordings:

```bash
openadapt flow induce rec1 rec2 rec3 --out program --name intake
```

`induce` lines the recordings up to find what is the same, what changes
(inputs), what repeats (loops), and where the paths split (branches). It uses
no model. When the recordings don't settle a branch condition or a value, it
refuses to write the program and prints a `record-next:` list of the extra
demonstrations it needs. `--held-out` also checks each recording against a
program learned from the others.

When a program has an open question, `disambiguate` asks it as a multiple
choice:

```bash
openadapt flow disambiguate program --interactive --write
```

## Repeat over a worklist

To run one compiled task once per row of a CSV or JSON list:

```bash
openadapt flow for-each bundle --records worklist.csv --out program
openadapt flow run program --worklist worklist.csv ...
```

Each column maps to the input with the same name, or use
`--map COLUMN=PARAM`. Every column must map to a known input that isn't a
secret. A list longer than `--max-iterations` (default 1000) is refused.

## Chain programs across applications

A compiled program belongs to one surface. For a task that reads from one
application and writes to another, compile one program per application and
chain them:

```bash
openadapt flow compose \
  --child lookup=bundles/portal-lookup \
  --child entry=bundles/emr-entry \
  --handoff lookup.member_id=entry.member_id \
  --out composed --name referral
```

`--handoff` copies a value that the first program confirmed into an input of
the next one; if that evidence is missing, the run stops. Children run in
`--child` order unless you give `--after NAME=PRED`. By default a child
starts only after the one before it ended `VERIFIED`.

## Keep secrets out of programs

Mark secret fields at recording time with `--secret FIELD`, or choose
"secret" for a proposal at compile time. A secret value is never written to
the recording or the program. At run time it comes from the environment
variable `OPENADAPT_FLOW_SECRET_<FIELD>`.
