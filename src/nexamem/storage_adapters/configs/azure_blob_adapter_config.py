"""
Configuration class for Azure Blob Storage adapter.
"""

from typing import Optional

from .i_storage_adapter_config import IStorageAdapterConfig


class AzureBlobAdapterConfig(IStorageAdapterConfig):
    """Configuration for Azure Blob Storage adapter."""

    def __init__(
        self,
        account_name: str,
        container_name: str,
        access_key: Optional[str] = None,
        connection_string: Optional[str] = None,
        use_managed_identity: bool = False,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        blob_prefix: str = "nexamem",
        auto_create_container: bool = True,
        **kwargs
    ):
        """
        Initialize Azure Blob Storage configuration.

        :param account_name: Azure Storage account name
        :param container_name: Blob container name
        :param access_key: Storage account access key (if not using managed identity)
        :param connection_string: Full connection string (alternative to account_name + access_key)
        :param use_managed_identity: Whether to use Azure managed identity for authentication
        :param tenant_id: Azure tenant ID (for service principal auth)
        :param client_id: Azure client ID (for service principal auth)
        :param client_secret: Azure client secret (for service principal auth)
        :param blob_prefix: Prefix for blob names
        :param auto_create_container: Whether to auto-create container if it doesn't exist
        :param kwargs: Additional configuration parameters
        """
        self.account_name = account_name
        self.container_name = container_name
        self.access_key = access_key
        self.connection_string = connection_string
        self.use_managed_identity = use_managed_identity
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.blob_prefix = blob_prefix
        self.auto_create_container = auto_create_container

        # Store additional configuration
        for key, value in kwargs.items():
            setattr(self, key, value)

    def validate(self) -> None:
        """Validate the configuration."""
        if not self.account_name and not self.connection_string:
            raise ValueError("Either account_name or connection_string must be provided")

        if not self.container_name:
            raise ValueError("container_name is required")

        if not self.use_managed_identity and not self.access_key and not self.connection_string:
            raise ValueError("access_key, connection_string, or use_managed_identity must be provided")

        if self.client_id and not self.client_secret:
            raise ValueError("client_secret is required when client_id is provided")