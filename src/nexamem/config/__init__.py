"""
Configuration models for NexaMem storage backends.
Uses Pydantic for validation and type safety.
"""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from .aimemory import AIMemoryConfig
from .storage import AzureRedisConfig, FileConfig, MemoryConfig, SQLiteConfig, StorageConfig

legacy_config_path = Path(__file__).parent.parent / "config.py"
spec = spec_from_file_location("nexamem._legacy_config", legacy_config_path)
if spec is None or spec.loader is None:
    raise ImportError("Cannot load the legacy NexaMem configuration module")
legacy_config = module_from_spec(spec)
spec.loader.exec_module(legacy_config)

ConfigError = legacy_config.ConfigError
initialize = legacy_config.initialize
get_config = legacy_config.get_config

__all__ = [
    # Legacy config (backward compatibility)
    "ConfigError",
    "initialize",
    "get_config",
    # New Pydantic config models
    "StorageConfig",
    "AzureRedisConfig",
    "SQLiteConfig",
    "FileConfig",
    "MemoryConfig",
    "AIMemoryConfig",
]
