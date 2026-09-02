# Seal as an RL reward

The Seal is a verifiable reward. An episode earns reward 1 only when a tier-2
or tier-3 oracle reads the required terminal effect from the system of record
and the outcome is `verified`. Screen-only evidence (tier 0 or 1) can drive a
local experiment, and it is never certified. A reward receipt is not an
Execute Seal: it verifies the terminal effect of one episode and says nothing
about how the model acted to get there. An episode the oracle could not score
(`reconciliation_required`, `failed_platform`) is dropped from the batch. It
is never paid 0. A trainer that folds those into zero is training on platform
noise, which is the failure this contract exists to stop.

The contract types are `RewardContractV1`, `RewardCertificateV1`,
`RewardOutcomeV1`, and `RewardEvidenceReceiptV1` in
[`openadapt-types`](https://github.com/OpenAdaptAI/openadapt-types/blob/main/docs/REWARD.md).
The pure scorer is `openadapt_types.score`.

## What runs where

| Node | Runs | Holds |
|---|---|---|
| Organization worker (inside the customer network) | The reward worker, the oracle read, the MockMed or real system of record | Records, the oracle recipe, the calibration corpus, evidence bytes. None of these leave. |
| OpenAdapt control service (off the high-volume path) | Contract registry, certificate issue, revocation | Contracts, certificates, the revocation list, privacy-safe receipts |
| Trainer node | The policy, rollouts, the optimizer | The checkpoint, episode ids, the receipts it fetched |

The trainer sees ids, digests, a tier, an outcome, a scalar, and a certificate
state. It cannot read the corpus or the record from a receipt.

## Outcome to scalar

Every `reward_outcome` has exactly one scoring class. The class decides whether
a scalar exists.

| `reward_outcome` | Class | Scalar (default `RewardScoringPolicyV1`) |
|---|---|---|
| `verified` | admitted positive | `verified_reward` = 1.0 |
| `halted_before_effect` | zero or penalty | `halted_before_effect_reward` = 0.0 |
| `refused` | zero or penalty | `refused_reward` = 0.0 |
| `rejected_policy` | zero or penalty | `rejected_policy_reward` = 0.0 |
| `wrong_effect` | zero or penalty | `wrong_effect_reward` = -1.0 |
| `reconciliation_required` | unscored | none |
| `failed_platform` | unscored | none |

`certified` on a receipt is a separate column from the scalar. It is true only
when all four hold: oracle tier 2 or 3, a certificate that is current at that
policy update, a `calibration_corpus_digest`, and a `calibration_scope`. The
scope is `synthetic` or `production`. Today the only certificate anyone can
compute is `synthetic` scope, calibrated on MockMed and ExtraDup. A
`production` scope needs the Phase-1 calibration on a held-out corpus, which
is not published. Show the scope beside the word certified;
`production_certified` on the receipt is that check.

`score()` returns `scalar=None` for an unscored outcome. The receipt refuses a
`scalar_reward` on one, and the contract cannot declare `uncertain_episodes`
or `platform_failures` as anything but `unscored`. A `verified` scalar must be
positive; every other scored outcome is zero or a declared penalty.

```python
from openadapt_types import RewardOutcomeV1, score

scalar, certified, development_only = score(
    RewardOutcomeV1.VERIFIED,
    tier=2,
    certificate=certificate,
    policy_update=120,
)
```

`development_only` is true at tier 0 or 1. A receipt that claims `certified`
at tier 0 does not validate; the validator raises
`RewardCertificationRefused`.

## Wire a trainer

The reward worker is `openadapt-flow serve-reward` (as of openadapt-flow#452).
It runs inside the customer network, reads the system of record once after
each episode, and signs a `RewardEvidenceReceiptV1` with a local Ed25519 key under
`~/.openadapt/reward-ref/`. A trainer submits an episode descriptor and gets
the receipt back. It never gets a credential for the store.

| Route | Body in | Body out |
|---|---|---|
| `GET /health` | none | issuer, key fingerprint, contract digest, oracle tier |
| `POST /v1/rewards` | the episode descriptor | the self-signed envelope, 200, receipt under `receipt` |
| `GET /v1/rewards/{receipt_id}` | none | the stored envelope |
| `POST /v1/graders/openai` | `{"sample": ..., "item": ...}` | `{"score": 0..1, ...}` or 422 |

Every route but `/health` needs `Authorization: Bearer <token>`. The envelope
carries `issuer: self_signed`, `execute_seal: false`, `production_seal: false`,
`flow_governed_policy: false`, `unscored`, and the receipt. The same
`episode_id` twice returns 409; a reward is issued once. A descriptor that
names a different contract digest returns 422.

The descriptor is the shape `openadapt_evals.reward.receipts.EpisodeDescriptor`
sends: `episode_id`, `policy_checkpoint_id`, `policy_update`,
`reward_contract_digest`, and optional `task_id`, `environment_id`, and
`metadata`. The record the oracle reads comes from `metadata.oracle_identity`,
an `oracle_identity` field beside it, or a registration the environment made
with `RewardWorker.begin_episode(episode_id, identity)` before the rollout.
Its keys must match the contract's `identity_keys` exactly.

The trainer-side adapters live in `openadapt_evals.reward`. They call
`openadapt_types.score`, read the receipt's own fields, and refuse the
combinations a trainer must never accept: an unscored episode is removed from
its GRPO group, a `development_only` receipt is never certified, and in
`require_certified` mode an expired certificate stops the run.

### OpenAI Agent RFT grader

OpenAI documents one custom-grader contract, the `python` grader's
`grade(sample, item) -> float`, and that grader runs with no network access.
A hosted RFT job can't reach this worker. The route exists for a self-hosted
loop that already speaks that shape.

```bash
curl -s -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"sample": {}, "item": {"episode_id": "episode_honest_01",
       "policy_checkpoint_id": "policy_checkpoint_mockmed_0", "policy_update": 0,
       "reward_contract_digest": "'$DIGEST'",
       "metadata": {"oracle_identity": {"patient_id": "patient-honest-0001"}}}}' \
  http://127.0.0.1:8788/v1/graders/openai
```

The `item` carries the episode descriptor fields by name. The grader schema
has no "do not score" value, and OpenAI's rule is that an exception or a bad
float is marked invalid and scored 0. This worker refuses that: an unscored
episode answers 422 with `error: unscored`, and your wrapper must drop the
sample before any grader sees it.

### TRL reward function

TRL's `GRPOTrainer` combines a `None` reward with `nansum`, so with one reward
function a `None` row trains as 0.0. `CertifiedRewardFunction` drops an
unscored episode a different way: it gives the episode the mean reward of its
scored group-mates, so its advantage is zero and it contributes no gradient.

```python
from openadapt_evals.reward import HttpRewardEndpoint
from openadapt_evals.reward.trl import CertifiedRewardFunction

reward = CertifiedRewardFunction(
    HttpRewardEndpoint(
        "http://127.0.0.1:8788",
        headers={"Authorization": f"Bearer {token}"},
    ),
    reward_contract_digest=contract_digest,
    policy_checkpoint_id="policy_checkpoint_mockmed_0",
    num_generations=8,
    require_certified=True,
)

trainer = GRPOTrainer(model=model, reward_funcs=[reward], args=args, train_dataset=dataset)
```

The dataset carries an `episode_id` column, one per completion. The policy
update is `trainer_state.global_step`. After each batch,
`reward.metadata_columns()` returns per-sample columns (`reward_outcome`,
`reward_certified`, `reward_calibration_scope`, `reward_certificate_state`,
`reward_unscored`) to log beside the scalars. Pass `reward.as_async()` instead
of `reward` when TRL should await it concurrently with other reward functions.
`require_certified=False` is the switch for a tier-0 or tier-1 development
run; every receipt is then logged as `development_only`.

### verl reward manager

verl's per-sample `compute_score` hook must return a number for every sample,
so it can't drop an unscored episode from its group. `CertifiedRewardManager`
is the batch hook instead. It fetches one receipt per sample and gives every
unscored sample the mean of its scored `uid` group-mates. The per-sample flags
go out in `reward_extra_info`.

```python
from openadapt_evals.reward.verl import register_with_verl

register_with_verl()   # registers "openadapt_certified"; call before the trainer starts
```

```yaml
reward_model:
  reward_manager: openadapt_certified
  reward_kwargs:
    endpoint_url: http://reward-worker:8788
    reward_contract_digest: sha256:...
    policy_checkpoint_id: policy.checkpoint.0001
    require_certified: true
```

Each sample's `extra_info` must carry `episode_id`. The policy update comes
from `data.meta_info["global_steps"]` when verl sets it, else from
`policy_update`.

### Prime Intellect environment

`openadapt-mockmed-extradup` is a `verifiers` `SingleTurnEnv` in
`environments/openadapt_mockmed_extradup/` of `openadapt-evals`. Each task
is one synthetic CREATE. The policy answers with a JSON action report, the
environment replays it on a fresh in-memory store, and the reward is 1.0 if
and only if the tier-2 read of that store is `VERIFIED`. There is no tier-0
path in the code; `load_environment(score_from_screen=True)` raises. Its
eval dataset carries the six labeled reward-hacking rows (`dup`, `extra`,
`omit`, `unsubmit`, `claim`, `screen_only`) so you can confirm the reward
fails them closed before you train.

The package is not on PyPI or the Prime hub yet, so install it from the
repository:

```bash
uv pip install "verifiers>=0.3.1,<0.3.2" \
  "openadapt-mockmed-extradup @ git+https://github.com/OpenAdaptAI/openadapt-evals@main#subdirectory=environments/openadapt_mockmed_extradup"
uv run vf-eval openadapt-mockmed-extradup -m gpt-4.1-mini -n 8 -r 1
```

To watch it fail closed without a model, serve the scripted policy and let
the model name select the case:

```bash
python scripted_policy.py serve --port 8123 &
SCRIPTED_POLICY_KEY=scripted vf-eval openadapt-mockmed-extradup \
  -m scripted/dup -b http://127.0.0.1:8123/v1 -k SCRIPTED_POLICY_KEY -n 2 -r 1
```

`check_fails_closed.py` runs all seven cases and exits non-zero if any
hacking case averages above 0.0. The full argument table is in the
[environment README](https://github.com/OpenAdaptAI/openadapt-evals/blob/main/environments/openadapt_mockmed_extradup/README.md).

## The certificate

`RewardCertificateV1` is a signed bound on one reward contract's false-accept
rate. Its fields:

| Field | Meaning |
|---|---|
| `certificate_id` | Revocation key. The issuer checks the revocation list, as for every other admission. |
| `reward_contract_digest` | The `RewardContractV1` this bound applies to |
| `checker_configuration_digest` | The checker configuration the bound was calibrated for |
| `epsilon` | Upper bound on P(false-accept) |
| `delta` | One minus the confidence of that bound |
| `threshold` | The checker decision threshold the bound was calibrated at |
| `calibration_corpus_digest` | Names the corpus. The corpus itself stays private. |
| `calibration_scope` | `synthetic` or `production`. What corpus family the bound was calibrated against. |
| `issued_at_policy_update` | The policy update the certificate was issued at |
| `expiry_policy_updates` | How many policy updates it stays current |
| `issuer` | `self_signed` or `organization`. A self-signed certificate may carry only `synthetic` scope; the validator refuses the other combination. |
| `issued_at`, `issuer_key_id`, `signature` | Ed25519 signature over the unsigned payload |

Expiry counts policy updates, not hours. A certificate issued at update `i`
with expiry `n` is current for updates `i` through `i + n - 1`;
`is_current(policy_update)` answers it. On-policy training breaks the
exchangeability the bound assumes, so the certificate expires on a schedule
of updates and a new one is issued against the current policy's trajectory
distribution. An expired, un-renewed certificate means `certified` is false on
every receipt after it, and a certified arm halts.

`RewardContractV1.certificate_policy` states the weakest certificate the
contract accepts (`epsilon`, `delta`, `threshold`, corpus digest, expiry).
`RewardCertificateV1.satisfies(policy)` is the check.

The MockMed worker signs its own certificate, so every certificate it issues
is `self_signed` and `synthetic`. That is enough to prove the plumbing and to
bound a synthetic run. It says nothing about a production checker. An
`organization` issuer holds the calibration corpus and the signing key, and
it is the only issuer that can state `production` scope.

The re-certification cadence, the vacuity check, and the kill criteria are
registered in the public
[certified-reward RL preregistration](https://github.com/OpenAdaptAI/openadapt-evals/blob/main/docs/preregistrations/PREREGISTRATION_CERTIFIED_REWARD_RL_2026_08_25.md)
(tag `prereg-certified-reward-rl-2026-08-25`).

## Run it locally with MockMed

The worker and its `--seed-mockmed` fixtures are as of openadapt-flow#452.

```bash
pip install 'openadapt-flow[reward]'
openadapt-flow serve-reward --seed-mockmed --port 8788
```

`--seed-mockmed` writes two contract bundles and their fixtures under the data
directory and serves the tier-2 one when `--contract` is omitted.
`contracts/mockmed` reads `mockmed/records.json` through the `json_file`
recipe, channel `file`, tier 2. Before it signs the synthetic certificate, the
seed runs 300 ExtraDup trials through the bundle's own judge, and
`calibration.json` beside the certificate records the trial count and the
false-accept count so you can recompute the bound. The certificate carries
`calibration_scope: synthetic` and `issuer: self_signed`.

`contracts/mockmed-tier0` reads `mockmed/screen.json` through the
`screen_dump` recipe, channel `ocr`, tier 0. The dump shows the banner-lie
episode as saved.

Three episodes to post, with the bearer token and contract digest the banner
prints:

```bash
TOKEN=...    # printed on start, also in ~/.openadapt/reward-ref/token
DIGEST=...   # printed on start as "digest", also GET /health
post() { curl -s -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d "$1" http://127.0.0.1:8788/v1/rewards; }

post '{"episode_id":"episode_honest_01","policy_checkpoint_id":"policy_checkpoint_mockmed_0",
       "policy_update":0,"reward_contract_digest":"'$DIGEST'",
       "metadata":{"oracle_identity":{"patient_id":"patient-honest-0001"}}}'
# -> reward_outcome verified, scalar_reward 1.0, certified true,
#    calibration_scope synthetic

post '{"episode_id":"episode_lie_01","policy_checkpoint_id":"policy_checkpoint_mockmed_0",
       "policy_update":0,"reward_contract_digest":"'$DIGEST'",
       "metadata":{"oracle_identity":{"patient_id":"patient-lie-0002"}}}'
# -> reward_outcome wrong_effect, scalar_reward 0.0. The screen said saved.
#    The store holds no record.

post '{"episode_id":"episode_dup_01","policy_checkpoint_id":"policy_checkpoint_mockmed_0",
       "policy_update":0,"reward_contract_digest":"'$DIGEST'",
       "metadata":{"oracle_identity":{"patient_id":"patient-dup-0003"}}}'
# -> reward_outcome wrong_effect. Two Triage records where the contract
#    allows one.
```

Then the tier-0 worker, in a second terminal, with that bundle's own digest:

```bash
openadapt-flow serve-reward --contract ~/.openadapt/reward-ref/contracts/mockmed-tier0 --port 8789
post '{"episode_id":"episode_lie_02","policy_checkpoint_id":"policy_checkpoint_mockmed_0",
       "policy_update":0,"reward_contract_digest":"'$DIGEST0'",
       "metadata":{"oracle_identity":{"patient_id":"patient-lie-0002"}}}'
# -> reward_outcome verified, development_only true, certified false.
#    The OCR dump agrees with the banner. That is why tier 0 cannot certify.
```

The banner lie scores 0 here because the seeded contract declares
`wrong_effect_reward: 0.0`. The contract default is -1.0. A penalty is a
training choice the contract states; the worker never picks one.

The same lie, scored two ways with no model and no GPU, is the MockMed proof
in `openadapt-evals`. It runs scripted rollouts for the gold CREATE and each
ExtraDup family (`dup`, `extra`, `omit`, `unsubmit`, `claim`) plus an
`oracle_outage` condition, at least three trials each, through a tier-0
`visual_only` reward and a tier-2 `certified_sor` reward:

```bash
python -m openadapt_evals.reward.proof --json out.json --markdown out.md
```

## Related pages

- [Effect verification](../concepts/effect-verification.md): the oracle, the
  three-valued verdict, and the tier ladder.
- [The Seal](seal.md) and [Invoke a program: Seal or halt](execute-api.md):
  the Execute receipt this reward receipt is not.
- The [ExtraDup kit](https://github.com/OpenAdaptAI/openadapt-evals/blob/main/openadapt_evals/extradup/README.md)
  in `openadapt-evals`: the mutants a screen-only checker passes and a
  system-of-record oracle fails.
