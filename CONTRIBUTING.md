# Contributing to Drake

Thank you for your interest in contributing to Drake! We welcome contributions
from everyone, whether you are fixing a bug, proposing a feature, improving
documentation, or helping with governance.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
  - [Report a Bug](#report-a-bug)
  - [Suggest a Feature](#suggest-a-feature)
  - [Improve Documentation](#improve-documentation)
  - [Submit a Pull Request](#submit-a-pull-request)
- [Development Setup](#development-setup)
- [Pull Request Guidelines](#pull-request-guidelines)
- [Developer Certificate of Origin (DCO)](#developer-certificate-of-origin-dco)
- [Getting Help](#getting-help)

## Code of Conduct

This project is governed by the [Contributor Covenant](CODE_OF_CONDUCT.md).
By participating, you agree to uphold its standards. Report unacceptable
behavior to the maintainers at the contact address listed in the
CODE_OF_CONDUCT.md.

## How to Contribute

### Report a Bug

If you find a bug, please open a [bug report](.github/ISSUE_TEMPLATE/bug_report.md)
and include:

- A clear, descriptive title
- Steps to reproduce the issue
- Expected vs. actual behavior
- Environment details (OS, Python version, git version, etc.)
- Screenshots or logs if applicable

### Suggest a Feature

Open a [feature request](.github/ISSUE_TEMPLATE/feature_request.md) with:

- A clear title and description of the problem you want to solve
- Your proposed solution and any alternatives you considered
- How the feature fits into Drake's governance architecture

### Improve Documentation

Documentation improvements are always welcome. If you find something unclear,
outdated, or missing, feel free to open an issue or submit a PR.

### Submit a Pull Request

See [Pull Request Guidelines](#pull-request-guidelines) and the
[Developer Certificate of Origin](#developer-certificate-of-origin-dco) below.

## Development Setup

Drake is a governance framework—there is no build step or runtime server.

To validate changes locally:

```bash
git clone https://github.com/sv-copilot/drake.git
cd drake
bash scripts/ci_preflight.sh
```

The CI preflight script runs markdown checks, JSON validation, and branch
convention checks. It is the same set of checks used in GitHub Actions.

## Pull Request Guidelines

1. **Scope each PR to one concern.** Keep changes small and focused. If your
   change touches multiple areas, split it into separate PRs.
2. **Branch from `main` and target `main`.** Use a descriptive branch name
   such as `agent/my-change` or `fix/my-bug`.
3. **Write a clear PR description.** Explain what the change does, why it is
   needed, and how it was validated.
4. **Run validation before opening.** From the repo root:
   ```bash
   bash scripts/ci_preflight.sh
   ```
5. **Include the DCO sign-off.** Every commit must include a `Signed-off-by`
   trailer (see below).
6. **Respond to feedback.** Maintainers may request changes. Please address
   them promptly.

## Developer Certificate of Origin (DCO)

This project requires all contributors to accept the
[Developer Certificate of Origin](https://developercertificate.org/). The DCO
is a lightweight attestation that you have the right to submit your
contribution under the project's license (Apache 2.0).

### How to Sign Off

Add a `Signed-off-by` trailer to each commit:

```
Signed-off-by: Your Name <your.email@example.com>
```

If you are using `git commit`, use the `-s` flag:

```bash
git commit -s -m "docs: add contribution guidelines"
```

If you are using the GitHub web UI, add the trailer manually to the commit
message body.

### What the DCO Says

```
Developer Certificate of Origin
Version 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I have
    the right to submit it under the open source license indicated in
    the file; or

(b) The contribution is based upon previous work that, to the best of
    my knowledge, is covered under an appropriate open source license
    and I have the right under that license to submit that work with
    modifications, whether created in whole or in part by me, under the
    same open source license (unless I am permitted to submit under a
    different license), as indicated in the file; or

(c) The contribution was provided directly to me by some other person
    who certified (a), (b) or (c) and I have not modified it.

(d) I understand and agree that this project and the contribution are
    public and that a record of the contribution (including all personal
    information I submit with it, including my sign-off) is maintained
    indefinitely and may be redistributed consistent with this project
    or the open source license(s) involved.
```

### Why DCO Instead of CLA

Drake uses the DCO rather than a Contributor License Agreement (CLA) because
it is simpler, less bureaucratic, and more aligned with open source norms. The
DCO places the responsibility on the contributor to certify their work without
requiring a separate legal agreement.

## Getting Help

- Open a [discussion](https://github.com/sv-copilot/drake/discussions) for
  questions and ideas
- File an [issue](https://github.com/sv-copilot/drake/issues) for bugs or
  feature requests
- Read [`docs/getting-started.md`](docs/getting-started.md) for the minimal
  adoption walkthrough
