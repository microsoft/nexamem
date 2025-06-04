"""
Configuration management for NexaMem library.
"""
from typing import Any, Dict, Optional

class ConfigError(Exception):
    """Custom exception for configuration errors."""
    pass

_config: Optional[Dict[str, Any]] = None

def initialize(config: Dict[str, Any]) -> None:
    """
    Initialize the NexaMem library with the given configuration.
    This function must be called before using any other functionality.

    Args:
        config (Dict[str, Any]): Configuration dictionary. Must include:
            - 'history_storage' (str): 'memory', 'file', or 'sqlite'.
            - 'file_path' (str, optional): Required if 'history_storage' is 'file'.
            - 'sqlite_path' (str, optional): Required if 'history_storage' is 'sqlite'.
            - 'debug' (bool, optional): Enable debug mode.
    Raises:
        ConfigError: If required parameters are missing or invalid.
    """
    global _config
    storage = config.get('history_storage')
    if storage not in ('memory', 'file', 'sqlite'):
        raise ConfigError("'history_storage' must be 'memory', 'file', or 'sqlite'.")
    if storage == 'file' and not config.get('file_path'):
        raise ConfigError("'file_path' is required when 'history_storage' is 'file'.")
    if storage == 'sqlite' and not config.get('sqlite_path'):
        raise ConfigError("'sqlite_path' is required when 'history_storage' is 'sqlite'.")
    config.setdefault('debug', False)
    _config = config.copy()

    # Print banner on first successful initialization
    if not getattr(initialize, '_banner_printed', False):
        banner = (
            "\033[1;36m========================================\033[0m\n"
            "\033[1;32m  NexaMem: AI Memory Manager\033[0m\n"
            "\033[1;33m  Successfully initialized!\033[0m\n"
            "\033[1;34m  https://github.com/microsoft/nexamem\033[0m\n"
            "\033[1;36m========================================\033[0m"
        )
        print(banner)
        initialize._banner_printed = True

def get_config() -> Optional[Dict[str, Any]]:
    """
    Get the current configuration.

    Returns:
        Optional[Dict[str, Any]]: The configuration dictionary if initialized, else None.
    """
    return _config
