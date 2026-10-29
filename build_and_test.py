"""Build and smoke-test wheel and source installations outside the checkout."""

import argparse
import os
import subprocess
import sys
import tomllib
import venv
from pathlib import Path
from tempfile import TemporaryDirectory

SMOKE_TEST = """
import asyncio
import importlib.metadata
import sys
from importlib.util import find_spec
from pathlib import Path
from unittest.mock import patch
import nexamem
from nexamem import AIMemory, AsyncAIMemory, AIMemoryConfig, StorageConfig

assert nexamem.__version__ == importlib.metadata.version('nexamem') == sys.argv[1]
assert Path(nexamem.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
assert Path(nexamem.__file__).with_name('py.typed').is_file()
assert all(find_spec(name) is None for name in ('langchain_core', 'autogen_core', 'semantic_kernel', 'agent_framework'))
assert all(find_spec('nexamem.integrations.' + name) is not None for name in ('langchain', 'autogen', 'semantic_kernel', 'agent_framework'))

for storage in (StorageConfig.memory(), StorageConfig.file('files'), StorageConfig.sqlite('data.db')):
    with AIMemory(AIMemoryConfig(default_scope='smoke', storage=storage)) as memory:
        memory_id = memory.store('installed distribution', metadata={'tested': True})
        assert memory.retrieve(memory_id)['content'] == 'installed distribution'
        assert memory.search('installed') == [memory_id]
        assert memory.delete(memory_id)
        with patch('nexamem.retention.time.time', return_value=100) as clock:
            expiring = memory.store('expires', ttl_sec=1)
            assert memory.retrieve(expiring) is not None
            clock.return_value = 101
            assert memory.retrieve(expiring) is None
            assert memory.purge_expired() == 0

async def check_async():
    async with AsyncAIMemory(AIMemoryConfig(default_scope='async', storage=StorageConfig.memory())) as memory:
        memory_id = await memory.store('async installed distribution')
        assert (await memory.retrieve(memory_id))['content'] == 'async installed distribution'
        assert await memory.delete(memory_id)

asyncio.run(check_async())
nexamem.initialize({'history_storage': 'memory'})
history = nexamem.ChatHistory()
history.add_user_message('legacy installation')
assert history.get_history()[0]['content'] == 'legacy installation'
print('Installed distribution verified:', nexamem.__version__)
"""


def verify_distributions(distribution_dir: Path, expected_version: str) -> None:
    """Install and exercise both artifact types in independent virtual environments."""
    wheels = list(distribution_dir.glob("*.whl"))
    sources = list(distribution_dir.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sources) != 1:
        raise ValueError(
            "Expected exactly one wheel and one source archive in the distribution directory"
        )
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    for artifact in wheels + sources:
        with TemporaryDirectory(prefix="nexamem-install-") as temporary_dir:
            directory = Path(temporary_dir)
            environment_dir = directory / "venv"
            venv.EnvBuilder(with_pip=True).create(environment_dir)
            executable = environment_dir / (
                "Scripts/python.exe" if os.name == "nt" else "bin/python"
            )
            subprocess.run(
                [str(executable), "-m", "pip", "install", "--quiet", str(artifact.resolve())],
                cwd=directory,
                env=environment,
                check=True,
            )
            subprocess.run(
                [str(executable), "-I", "-c", SMOKE_TEST, expected_version],
                cwd=directory,
                env=environment,
                check=True,
            )


def main() -> None:
    """Build distributions unless supplied by CI, then verify both installation paths."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--dist-dir", type=Path, default=Path("dist"))
    arguments = parser.parse_args()
    project_dir = Path(__file__).resolve().parent
    distribution_dir = arguments.dist_dir.resolve()
    metadata = tomllib.loads((project_dir / "pyproject.toml").read_text(encoding="utf-8"))
    if not arguments.skip_build:
        subprocess.run(
            [sys.executable, "-m", "build", "--outdir", str(distribution_dir)],
            cwd=project_dir,
            check=True,
        )
    subprocess.run(
        [sys.executable, "-m", "twine", "check", "--strict", *map(str, distribution_dir.glob("*"))],
        check=True,
    )
    verify_distributions(distribution_dir, metadata["project"]["version"])


if __name__ == "__main__":
    main()
