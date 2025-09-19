"""
Configuration class for Azure Cosmos DB adapter.
"""

from typing import Optional

from .i_storage_adapter_config import IStorageAdapterConfig


class AzureCosmosAdapterConfig(IStorageAdapterConfig):
    """Configuration for Azure Cosmos DB adapter."""

    def __init__(
        self,
        endpoint: str,
        database_name: str,
        container_name: str,
        primary_key: Optional[str] = None,
        use_managed_identity: bool = False,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        partition_key: str = "/id",
        consistency_level: str = "Session",
        auto_create_database: bool = True,
        auto_create_container: bool = True,
        throughput: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize Azure Cosmos DB configuration.

        :param endpoint: Cosmos DB account endpoint URL
        :param database_name: Database name
        :param container_name: Container name
        :param primary_key: Cosmos DB primary key (if not using managed identity)
        :param use_managed_identity: Whether to use Azure managed identity for authentication
        :param tenant_id: Azure tenant ID (for service principal auth)
        :param client_id: Azure client ID (for service principal auth)
        :param client_secret: Azure client secret (for service principal auth)
        :param partition_key: Partition key path (default: "/id")
        :param consistency_level: Consistency level (Session, Eventual, Strong, etc.)
        :param auto_create_database: Whether to auto-create database if it doesn't exist
        :param auto_create_container: Whether to auto-create container if it doesn't exist
        :param throughput: Provisioned throughput (RU/s) for container
        :param kwargs: Additional configuration parameters
        """
        self.endpoint = endpoint
        self.database_name = database_name
        self.container_name = container_name
        self.primary_key = primary_key
        self.use_managed_identity = use_managed_identity
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.partition_key = partition_key
        self.consistency_level = consistency_level
        self.auto_create_database = auto_create_database
        self.auto_create_container = auto_create_container
        self.throughput = throughput

        # Store additional configuration
        for key, value in kwargs.items():
            setattr(self, key, value)

    def validate(self) -> None:
        """Validate the configuration."""
        if not self.endpoint:
            raise ValueError("endpoint is required")

        if not self.database_name:
            raise ValueError("database_name is required")

        if not self.container_name:
            raise ValueError("container_name is required")

        if not self.use_managed_identity and not self.primary_key:
            raise ValueError("primary_key or use_managed_identity must be provided")

        if self.client_id and not self.client_secret:
            raise ValueError("client_secret is required when client_id is provided")

        if not self.endpoint.startswith(('https://', 'http://')):
            raise ValueError("endpoint must be a valid URL")

        if self.consistency_level not in ['Strong', 'BoundedStaleness', 'Session', 'Eventual', 'ConsistentPrefix']:
            raise ValueError("Invalid consistency_level. Must be one of: Strong, BoundedStaleness, Session, Eventual, ConsistentPrefix")

        if self.throughput and (self.throughput < 400 or self.throughput > 1000000):
            raise ValueError("throughput must be between 400 and 1,000,000 RU/s")