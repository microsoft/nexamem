"""
Storage configuration models using Pydantic for validation.
"""

import os
from enum import Enum
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator


class StorageType(str, Enum):
    """Supported storage backend types."""
    AZURE_REDIS = "azure_redis"
    MEMORY = "memory"
    FILE = "file"
    SQLITE = "sqlite"


class AzureAuthMethod(str, Enum):
    """Azure Redis authentication methods."""
    ACCESS_KEY = "access_key"
    ENTRA_ID = "entra_id"
    KEYVAULT = "keyvault"


class AzureRedisConfig(BaseModel):
    """Configuration for Azure Cache for Redis."""
    
    # Connection details
    hostname: str = Field(..., description="Azure Redis hostname (e.g., 'cache.redis.cache.windows.net')")
    port: int = Field(default=6380, description="Azure Redis SSL port")
    ssl: bool = Field(default=True, description="Use SSL (required for Azure)")
    db: int = Field(default=0, ge=0, le=15, description="Redis database number")
    
    # Authentication
    auth_method: AzureAuthMethod = Field(default=AzureAuthMethod.ACCESS_KEY)
    access_key: Optional[str] = Field(None, description="Primary/Secondary access key")
    
    # Entra ID authentication
    use_entra_id: bool = Field(default=False)
    username: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    tenant_id: Optional[str] = None
    
    # Azure Key Vault
    keyvault_url: Optional[str] = None
    secret_name: Optional[str] = None
    
    # Connection tuning
    max_connections: int = Field(default=50, description="Connection pool size")
    retry_on_timeout: bool = Field(default=True)
    socket_connect_timeout: float = Field(default=5.0)
    socket_timeout: float = Field(default=5.0)
    
    # Data structure preferences
    use_collections: bool = Field(default=True, description="Use Redis collections instead of individual keys")
    collection_prefix: str = Field(default="nexamem", description="Prefix for collection names")
    
    @field_validator('hostname')
    @classmethod
    def validate_azure_hostname(cls, v):
        """Validate that hostname is an Azure Redis hostname."""
        if not v.endswith('.redis.cache.windows.net'):
            raise ValueError('Azure Redis hostname must end with .redis.cache.windows.net')
        return v
    
    @field_validator('auth_method')
    @classmethod
    def validate_auth_config(cls, v, info):
        """Validate that required auth fields are provided."""
        values = info.data if info else {}
        if v == AzureAuthMethod.ACCESS_KEY and not values.get('access_key'):
            raise ValueError('access_key required when using access_key auth')
        elif v == AzureAuthMethod.ENTRA_ID and not values.get('use_entra_id'):
            raise ValueError('use_entra_id must be True when using entra_id auth')
        elif v == AzureAuthMethod.KEYVAULT:
            if not (values.get('keyvault_url') and values.get('secret_name')):
                raise ValueError('keyvault_url and secret_name required when using keyvault auth')
        return v
    
    @classmethod
    def from_env(cls) -> "AzureRedisConfig":
        """Create configuration from environment variables."""
        hostname = os.getenv('AZURE_REDIS_HOSTNAME')
        if not hostname:
            raise ValueError("AZURE_REDIS_HOSTNAME environment variable required")
        
        # Determine auth method from available env vars
        if os.getenv('AZURE_REDIS_ACCESS_KEY'):
            auth_method = AzureAuthMethod.ACCESS_KEY
            access_key = os.getenv('AZURE_REDIS_ACCESS_KEY')
            use_entra_id = False
        elif os.getenv('AZURE_CLIENT_ID'):
            auth_method = AzureAuthMethod.ENTRA_ID
            access_key = None
            use_entra_id = True
        elif os.getenv('AZURE_KEYVAULT_URL'):
            auth_method = AzureAuthMethod.KEYVAULT
            access_key = None
            use_entra_id = False
        else:
            raise ValueError("No Azure authentication method found in environment")
        
        return cls(
            hostname=hostname,
            port=int(os.getenv('AZURE_REDIS_PORT', '6380')),
            auth_method=auth_method,
            access_key=access_key,
            use_entra_id=use_entra_id,
            client_id=os.getenv('AZURE_CLIENT_ID'),
            client_secret=os.getenv('AZURE_CLIENT_SECRET'),
            tenant_id=os.getenv('AZURE_TENANT_ID'),
            keyvault_url=os.getenv('AZURE_KEYVAULT_URL'),
            secret_name=os.getenv('AZURE_REDIS_SECRET_NAME'),
            use_collections=os.getenv('AZURE_REDIS_USE_COLLECTIONS', 'true').lower() == 'true'
        )


class MemoryConfig(BaseModel):
    """Configuration for in-memory storage."""
    max_size: Optional[int] = Field(None, description="Maximum number of messages to store")
    cleanup_interval: int = Field(default=300, description="TTL cleanup interval in seconds")


class FileConfig(BaseModel):
    """Configuration for file-based storage."""
    path: str = Field(..., description="File path for storage")
    encoding: str = Field(default="utf-8", description="File encoding")
    backup_count: int = Field(default=0, description="Number of backup files to keep")
    auto_create_dirs: bool = Field(default=True, description="Auto-create parent directories")


class SQLiteConfig(BaseModel):
    """Configuration for SQLite storage."""
    path: str = Field(..., description="SQLite database file path")
    timeout: float = Field(default=30.0, description="Connection timeout in seconds")
    check_same_thread: bool = Field(default=False, description="SQLite same thread check")
    auto_migrate: bool = Field(default=True, description="Automatically migrate schema")
    auto_create_dirs: bool = Field(default=True, description="Auto-create parent directories")


class StorageConfig(BaseModel):
    """Unified storage configuration."""
    type: StorageType
    config: Union[AzureRedisConfig, MemoryConfig, FileConfig, SQLiteConfig]
    
    @classmethod
    def azure_redis(cls, config: AzureRedisConfig) -> "StorageConfig":
        """Create Azure Redis storage config."""
        return cls(type=StorageType.AZURE_REDIS, config=config)
    
    @classmethod
    def memory(cls, config: Optional[MemoryConfig] = None) -> "StorageConfig":
        """Create in-memory storage config."""
        return cls(type=StorageType.MEMORY, config=config or MemoryConfig())
    
    @classmethod
    def file(cls, path: str, **kwargs) -> "StorageConfig":
        """Create file storage config."""
        return cls(type=StorageType.FILE, config=FileConfig(path=path, **kwargs))
    
    @classmethod
    def sqlite(cls, path: str, **kwargs) -> "StorageConfig":
        """Create SQLite storage config."""
        return cls(type=StorageType.SQLITE, config=SQLiteConfig(path=path, **kwargs))
    
    @classmethod
    def from_env(cls) -> "StorageConfig":
        """Create storage config from environment variables."""
        storage_type = os.getenv('NEXAMEM_STORAGE_TYPE', 'memory').lower()
        
        if storage_type == 'azure_redis':
            return cls.azure_redis(AzureRedisConfig.from_env())
        elif storage_type == 'file':
            path = os.getenv('NEXAMEM_FILE_PATH')
            if not path:
                raise ValueError("NEXAMEM_FILE_PATH required for file storage")
            return cls.file(path)
        elif storage_type == 'sqlite':
            path = os.getenv('NEXAMEM_SQLITE_PATH')
            if not path:
                raise ValueError("NEXAMEM_SQLITE_PATH required for SQLite storage")
            return cls.sqlite(path)
        else:  # memory
            return cls.memory()
