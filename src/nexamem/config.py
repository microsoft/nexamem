"""
Configuration management for NexaMem library.

⚠️  DEPRECATED: This module is deprecated and will be removed in a future version.
Please migrate to the new AIMemoryConfig API. See LEGACY_API.md for migration guidance.
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
    
    ⚠️  DEPRECATED: This function is deprecated and will be removed in a future version.
    Please migrate to the new AIMemoryConfig API. See LEGACY_API.md for migration guidance.

    Args:
        config (Dict[str, Any]): Configuration dictionary. Must include:
            - 'history_storage' (str): 'memory', 'file', 'sqlite', or 'redis'.
            - 'file_path' (str, optional): Required if 'history_storage' is 'file'.
            - 'sqlite_path' (str, optional): Required if 'history_storage' is 'sqlite'.
            - 'redis_config' (dict, optional): Required if 'history_storage' is 'redis'.
            - 'debug' (bool, optional): Enable debug mode.
    Raises:
        ConfigError: If required parameters are missing or invalid.
    """
    global _config
    storage = config.get('history_storage')
    if storage not in ('memory', 'file', 'sqlite', 'redis'):
        raise ConfigError("'history_storage' must be 'memory', 'file', 'sqlite', or 'redis'.")
    if storage == 'file' and not config.get('file_path'):
        raise ConfigError("'file_path' is required when 'history_storage' is 'file'.")
    if storage == 'sqlite' and not config.get('sqlite_path'):
        raise ConfigError("'sqlite_path' is required when 'history_storage' is 'sqlite'.")
    if storage == 'redis' and not config.get('redis_config'):
        raise ConfigError("'redis_config' is required when 'history_storage' is 'redis'.")
    
    # Validate Redis configuration if provided
    if storage == 'redis':
        redis_config = config.get('redis_config', {})
        if not isinstance(redis_config, dict):
            raise ConfigError("'redis_config' must be a dictionary.")
        
        # Check for Azure-specific configurations
        azure_hostname = redis_config.get('azure_hostname')
        if azure_hostname:
            # Azure Redis - validate Azure-specific parameters
            use_entra_id = redis_config.get('use_azure_entra_id', False)
            access_key = redis_config.get('azure_access_key')
            keyvault_config = redis_config.get('azure_keyvault_url') and redis_config.get('azure_secret_name')
            
            if not (access_key or use_entra_id or keyvault_config):
                raise ConfigError(
                    "For Azure Redis, must provide either 'azure_access_key', "
                    "Entra ID config ('use_azure_entra_id'), or Key Vault config "
                    "('azure_keyvault_url' and 'azure_secret_name')."
                )
        else:
            # Standard Redis - require host at minimum
            if not redis_config.get('host', redis_config.get('hostname')):
                raise ConfigError("Redis 'host' or 'hostname' is required for non-Azure Redis.")
    
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
    
    ⚠️  DEPRECATED: This function is deprecated and will be removed in a future version.
    Please migrate to the new AIMemoryConfig API. See LEGACY_API.md for migration guidance.

    Returns:
        Optional[Dict[str, Any]]: The configuration dictionary if initialized, else None.
    """
    return _config
