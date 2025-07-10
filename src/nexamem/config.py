"""
Configuration management for NexaMem library.
"""
from typing import Any, Dict, Optional
from enum import Enum

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
            - 'history_storage' (str or StorageType): 'memory', 'file', 'sqlite', or 'redis'.
            - 'file_path' (str, optional): Required if 'history_storage' is 'file'.
            - 'sqlite_path' (str, optional): Required if 'history_storage' is 'sqlite'.
            - 'redis_host' (str, optional): Redis host. Required for 'redis' storage.
            - 'redis_port' (int, optional): Redis port. Defaults to 6380 for Azure Redis.
            - 'redis_password' (str, optional): Redis password/access key. For access key auth.
            - 'redis_ssl' (bool, optional): Use SSL for Redis. Defaults to True for Azure.
            - 'redis_db' (int, optional): Redis database number. Defaults to 0.
            - 'redis_key_prefix' (str, optional): Prefix for Redis keys. Defaults to 'nexamem:'.
            - 'redis_auth_method' (str or RedisAuthMethod, optional): 'access_key' or 'entra_id'. Defaults to 'access_key'.
            - 'redis_entra_scope' (str, optional): Entra ID scope. Defaults to Azure Redis scope.
            - 'debug' (bool, optional): Enable debug mode.
    Raises:
        ConfigError: If required parameters are missing or invalid.
    """
    global _config
    
    # Convert enum values to strings for internal processing
    normalized_config = dict(config)
    
    # Handle StorageType enum
    storage = normalized_config.get('history_storage')
    if hasattr(storage, 'value'):  # It's an enum
        storage = storage.value
        normalized_config['history_storage'] = storage
    
    # Handle RedisAuthMethod enum
    auth_method = normalized_config.get('redis_auth_method')
    if hasattr(auth_method, 'value'):  # It's an enum
        auth_method = auth_method.value
        normalized_config['redis_auth_method'] = auth_method
    
    if storage not in ('memory', 'file', 'sqlite', 'redis'):
        raise ConfigError("'history_storage' must be 'memory', 'file', 'sqlite', or 'redis'.")
    if storage == 'file' and not normalized_config.get('file_path'):
        raise ConfigError("'file_path' is required when 'history_storage' is 'file'.")
    if storage == 'sqlite' and not normalized_config.get('sqlite_path'):
        raise ConfigError("'sqlite_path' is required when 'history_storage' is 'sqlite'.")
    if storage == 'redis':
        if not normalized_config.get('redis_host'):
            raise ConfigError("'redis_host' is required when 'history_storage' is 'redis'.")
        
        # Validate authentication method
        auth_method = normalized_config.get('redis_auth_method', 'access_key')
        if auth_method not in ('access_key', 'entra_id'):
            raise ConfigError("'redis_auth_method' must be 'access_key' or 'entra_id'.")
        
        if auth_method == 'access_key' and not normalized_config.get('redis_password'):
            raise ConfigError("'redis_password' is required when using 'access_key' authentication.")
            
        # Set Azure Redis Cache defaults
        normalized_config.setdefault('redis_port', 6380)
        normalized_config.setdefault('redis_ssl', True)
        normalized_config.setdefault('redis_db', 0)
        normalized_config.setdefault('redis_key_prefix', 'nexamem:')
        normalized_config.setdefault('redis_auth_method', 'access_key')
        normalized_config.setdefault('redis_entra_scope', 'https://redis.azure.com/.default')
    normalized_config.setdefault('debug', False)
    _config = normalized_config.copy()

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
