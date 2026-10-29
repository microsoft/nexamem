# Async Testing

Install the project's declared development dependencies in a supported Python environment:

```shell
python -m pip install -e ".[dev]"
```

Pytest configuration lives only in `pyproject.toml`. `asyncio_mode = "auto"` collects async tests automatically; the default fixture loop scope is `function`. There is no `pytest.ini` override and no need to force-load the plugin with `-p pytest_asyncio`.

## Focused Checks

```shell
python -m pytest tests/test_async_verification.py tests/test_ci_async_verification.py -q
python -m pytest tests/test_storage_contract.py tests/test_redis_storage.py -q
```

Focused runs do not automatically start package-wide coverage. The complete release gate explicitly measures all `src/nexamem` lines, including both API generations:

```shell
python -m pytest tests/ -m "not integration" --cov=nexamem --cov-report=term-missing --cov-fail-under=90
```

Redis tests use fakeredis; identity factories are mocked. Unit coverage does not require credentials, cloud resources, or a live Redis service. Mark any separately added live-service tests `integration`; they do not contribute to the release unit-coverage gate.

## Troubleshooting

Use `python -m pytest --version` and `python -m pip show pytest-asyncio` to verify that pip and pytest refer to the same interpreter. Check for an inherited `PYTEST_DISABLE_PLUGIN_AUTOLOAD` setting before changing test configuration. Create a fresh virtual environment if the old one points to an uninstalled interpreter.

Await all async operations and use `aclose()` where the adapter exposes it. Local async storage wraps synchronous file/SQLite work; tests passing does not prove event-loop responsiveness under load.

CI runs the same suite once per Python/OS combination; it does not rerun overlapping async subsets as an additional coverage gate.