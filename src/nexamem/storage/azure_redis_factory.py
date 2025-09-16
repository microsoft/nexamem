"""
Service factory and dependency injection interfaces for Azure Redis.
Implements SOLID principles for better testability and extensibility.
"""

from abc import ABC, abstractmethod
from typing import Protocol, Union, runtime_checkable

from ..config.storage import AzureRedisConfig
from .azure_redis import AsyncAzureRedisStorage, AzureRedisStorage


@runtime_checkable
class RedisClientProtocol(Protocol):
    """Protocol for Redis client interface."""
    
    def ping(self) -> bool:
        """Test connection."""
        ...
    
    def close(self) -> None:
        """Close connection."""
        ...


@runtime_checkable
class AsyncRedisClientProtocol(Protocol):
    """Protocol for async Redis client interface."""
    
    async def ping(self) -> bool:
        """Test connection."""
        ...
    
    async def aclose(self) -> None:
        """Close connection."""
        ...


class AuthenticationProvider(ABC):
    """Abstract authentication provider for Azure Redis."""
    
    @abstractmethod
    def get_auth_token(self) -> str:
        """Get authentication token."""
        pass


class AsyncAuthenticationProvider(ABC):
    """Abstract async authentication provider for Azure Redis."""
    
    @abstractmethod
    async def get_auth_token(self) -> str:
        """Get authentication token."""
        pass


class AccessKeyAuthProvider(AuthenticationProvider):
    """Access key authentication provider."""
    
    def __init__(self, access_key: str):
        self.access_key = access_key
    
    def get_auth_token(self) -> str:
        """Get access key as token."""
        return self.access_key


class AsyncAccessKeyAuthProvider(AsyncAuthenticationProvider):
    """Async access key authentication provider."""
    
    def __init__(self, access_key: str):
        self.access_key = access_key
    
    async def get_auth_token(self) -> str:
        """Get access key as token."""
        return self.access_key


class EntraIdAuthProvider(AuthenticationProvider):
    """Entra ID authentication provider."""
    
    def __init__(self, scope: str = "https://redis.azure.com/.default"):
        self.scope = scope
    
    def get_auth_token(self) -> str:
        """Get Entra ID token."""
        try:
            from azure.identity import DefaultAzureCredential
            credential = DefaultAzureCredential()
            token = credential.get_token(self.scope)
            return token.token
        except ImportError:
            raise ImportError("azure-identity package required for Entra ID auth")


class AsyncEntraIdAuthProvider(AsyncAuthenticationProvider):
    """Async Entra ID authentication provider."""
    
    def __init__(self, scope: str = "https://redis.azure.com/.default"):
        self.scope = scope
    
    async def get_auth_token(self) -> str:
        """Get Entra ID token."""
        try:
            from azure.identity.aio import DefaultAzureCredential
            credential = DefaultAzureCredential()
            token = await credential.get_token(self.scope)
            return token.token
        except ImportError:
            raise ImportError("azure-identity async package required for Entra ID auth")


class KeyVaultAuthProvider(AuthenticationProvider):
    """Key Vault authentication provider."""
    
    def __init__(self, keyvault_url: str, secret_name: str):
        self.keyvault_url = keyvault_url
        self.secret_name = secret_name
    
    def get_auth_token(self) -> str:
        """Get token from Key Vault."""
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient
            
            credential = DefaultAzureCredential()
            secret_client = SecretClient(
                vault_url=self.keyvault_url,
                credential=credential
            )
            secret = secret_client.get_secret(self.secret_name)
            return secret.value
        except ImportError:
            raise ImportError("azure-keyvault-secrets and azure-identity packages required for Key Vault auth")


class AsyncKeyVaultAuthProvider(AsyncAuthenticationProvider):
    """Async Key Vault authentication provider."""
    
    def __init__(self, keyvault_url: str, secret_name: str):
        self.keyvault_url = keyvault_url
        self.secret_name = secret_name
    
    async def get_auth_token(self) -> str:
        """Get token from Key Vault."""
        try:
            from azure.identity.aio import DefaultAzureCredential
            from azure.keyvault.secrets.aio import SecretClient
            
            credential = DefaultAzureCredential()
            secret_client = SecretClient(
                vault_url=self.keyvault_url,
                credential=credential
            )
            secret = await secret_client.get_secret(self.secret_name)
            return secret.value
        except ImportError:
            raise ImportError("azure-keyvault-secrets async and azure-identity packages required for Key Vault auth")


