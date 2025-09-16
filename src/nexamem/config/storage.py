"""
Storage configuration models using Pydantic for validation.
"""

import os
from enum import Enum
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class StorageType(str, Enum):
    """Supported storage backend types."""
    AZURE_REDIS = "azure_redis"
    AZURE_COSMOS = "azure_cosmos"
    AZURE_BLOB = "azure_blob"
    AZURE_AI_SEARCH = "azure_ai_search"
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
    
    @model_validator(mode='after')
    def validate_auth_config(self):
        """Validate that required auth fields are provided."""
        if self.auth_method == AzureAuthMethod.ACCESS_KEY and not self.access_key:
            raise ValueError('access_key required when using access_key auth')
        elif self.auth_method == AzureAuthMethod.ENTRA_ID and not self.use_entra_id:
            raise ValueError('use_entra_id must be True when using entra_id auth')
        elif self.auth_method == AzureAuthMethod.KEYVAULT:
            if not (self.keyvault_url and self.secret_name):
                raise ValueError('keyvault_url and secret_name required when using keyvault auth')
        return self
    
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


class AzureCosmosConfig(BaseModel):
    """Configuration for Azure Cosmos DB."""
    
    # Connection details
    endpoint: str = Field(..., description="Cosmos DB endpoint URL")
    database_name: str = Field(..., description="Database name")
    container_name: str = Field(default="memories", description="Container name for storing memories")
    
    # Authentication
    auth_method: AzureAuthMethod = Field(default=AzureAuthMethod.ACCESS_KEY)
    account_key: Optional[str] = Field(None, description="Account key for authentication")
    
    # Entra ID authentication
    use_entra_id: bool = Field(default=False)
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    tenant_id: Optional[str] = None
    
    # Azure Key Vault
    keyvault_url: Optional[str] = None
    secret_name: Optional[str] = None
    
    # Performance tuning
    consistency_level: str = Field(default="Session", description="Consistency level (Session, Eventual, Strong, etc.)")
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    connection_timeout: int = Field(default=10, description="Connection timeout in seconds")
    retry_total: int = Field(default=3, description="Maximum number of retries")
    
    # Partition and indexing
    partition_key: str = Field(default="/scope", description="Partition key for the container")
    auto_create_container: bool = Field(default=True, description="Auto-create container if it doesn't exist")
    throughput: Optional[int] = Field(default=400, description="Provisioned throughput (RU/s)")
    
    @model_validator(mode='after')
    def validate_cosmos_auth_config(self):
        """Validate that required auth fields are provided."""
        if self.auth_method == AzureAuthMethod.ACCESS_KEY and not self.account_key:
            raise ValueError('account_key required when using access_key auth')
        elif self.auth_method == AzureAuthMethod.ENTRA_ID and not self.use_entra_id:
            raise ValueError('use_entra_id must be True when using entra_id auth')
        elif self.auth_method == AzureAuthMethod.KEYVAULT:
            if not (self.keyvault_url and self.secret_name):
                raise ValueError('keyvault_url and secret_name required when using keyvault auth')
        return self
    
    @classmethod
    def from_env(cls) -> "AzureCosmosConfig":
        """Create configuration from environment variables."""
        endpoint = os.getenv('AZURE_COSMOS_ENDPOINT')
        if not endpoint:
            raise ValueError("AZURE_COSMOS_ENDPOINT environment variable required")
        
        database_name = os.getenv('AZURE_COSMOS_DATABASE')
        if not database_name:
            raise ValueError("AZURE_COSMOS_DATABASE environment variable required")
        
        # Determine auth method from available env vars
        if os.getenv('AZURE_COSMOS_KEY'):
            auth_method = AzureAuthMethod.ACCESS_KEY
            account_key = os.getenv('AZURE_COSMOS_KEY')
            use_entra_id = False
        elif os.getenv('AZURE_CLIENT_ID'):
            auth_method = AzureAuthMethod.ENTRA_ID
            account_key = None
            use_entra_id = True
        elif os.getenv('AZURE_KEYVAULT_URL'):
            auth_method = AzureAuthMethod.KEYVAULT
            account_key = None
            use_entra_id = False
        else:
            raise ValueError("No Azure authentication method found in environment")
        
        return cls(
            endpoint=endpoint,
            database_name=database_name,
            container_name=os.getenv('AZURE_COSMOS_CONTAINER', 'memories'),
            auth_method=auth_method,
            account_key=account_key,
            use_entra_id=use_entra_id,
            client_id=os.getenv('AZURE_CLIENT_ID'),
            client_secret=os.getenv('AZURE_CLIENT_SECRET'),
            tenant_id=os.getenv('AZURE_TENANT_ID'),
            keyvault_url=os.getenv('AZURE_KEYVAULT_URL'),
            secret_name=os.getenv('AZURE_COSMOS_SECRET_NAME'),
            consistency_level=os.getenv('AZURE_COSMOS_CONSISTENCY_LEVEL', 'Session'),
            throughput=int(os.getenv('AZURE_COSMOS_THROUGHPUT', '400'))
        )


