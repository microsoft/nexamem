# Contributing

Use Python 3.11, 3.12, or 3.13 and the [pip/venv setup](INSTALLATION.md). Keep changes compatible with 3.11. Add pytest regressions under `tests/`; do not use live services for unit coverage.

## Required Checks

```shell
python -m pip check
python -m pytest tests/ -m "not integration" --cov=nexamem --cov-report=xml --cov-report=term-missing --cov-fail-under=90
python -m ruff check src/ tests/ build_and_test.py
python -m ruff format --check src/ tests/ build_and_test.py
python -m mypy src/
```

Coverage is overall **line coverage**, with a 90% minimum across the complete package, including legacy modules. Do not exclude difficult backends, policy code, abstract code, or legacy paths to meet the threshold. Fakeredis and mocked identity services are acceptable unit dependencies. Report live-service validation separately.

Strict mypy is a blocking gate and currently passes across the package. Do not replace failures with `|| echo`, blanket ignores, or relaxed settings. Ruff is the formatter; Black is not required.

Validate local documentation links and heading anchors, parse Python examples, and execute the offline README, SQLite, framework, and legacy examples before a release. Run examples outside the checkout with the installed package. Azure and exporter examples require separate deployment validation; do not run credentialed live-service checks on untrusted PRs. These documentation checks and the recommended dependency-review, dependency-audit, and workflow-lint checks are not yet automated CI jobs.

## Pull Requests and Enforcement

The maintainer plans to enable required pull requests after 1.0 is deployed. This release preparation does not enable branch protection or change repository settings. Until then, complete the checks above and the full CI/distribution workflow before a release; workflow success is not the same as enforced merge protection.

After deployment, require PRs and passing CI/CodeQL checks on the default branch. For a single-maintainer repository, do not require approval from the PR author: GitHub does not allow self-approval. Only require additional reviewer or code-owner approval when an eligible second reviewer is available. Configure branch rules and release-environment permissions explicitly rather than assuming CODEOWNERS or workflow YAML provides them.

## Code Ownership

[CODEOWNERS](.github/CODEOWNERS) assigns repository-wide ownership to `@chadada_microsoft`. GitHub requires a code owner to have write access; the collaborator API did not permit verification of that account's access. CODEOWNERS does not grant access or allow pull-request authors to approve their own pull requests. Required-review rules and any authorized bypass must be configured separately by repository administrators; this change does not modify them.

## Distribution Checks

```shell
python build_and_test.py --dist-dir dist-release
```

The helper builds wheel and source archives, checks metadata with strict Twine, installs each archive in its own fresh virtual environment, and executes outside the checkout with `PYTHONPATH` removed and isolated imports. It checks the package/version metadata, `py.typed`, memory/file/SQLite CRUD, async CRUD, and legacy initialization.

Choose a fresh output directory for each candidate: the helper deliberately rejects directories with multiple wheels or source archives rather than deleting existing artifacts. To verify CI-downloaded distributions without rebuilding:

```shell
python build_and_test.py --skip-build --dist-dir dist
```

CI builds once after tests and quality pass, then checks the exact wheel and sdist on Linux, Windows, and macOS using Python 3.11 and 3.13. Publication uses those same uploaded artifacts.

## Release Process

1. Complete [release blockers](PROJECT_STATUS.md) and review [migration notes](LEGACY_API.md).
2. With maintainer approval, set a unique candidate version such as `1.0.0rc1` in both `pyproject.toml` and `src/nexamem/__init__.py`. Re-run required checks and clean-install validation. Never reuse an already-uploaded version for changed content.
3. Manually run the publish workflow on the candidate branch. It validates a prerelease version, calls reusable CI, and uses the `testpypi` environment and OIDC. `skip-existing` is enabled only for TestPyPI retries; it does not replace changed content or prove equivalence with a previous upload.
4. Verify the approved candidate from TestPyPI using a deliberate trusted dependency-source strategy. Do not combine untrusted indexes or disable TLS verification.
5. Prepare both version declarations for the proposed stable version, update the package classifier and release documentation, and rerun required checks and clean-install validation. Keep the release marked unpublished until registry verification succeeds. Preparation is not authorization to publish.
6. With explicit stable-release approval, confirm the production trusted publisher uses owner `microsoft`, repository `nexamem`, workflow `python-publish-to-test.yml`, and environment `pypi`. Confirm environment access and tag permissions separately from the deferred PR requirement. Have a maintainer create and push the exact `v<version>` tag at the approved stable commit. This triggers production publication, not just a GitHub label. The environment-scoped `pypi` job accepts matching stable tags only, uses OIDC, and treats upload failures as blocking. Production never uses `skip-existing`.
7. Verify the uploaded production wheel and source archive match the successful publishing run's artifacts, then perform clean installed-package checks with a deliberate trusted dependency-source strategy. Record the evidence, date the stable changelog entry, update installation/release-status wording, and create GitHub release notes only after successful publication. Enable the planned PR requirements after deployment.

Repository maintainers must configure trusted publishers, appropriate environment access, and branch/tag permissions explicitly. Required PRs and CI checks are planned for after 1.0 deployment; reviewer requirements must fit the available maintainers. YAML alone cannot establish those repository settings. Fork/PR CI has no publishing token permissions. Ordinary branch pushes never publish.

Preparing code is not authorization to create a tag, commit, push, or publish a release.