class AzureRedisStorageFactory:
    """Factory for creating Azure Redis storage instances with dependency injection."""
    
    @staticmethod
    def create_auth_provider(config: AzureRedisConfig) -> AuthenticationProvider:
        """Create authentication provider based on config."""
        from ..config.storage import AzureAuthMethod
        
        if config.auth_method == AzureAuthMethod.ACCESS_KEY:
            if not config.access_key:
                raise ValueError("Access key required for ACCESS_KEY auth method")
            return AccessKeyAuthProvider(config.access_key)
        
        elif config.auth_method == AzureAuthMethod.ENTRA_ID:
            return EntraIdAuthProvider()
        
        elif config.auth_method == AzureAuthMethod.KEYVAULT:
            if not (config.keyvault_url and config.secret_name):
                raise ValueError("Keyvault URL and secret name required for KEYVAULT auth method")
            return KeyVaultAuthProvider(config.keyvault_url, config.secret_name)
        
        else:
            raise ValueError(f"Unsupported auth method: {config.auth_method}")
    
    @staticmethod
    def create_async_auth_provider(config: AzureRedisConfig) -> AsyncAuthenticationProvider:
        """Create async authentication provider based on config."""
        from ..config.storage import AzureAuthMethod
        
        if config.auth_method == AzureAuthMethod.ACCESS_KEY:
            if not config.access_key:
                raise ValueError("Access key required for ACCESS_KEY auth method")
            return AsyncAccessKeyAuthProvider(config.access_key)
        
        elif config.auth_method == AzureAuthMethod.ENTRA_ID:
            return AsyncEntraIdAuthProvider()
        
        elif config.auth_method == AzureAuthMethod.KEYVAULT:
            if not (config.keyvault_url and config.secret_name):
                raise ValueError("Keyvault URL and secret name required for KEYVAULT auth method")
            return AsyncKeyVaultAuthProvider(config.keyvault_url, config.secret_name)
        
        else:
            raise ValueError(f"Unsupported auth method: {config.auth_method}")
    
    @staticmethod
    def create_storage(
        config: AzureRedisConfig,
        auth_provider: AuthenticationProvider = None
    ) -> AzureRedisStorage:
        """Create sync Azure Redis storage with optional custom auth provider."""
        if auth_provider is None:
            auth_provider = AzureRedisStorageFactory.create_auth_provider(config)
        
        storage = AzureRedisStorage(config)
        # Override auth method if custom provider given
        if auth_provider:
            storage._auth_provider = auth_provider
        
        return storage
    
    @staticmethod
    def create_async_storage(
        config: AzureRedisConfig,
        auth_provider: AsyncAuthenticationProvider = None
    ) -> AsyncAzureRedisStorage:
        """Create async Azure Redis storage with optional custom auth provider."""
        if auth_provider is None:
            auth_provider = AzureRedisStorageFactory.create_async_auth_provider(config)
        
        storage = AsyncAzureRedisStorage(config)
        # Override auth method if custom provider given
        if auth_provider:
            storage._auth_provider = auth_provider
        
        return storage


# Convenience functions for external projects
def create_azure_redis_storage(
    config: AzureRedisConfig,
    async_preferred: bool = True,
    auth_provider: Union[AuthenticationProvider, AsyncAuthenticationProvider] = None
) -> Union[AzureRedisStorage, AsyncAzureRedisStorage]:
    """
    Convenience function to create Azure Redis storage.
    
    Args:
        config: Azure Redis configuration
        async_preferred: Whether to prefer async implementation
        auth_provider: Optional custom authentication provider
    
    Returns:
        Storage instance (async or sync based on preference)
    """
    if async_preferred:
        return AzureRedisStorageFactory.create_async_storage(config, auth_provider)
    else:
        return AzureRedisStorageFactory.create_storage(config, auth_provider)


def create_from_env(async_preferred: bool = True) -> Union[AzureRedisStorage, AsyncAzureRedisStorage]:
    """
    Create Azure Redis storage from environment variables.
    
    Args:
        async_preferred: Whether to prefer async implementation
    
    Returns:
        Storage instance configured from environment
    """
    config = AzureRedisConfig.from_env()
    return create_azure_redis_storage(config, async_preferred)