class AzureBlobConfig(BaseModel):
    """Configuration for Azure Blob Storage."""
    
    # Connection details
    account_name: str = Field(..., description="Storage account name")
    container_name: str = Field(default="memories", description="Container name for storing memories")
    
    # Authentication
    auth_method: AzureAuthMethod = Field(default=AzureAuthMethod.ACCESS_KEY)
    account_key: Optional[str] = Field(None, description="Account key for authentication")
    connection_string: Optional[str] = Field(None, description="Full connection string")
    
    # Entra ID authentication
    use_entra_id: bool = Field(default=False)
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    tenant_id: Optional[str] = None
    
    # Azure Key Vault
    keyvault_url: Optional[str] = None
    secret_name: Optional[str] = None
    
    # Blob settings
    blob_prefix: str = Field(default="nexamem", description="Prefix for blob names")
    tier: str = Field(default="Hot", description="Blob tier (Hot, Cool, Archive)")
    auto_create_container: bool = Field(default=True, description="Auto-create container if it doesn't exist")
    
    # Performance settings
    max_block_size: int = Field(default=4 * 1024 * 1024, description="Maximum block size for uploads")
    max_single_put_size: int = Field(default=64 * 1024 * 1024, description="Maximum size for single put")
    
    @model_validator(mode='after')
    def validate_blob_auth_config(self):
        """Validate that required auth fields are provided."""
        if self.auth_method == AzureAuthMethod.ACCESS_KEY and not (self.account_key or self.connection_string):
            raise ValueError('account_key or connection_string required when using access_key auth')
        elif self.auth_method == AzureAuthMethod.ENTRA_ID and not self.use_entra_id:
            raise ValueError('use_entra_id must be True when using entra_id auth')
        elif self.auth_method == AzureAuthMethod.KEYVAULT:
            if not (self.keyvault_url and self.secret_name):
                raise ValueError('keyvault_url and secret_name required when using keyvault auth')
        return self
    
    @classmethod
    def from_env(cls) -> "AzureBlobConfig":
        """Create configuration from environment variables."""
        account_name = os.getenv('AZURE_STORAGE_ACCOUNT')
        if not account_name:
            raise ValueError("AZURE_STORAGE_ACCOUNT environment variable required")
        
        # Check for connection string first
        connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        if connection_string:
            return cls(
                account_name=account_name,
                connection_string=connection_string,
                auth_method=AzureAuthMethod.ACCESS_KEY,
                container_name=os.getenv('AZURE_BLOB_CONTAINER', 'memories'),
                blob_prefix=os.getenv('AZURE_BLOB_PREFIX', 'nexamem')
            )
        
        # Determine auth method from available env vars
        if os.getenv('AZURE_STORAGE_KEY'):
            auth_method = AzureAuthMethod.ACCESS_KEY
            account_key = os.getenv('AZURE_STORAGE_KEY')
            use_entra_id = False
        elif os.getenv('AZURE_CLIENT_ID'):
            auth_method = AzureAuthMethod.ENTRA_ID
            account_key = None
            use_entra_id = True
        elif os.getenv('AZURE_KEYVAULT_URL'):
            auth_method = AzureAuthMethod.KEYVAULT
            account_key = None
            use_entra_id = False
        else:
            raise ValueError("No Azure authentication method found in environment")
        
        return cls(
            account_name=account_name,
            container_name=os.getenv('AZURE_BLOB_CONTAINER', 'memories'),
            auth_method=auth_method,
            account_key=account_key,
            use_entra_id=use_entra_id,
            client_id=os.getenv('AZURE_CLIENT_ID'),
            client_secret=os.getenv('AZURE_CLIENT_SECRET'),
            tenant_id=os.getenv('AZURE_TENANT_ID'),
            keyvault_url=os.getenv('AZURE_KEYVAULT_URL'),
            secret_name=os.getenv('AZURE_BLOB_SECRET_NAME'),
            blob_prefix=os.getenv('AZURE_BLOB_PREFIX', 'nexamem')
        )


