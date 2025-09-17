"""
Storage adapters for different storage backends.
"""

from .i_storage_adapter import IStorageAdapter
from .redis_adapter import RedisAdapter, RedisAdapterError, RedisConnectionError
from .configs.redis_adapter_config import RedisAdapterConfig

# Import other adapters if they exist
try:
    from .in_memory_adapter import InMemoryAdapter
    from .configs.in_memory_adapter_config import InMemoryAdapterConfig
except ImportError:
    InMemoryAdapter = None
    InMemoryAdapterConfig = None

__all__ = [
    "IStorageAdapter",
    "RedisAdapter", 
    "RedisAdapterError",
    "RedisConnectionError",
    "RedisAdapterConfig",
]

# Add to __all__ if available
if InMemoryAdapter is not None:
    __all__.extend(["InMemoryAdapter", "InMemoryAdapterConfig"])