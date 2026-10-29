# Release Status

## 1.0.0: Released

NexaMem `1.0.0` was [published to production PyPI](https://pypi.org/project/nexamem/1.0.0/) on 2026-10-29 from tag `v1.0.0` at commit `8a251619da8149235f8b03d06a381cec6518e055`. This stability release includes authentication, lifecycle, retention, and optional integration improvements. Package and module versions are `1.0.0`, with the Production/Stable classifier. The maintainer explicitly approved the main fast-forward, stable tag, and production upload. Existing PyPI/TestPyPI versions are immutable: changed package content requires a new version.

| Area | State |
| --- | --- |
| Python floor | Raised to 3.11; CI matrix targets 3.11, 3.12, 3.13 |
| Dependency tooling | pip, venv, pip-tools, setuptools, build, Twine; no uv requirement |
| Unit coverage | Complete offline package suite, including legacy modules and real framework interfaces; blocking 90% overall line-coverage gate |
| Regression fixes | Storage index updates, safe file writes, SQLite closure, legacy initialization, metrics deadlock, audit stream reads, Redis scope handling and TLS |
| CI | Consolidated reusable workflow; tests, Ruff, mypy, and installed artifacts are blocking |
| Distribution verification | Wheel and sdist metadata plus independent clean installations |
| Strict typing | All 33 package source files pass strict mypy without relaxing settings |
| Authentication | Renewable Entra Redis credentials, owned cleanup, Managed Redis endpoint defaults; live Azure validation still pending |
| Async/lifecycle | Thread-backed local data I/O, cancellation serialization, facade context managers and borrowed-storage semantics |
| Retention | Logical per-record expiry and explicit purge; not audit/backup erasure or background physical deletion |
| Integrations | LangChain, AutoGen, Semantic Kernel, Agent Framework; Foundry hosting documentation, not a fifth adapter |
| Cross-platform verification | Stable commit `8a25161` passed all 17 reusable CI jobs on main and again in the tag publication workflow |
| Stable verification | CI and CodeQL passed; production archive digests match CI artifacts; four additional clean-install smoke tests passed |
| Publication | `1.0.0` published to production PyPI through trusted publishing; preceding `1.0.0rc1` verified on TestPyPI |
| PR enforcement | Maintainer will enable required PRs after v1 deployment; no repository protection settings changed during release |

## Remote Verification

Stable commit `8a25161` passed [CI run 40923519770](https://github.com/microsoft/nexamem/actions/runs/40923519770) and [CodeQL run 40923518876](https://github.com/microsoft/nexamem/actions/runs/40923518876). All 17 CI jobs and both CodeQL jobs succeeded. Tag `v1.0.0` then passed [production publish workflow 40925594891](https://github.com/microsoft/nexamem/actions/runs/40925594891): stable-version validation, all 17 reusable CI jobs, and the production PyPI upload succeeded; the TestPyPI job was skipped.

The production PyPI JSON API reports these SHA-256 digests, which exactly match the downloaded production workflow artifacts:

```text
nexamem-1.0.0-py3-none-any.whl  6d2f60991d2cafbe2c193a2ad8283151d8b5d70f2295c0e6dea9ab71085af115
nexamem-1.0.0.tar.gz           24f2d67d497f239121f93f5dd0fec2c3da4dbd694bd867f45d1e8cde7c7b80b2
```

Both production-matching CI archives passed strict Twine checks and four independent clean-install smoke tests on Windows/Python 3.11.12 and 3.13.15, outside the checkout. Dependencies came from the approved package feed. These checks verified version metadata, local persistence, async operations, logical expiry, legacy APIs, and shipped adapter modules without framework extras.

Direct archive retrieval from `files.pythonhosted.org` failed with a TLS handshake error on this workstation, and the approved package mirror had not yet indexed 1.0.0. Certificate verification was not disabled. Therefore the additional local installs used CI archives checked against production PyPI's published digests, not independently downloaded production archives. Post-release documentation updates do not rebuild, replace, or retag the published package; its embedded README reflects the preparation state at the release commit.

### Earlier Verification

Commit `79f0d66` passed [CI run 40905994705](https://github.com/microsoft/nexamem/actions/runs/40905994705) and [CodeQL run 40905993954](https://github.com/microsoft/nexamem/actions/runs/40905993954). All nine Python 3.11/3.12/3.13 test jobs across Linux, macOS, and Windows, quality checks, package build, and six clean distribution-install jobs succeeded. This verifies that baseline, not a subsequently changed candidate or live Azure deployment.

Candidate commit `442f201` passed [publish workflow 40916874870](https://github.com/microsoft/nexamem/actions/runs/40916874870), including version validation, all 17 reusable CI jobs, and TestPyPI publication. The production PyPI job was skipped. The [TestPyPI release](https://test.pypi.org/project/nexamem/1.0.0rc1/) contains wheel and source archives whose SHA-256 digests exactly match that workflow's build artifacts:

```text
nexamem-1.0.0rc1-py3-none-any.whl  004c13c2fdbe31052a33448ef9c0f5bb3e52995233d4cc9713e0faa558af1be2
nexamem-1.0.0rc1.tar.gz           1391d57c68d9e305e3dd89fdde25efd2ce1cd09ff32812167668e68fb2a13e8b
```

Both downloaded TestPyPI archives passed strict Twine checks and independent clean installations on Windows/Python 3.11.12 and 3.13.15. Dependencies came from the approved package feed, not a combined TestPyPI/PyPI index. Isolated smoke tests ran outside the checkout and verified version metadata, local persistence, async operations, logical expiry, legacy APIs, and shipped adapter modules. This documentation follow-up does not rebuild or replace the published archives.

## Local Verification

- Windows/Python 3.11.12 and 3.13.15: 203 offline tests pass on each runtime, with 92.61% whole-package line coverage (3290 statements), including legacy modules and all four adapters.
- Strict mypy passes across 33 source modules on both runtimes. Ruff lint and formatting checks pass; both development environments pass `pip check`.
- Eight local README, SQLite persistence, and framework examples execute successfully on both Python 3.11 and 3.13. A fresh Python 3.11 source install passes `pip check` and all four base examples without framework extras. Local documentation links and example syntax are checked separately from live-service behavior.
- Validation-only wheel and sdist in `dist-release/frameworks/` pass strict Twine checks and independent clean base installations on Python 3.11 and 3.13. Smoke tests cover local CRUD, logical expiry, context managers, legacy APIs, and shipped adapter modules without installing framework extras.
- The Windows/Python 3.13 development lock was regenerated with pip-tools. Stable metadata is `1.0.0`; prior artifacts remain tied to their original versions and must not be replaced under a reused version.

## Stable Preparation Verification

Before committing and publishing the stable version, these local preparation checks completed on 2026-10-29. They are historical preparation evidence; production verification is recorded above.

- Both version declarations match `1.0.0`, packaging accepts it as stable, and the intended classifier is Production/Stable. The version was unused on production PyPI at the preparation check; no upload was attempted.
- All 203 offline tests pass on Python 3.11.12 and 3.13.15 with 92.61% whole-package line coverage (3290 statements). Strict mypy passes across 33 modules on both runtimes; Ruff lint/format (51 files), both dependency checks, and editor diagnostics pass.
- Local links and heading anchors resolve across 11 documents; all 14 Python examples parse. Nine offline README, SQLite, framework, and legacy examples run unchanged outside the checkout on each runtime, for 18 successful executions. Credentialed service/exporter examples were not executed.
- Fresh `1.0.0` wheel and source archives in `dist-release/1.0.0-preparation/` pass strict Twine checks and four independent clean-install smoke tests (both archive formats on both runtimes). Dependencies came from the approved feed; isolated installed-package checks verify version metadata, local persistence, async operations, expiry, legacy APIs, and shipped adapter modules. These are local preparation artifacts, not production uploads.

The approved stable commit subsequently passed remote CI, CodeQL, production publishing, digest checks, and production-matching installed-distribution checks as recorded above.

## Remaining Work

- Validate live Azure/Foundry networking, data-plane permissions, token refresh/reconnect/failover, and intended Managed Redis endpoint policy before production use.
- Enable the maintainer's planned required-PR protections after release. Production trusted publishing succeeded; environment access and tag restrictions remain a separate repository-governance decision, not a guarantee supplied by a successful upload.
- Recheck direct PyPI installation when this workstation's network policy and approved mirror indexing permit it. The verified workflow archives match production registry digests; the local direct-download limitation remains disclosed above.

Passing local tests does not establish live Azure compatibility, regulatory compliance, automatic encryption, quota/PII enforcement, or physical-erasure guarantees. The documentation records those limitations rather than promising them.

See [changes](CHANGELOG.md), [contributor commands](CONTRIBUTING.md), [architecture](NEW_ARCHITECTURE.md), and [security](SECURITY.md).