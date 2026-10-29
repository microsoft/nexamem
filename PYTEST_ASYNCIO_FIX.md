# pytest-asyncio Configuration

The historical duplicate workflow/plugin-loading workaround has been superseded by a single pytest configuration in `pyproject.toml` and the reusable [CI workflow](.github/workflows/ci.yml).

Install `.[dev]`, use `python -m pytest`, and let pytest discover `pytest-asyncio` normally. Do not restore a second `pytest.ini` or force-load the plugin twice. See [current async testing](ASYNC_TESTING.md) for commands and troubleshooting.