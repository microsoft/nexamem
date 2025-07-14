"""
Configuration models for NexaMem storage backends.
Uses Pydantic for validation and type safety.
"""

from .aimemory import AIMemoryConfig
from .storage import AzureRedisConfig, FileConfig, MemoryConfig, SQLiteConfig, StorageConfig

# Legacy config imports to maintain backward compatibility
try:
    import sys
    if 'nexamem.config' not in sys.modules:
        # Import the legacy config module directly to avoid circular import
        import importlib.util
        import os
        
        legacy_config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.py')
        spec = importlib.util.spec_from_file_location("nexamem_legacy_config", legacy_config_path)
        legacy_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(legacy_config)
        
        ConfigError = legacy_config.ConfigError
        initialize = legacy_config.initialize
        get_config = legacy_config.get_config
    else:
        # Fallback if there are issues
        class ConfigError(Exception):
            pass
        def initialize(config): pass
        def get_config(): return None
except Exception:
    # Fallback definitions
    class ConfigError(Exception):
        pass
    def initialize(config): pass
    def get_config(): return None

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
