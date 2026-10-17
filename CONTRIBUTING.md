# Contributing

Thanks for contributing to OpenAdapt. A few things keep the project healthy and
keep the company able to steward it.

## Licensing of your contributions

This repository's code is MIT-licensed, and your contribution goes in under the
MIT License. Two things cover it.

1. **Developer Certificate of Origin (required now).** Add a `Signed-off-by`
   line to every commit, certifying you wrote the change or that you have the
   right to submit it under the project license:

   ```
   git commit -s -m "fix: ..."
   ```

   This produces `Signed-off-by: Your Name <you@example.com>`. The full text is
   at https://developercertificate.org.

2. **Contributor License Agreement (published, not yet enforced).** The
   canonical text is
   [`openadapt-flow/CLA.md`](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/CLA.md)
   for individuals, and
   [`openadapt-flow/CCLA.md`](https://github.com/OpenAdaptAI/openadapt-flow/blob/main/CCLA.md)
   for companies whose employees contribute on company time. It gives MLDSAI
   Inc. an explicit copyright and patent license, which the MIT License alone
   doesn't provide, and it keeps the option of relicensing the combined work
   later.

   You don't agree to the CLA by opening a pull request. Nothing is implied.
   You agree when you sign, either through the automated CLA check once that
   check is turned on for this repository, or by email. Until the check is on,
   the DCO sign-off and the MIT License are what govern your contribution.

OpenAdapt is open-core. MLDSAI Inc. sells proprietary products built on this
code, including a hosted control plane, and your contribution may end up in
them. The MIT License already permits that. The CLA says it out loud so nobody
is surprised.

## Pull request guidelines

- Use **Conventional Commits** for titles and commits (`feat:`, `fix:`,
  `docs:`, `chore:`, `refactor:`, `test:`, `ci:`).
- Keep PRs focused; separate mechanical changes from behavior changes.
- Add or update tests for any behavior change.
- Prefer honest, measured claims in docs. If something is experimental, say so.

## Source-availability boundary

OpenAdapt is open-core. Do not add private crown-jewel artifacts (grown
hardening corpus, tuned adversary params, deployment-derived thresholds,
per-system-of-record oracle/connector recipes, real-EMR datasets) to this public
repository. Interfaces and mechanisms are public; data, recipes, and empirical
tuning are private. See the OpenAdapt Source-Availability Boundary policy.

## Reporting security issues

Do not file security problems as public issues; see `SECURITY.md` if present, or
email security@openadapt.ai.
