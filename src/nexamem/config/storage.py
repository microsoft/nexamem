"""
Storage configuration models using Pydantic for validation.
"""

import os
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


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
    hostname: str = Field(
        ..., description="Azure Redis hostname (e.g., 'cache.redis.cache.windows.net')"
    )
    port: int = Field(default=6380, description="Azure Redis SSL port")
    ssl: bool = Field(default=True, description="Use SSL (required for Azure)")
    db: int = Field(default=0, ge=0, le=15, description="Redis database number")

    # Authentication
    auth_method: AzureAuthMethod = Field(default=AzureAuthMethod.ACCESS_KEY)
    access_key: str | None = Field(None, description="Primary/Secondary access key")

    # Entra ID authentication
    use_entra_id: bool = Field(default=False)
    username: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    tenant_id: str | None = None

    # Azure Key Vault
    keyvault_url: str | None = None
    secret_name: str | None = None

    # Connection tuning
    max_connections: int = Field(default=50, description="Connection pool size")
    retry_on_timeout: bool = Field(default=True)
    socket_connect_timeout: float = Field(default=5.0)
    socket_timeout: float = Field(default=5.0)

    # Data structure preferences
    use_collections: bool = Field(
        default=True, description="Use Redis collections instead of individual keys"
    )
    collection_prefix: str = Field(default="nexamem", description="Prefix for collection names")

    @field_validator("hostname")
    @classmethod
    def validate_azure_hostname(cls, v: str) -> str:
        """Validate that hostname is an Azure Redis hostname."""
        if not v.endswith((".redis.cache.windows.net", ".redis.azure.net")) or any(
            separator in v for separator in ("/", ":", " ")
        ):
            raise ValueError("Expected an Azure Cache for Redis or Azure Managed Redis hostname")
        return v

    @model_validator(mode="before")
    @classmethod
    def managed_redis_defaults(cls, data: Any) -> Any:
        """Select the Managed Redis TLS port unless explicitly configured."""
        if isinstance(data, dict) and "port" not in data:
            hostname = data.get("hostname", "")
            if isinstance(hostname, str) and hostname.endswith(".redis.azure.net"):
                return {**data, "port": 10000}
        return data

    @model_validator(mode="after")
    def validate_auth_config(self) -> "AzureRedisConfig":
        """Validate that required auth fields are provided."""
        if not self.ssl:
            raise ValueError("TLS is required for Azure Redis")
        if self.hostname.endswith(".redis.azure.net") and self.db != 0:
            raise ValueError("Azure Managed Redis supports database 0 only")
        if self.auth_method == AzureAuthMethod.ACCESS_KEY and not self.access_key:
            raise ValueError("access_key required when using access_key auth")
        elif self.auth_method == AzureAuthMethod.ENTRA_ID and not self.use_entra_id:
            raise ValueError("use_entra_id must be True when using entra_id auth")
        elif self.auth_method == AzureAuthMethod.KEYVAULT and not (
            self.keyvault_url and self.secret_name
        ):
            raise ValueError("keyvault_url and secret_name required when using keyvault auth")
        return self

    @classmethod
    def from_env(cls) -> "AzureRedisConfig":
        """Create configuration from environment variables."""
        hostname = os.getenv("AZURE_REDIS_HOSTNAME")
        if not hostname:
            raise ValueError("AZURE_REDIS_HOSTNAME environment variable required")

        # Determine auth method from available env vars
        explicit_method = os.getenv("AZURE_REDIS_AUTH_METHOD")
        if explicit_method:
            auth_method = AzureAuthMethod(explicit_method)
            access_key = os.getenv("AZURE_REDIS_ACCESS_KEY")
            use_entra_id = auth_method == AzureAuthMethod.ENTRA_ID
        elif os.getenv("AZURE_REDIS_ACCESS_KEY"):
            auth_method = AzureAuthMethod.ACCESS_KEY
            access_key = os.getenv("AZURE_REDIS_ACCESS_KEY")
            use_entra_id = False
        elif os.getenv("AZURE_CLIENT_ID"):
            auth_method = AzureAuthMethod.ENTRA_ID
            access_key = None
            use_entra_id = True
        elif os.getenv("AZURE_KEYVAULT_URL"):
            auth_method = AzureAuthMethod.KEYVAULT
            access_key = None
            use_entra_id = False
        else:
            raise ValueError("No Azure authentication method found in environment")

        return cls(
            hostname=hostname,
            port=int(
                os.getenv("AZURE_REDIS_PORT")
                or ("10000" if hostname.endswith(".redis.azure.net") else "6380")
            ),
            auth_method=auth_method,
            access_key=access_key,
            use_entra_id=use_entra_id,
            username=os.getenv("AZURE_REDIS_USERNAME"),
            client_id=os.getenv("AZURE_CLIENT_ID"),
            client_secret=os.getenv("AZURE_CLIENT_SECRET"),
            tenant_id=os.getenv("AZURE_TENANT_ID"),
            keyvault_url=os.getenv("AZURE_KEYVAULT_URL"),
            secret_name=os.getenv("AZURE_REDIS_SECRET_NAME"),
            use_collections=os.getenv("AZURE_REDIS_USE_COLLECTIONS", "true").lower() == "true",
        )


class MemoryConfig(BaseModel):
    """Configuration for in-memory storage."""

    max_size: int | None = Field(default=None, description="Maximum number of messages to store")
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
    config: AzureRedisConfig | MemoryConfig | FileConfig | SQLiteConfig

    @classmethod
    def azure_redis(cls, config: AzureRedisConfig) -> "StorageConfig":
        """Create Azure Redis storage config."""
        return cls(type=StorageType.AZURE_REDIS, config=config)

    @classmethod
    def memory(cls, config: MemoryConfig | None = None) -> "StorageConfig":
        """Create in-memory storage config."""
        return cls(type=StorageType.MEMORY, config=config or MemoryConfig())

    @classmethod
    def file(cls, path: str, **kwargs: Any) -> "StorageConfig":
        """Create file storage config."""
        return cls(type=StorageType.FILE, config=FileConfig(path=path, **kwargs))

    @classmethod
    def sqlite(cls, path: str, **kwargs: Any) -> "StorageConfig":
        """Create SQLite storage config."""
        return cls(type=StorageType.SQLITE, config=SQLiteConfig(path=path, **kwargs))

    @classmethod
    def from_env(cls) -> "StorageConfig":
        """Create storage config from environment variables."""
        storage_type = os.getenv("NEXAMEM_STORAGE_TYPE", "memory").lower()

        if storage_type == "azure_redis":
            return cls.azure_redis(AzureRedisConfig.from_env())
        elif storage_type == "file":
            path = os.getenv("NEXAMEM_FILE_PATH")
            if not path:
                raise ValueError("NEXAMEM_FILE_PATH required for file storage")
            return cls.file(path)
        elif storage_type == "sqlite":
            path = os.getenv("NEXAMEM_SQLITE_PATH")
            if not path:
                raise ValueError("NEXAMEM_SQLITE_PATH required for SQLite storage")
            return cls.sqlite(path)
        else:  # memory
            return cls.memory()
