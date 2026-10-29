# Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file

- This is a Python package project for managing NexaMem chatbot history.
- Follow best practices for open-source Python packages (PEP 517/518, pyproject.toml, tests, docs, etc).
- All code should be compatible with Python 3.11+; CI targets Python 3.11, 3.12, and 3.13.
- Use pip, venv, and pip-tools for dependency management; do not require uv.
- Use clear, concise docstrings and type hints.
- Write tests in the `tests/` directory using pytest.
- Run Pytest before committing changes to ensure all tests pass.
- Require at least 90% overall unit-test line coverage across the complete package, including legacy modules. Keep Ruff and strict mypy checks blocking.
- Create a `whl` file for distribution when ready.