class AzureAISearchConfig(BaseModel):
    """Configuration for Azure AI Search vector database."""
    
    # Connection details
    endpoint: str = Field(..., description="Azure AI Search endpoint URL")
    index_name: str = Field(default="memory-index", description="Search index name")
    
    # Authentication
    auth_method: AzureAuthMethod = Field(default=AzureAuthMethod.ACCESS_KEY)
    api_key: Optional[str] = Field(None, description="Admin API key for authentication")
    
    # Entra ID authentication
    use_entra_id: bool = Field(default=False)
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    tenant_id: Optional[str] = None
    
    # Azure Key Vault
    keyvault_url: Optional[str] = None
    secret_name: Optional[str] = None
    
    # Vector configuration
    vector_dimension: int = Field(default=1536, description="Vector embedding dimension")
    embedding_provider: str = Field(default="openai", description="Embedding provider (openai, azure_openai, custom)")
    
    # OpenAI embeddings settings
    openai_api_key: Optional[str] = None
    openai_model: str = Field(default="text-embedding-3-small", description="OpenAI embedding model")
    
    # Azure OpenAI embeddings settings
    azure_openai_endpoint: Optional[str] = None
    azure_openai_api_key: Optional[str] = None
    azure_openai_deployment: Optional[str] = None
    azure_openai_api_version: str = Field(default="2024-02-01", description="Azure OpenAI API version")
    
    # Search settings
    auto_create_index: bool = Field(default=True, description="Auto-create index if it doesn't exist")
    search_top_k: int = Field(default=10, description="Default number of results to return")
    similarity_threshold: float = Field(default=0.7, description="Minimum similarity threshold")
    
    @field_validator('endpoint')
    @classmethod
    def validate_search_endpoint(cls, v):
        """Validate that endpoint is an Azure AI Search endpoint."""
        if not v.endswith('.search.windows.net'):
            raise ValueError('Azure AI Search endpoint must end with .search.windows.net')
        return v
    
    @model_validator(mode='after')
    def validate_search_auth_config(self):
        """Validate that required auth fields are provided."""
        if self.auth_method == AzureAuthMethod.ACCESS_KEY and not self.api_key:
            raise ValueError('api_key required when using access_key auth')
        elif self.auth_method == AzureAuthMethod.ENTRA_ID and not self.use_entra_id:
            raise ValueError('use_entra_id must be True when using entra_id auth')
        elif self.auth_method == AzureAuthMethod.KEYVAULT:
            if not (self.keyvault_url and self.secret_name):
                raise ValueError('keyvault_url and secret_name required when using keyvault auth')
        
        # Validate embedding provider configuration
        if self.embedding_provider == "openai" and not self.openai_api_key:
            raise ValueError('openai_api_key required when using openai embedding provider')
        elif self.embedding_provider == "azure_openai":
            if not all([self.azure_openai_endpoint, self.azure_openai_api_key, self.azure_openai_deployment]):
                raise ValueError('azure_openai_endpoint, azure_openai_api_key, and azure_openai_deployment required for azure_openai provider')
        
        return self
    
    @classmethod
    def from_env(cls) -> "AzureAISearchConfig":
        """Create configuration from environment variables."""
        endpoint = os.getenv('AZURE_SEARCH_ENDPOINT')
        if not endpoint:
            raise ValueError("AZURE_SEARCH_ENDPOINT environment variable required")
        
        # Determine auth method from available env vars
        if os.getenv('AZURE_SEARCH_KEY'):
            auth_method = AzureAuthMethod.ACCESS_KEY
            api_key = os.getenv('AZURE_SEARCH_KEY')
            use_entra_id = False
        elif os.getenv('AZURE_CLIENT_ID'):
            auth_method = AzureAuthMethod.ENTRA_ID
            api_key = None
            use_entra_id = True
        elif os.getenv('AZURE_KEYVAULT_URL'):
            auth_method = AzureAuthMethod.KEYVAULT
            api_key = None
            use_entra_id = False
        else:
            raise ValueError("No Azure authentication method found in environment")
        
        # Determine embedding provider
        embedding_provider = os.getenv('EMBEDDING_PROVIDER', 'openai')
        
        return cls(
            endpoint=endpoint,
            index_name=os.getenv('AZURE_SEARCH_INDEX', 'memory-index'),
            auth_method=auth_method,
            api_key=api_key,
            use_entra_id=use_entra_id,
            client_id=os.getenv('AZURE_CLIENT_ID'),
            client_secret=os.getenv('AZURE_CLIENT_SECRET'),
            tenant_id=os.getenv('AZURE_TENANT_ID'),
            keyvault_url=os.getenv('AZURE_KEYVAULT_URL'),
            secret_name=os.getenv('AZURE_SEARCH_SECRET_NAME'),
            vector_dimension=int(os.getenv('VECTOR_DIMENSION', '1536')),
            embedding_provider=embedding_provider,
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            openai_model=os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small'),
            azure_openai_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
            azure_openai_api_key=os.getenv('AZURE_OPENAI_KEY'),
            azure_openai_deployment=os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT'),
            search_top_k=int(os.getenv('SEARCH_TOP_K', '10')),
            similarity_threshold=float(os.getenv('SIMILARITY_THRESHOLD', '0.7'))
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
    config: Union[AzureRedisConfig, AzureCosmosConfig, AzureBlobConfig, AzureAISearchConfig, MemoryConfig, FileConfig, SQLiteConfig]
    
    @classmethod
    def azure_redis(cls, config: AzureRedisConfig) -> "StorageConfig":
        """Create Azure Redis storage config."""
        return cls(type=StorageType.AZURE_REDIS, config=config)
    
    @classmethod
    def azure_cosmos(cls, config: AzureCosmosConfig) -> "StorageConfig":
        """Create Azure Cosmos DB storage config."""
        return cls(type=StorageType.AZURE_COSMOS, config=config)
    
    @classmethod
    def azure_blob(cls, config: AzureBlobConfig) -> "StorageConfig":
        """Create Azure Blob Storage config."""
        return cls(type=StorageType.AZURE_BLOB, config=config)
    
    @classmethod
    def azure_ai_search(cls, config: AzureAISearchConfig) -> "StorageConfig":
        """Create Azure AI Search storage config."""
        return cls(type=StorageType.AZURE_AI_SEARCH, config=config)
    
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
        elif storage_type == 'azure_cosmos':
            return cls.azure_cosmos(AzureCosmosConfig.from_env())
        elif storage_type == 'azure_blob':
            return cls.azure_blob(AzureBlobConfig.from_env())
        elif storage_type == 'azure_ai_search':
            return cls.azure_ai_search(AzureAISearchConfig.from_env())
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
