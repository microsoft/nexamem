"""
Azure Blob Storage adapter implementation.
Implements the IStorageAdapter interface for Azure Blob Storage.
"""

import json
import logging
from typing import TYPE_CHECKING, Any, List, Optional

try:
    from azure.storage.blob import BlobServiceClient
    from azure.storage.blob.aio import BlobServiceClient as AsyncBlobServiceClient
    from azure.identity import DefaultAzureCredential
    from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential
    from azure.core.exceptions import AzureError, ResourceNotFoundError
    AZURE_BLOB_AVAILABLE = True
except ImportError:
    BlobServiceClient = None
    AsyncBlobServiceClient = None
    DefaultAzureCredential = None
    AsyncDefaultAzureCredential = None
    AzureError = Exception
    ResourceNotFoundError = Exception
    AZURE_BLOB_AVAILABLE = False

# Type checking imports
if TYPE_CHECKING:
    from azure.storage.blob import BlobServiceClient as BlobClient
    from azure.storage.blob.aio import BlobServiceClient as AsyncBlobClient
else:
    BlobClient = Any
    AsyncBlobClient = Any

from nexamem.schemas.memory_entry import MemoryEntry
from nexamem.schemas.memory_filter import MemoryFilter
from nexamem.schemas.memory_scope import MemoryScope
from nexamem.storage_adapters.configs.azure_blob_adapter_config import AzureBlobAdapterConfig

logger = logging.getLogger(__name__)


class AzureBlobAdapterError(Exception):
    """Base exception for Azure Blob adapter errors."""
    pass


class AzureBlobConnectionError(AzureBlobAdapterError):
    """Raised when Azure Blob connection fails."""
    pass


class AzureBlobAdapter:
    """
    Azure Blob Storage adapter implementing IStorageAdapter interface.

    Key Design:
    - Blob names follow pattern: {prefix}/{env}/{agent_id}/{user_id}/{session_id}/{channel}/{uuid}.json
    - Each MemoryEntry is stored as a separate JSON blob
    - Metadata is stored in blob properties
    - Supports prefix-based querying for filtering
    """

    def __init__(self, config: AzureBlobAdapterConfig):
        """
        Initialize the Azure Blob Storage adapter.

        Args:
            config: Azure Blob adapter configuration
        """
        if not AZURE_BLOB_AVAILABLE:
            raise AzureBlobAdapterError(
                "Azure Blob Storage packages are not installed. Install with: pip install azure-storage-blob azure-identity"
            )

        self.config = config
        config.validate()
        self._client: Optional[BlobClient] = None
        self._async_client: Optional[AsyncBlobClient] = None

    @property
    def client(self) -> "BlobClient":
        """Get or create synchronous Azure Blob client."""
        if self._client is None:
            try:
                if self.config.connection_string:
                    self._client = BlobServiceClient.from_connection_string(
                        self.config.connection_string
                    )
                elif self.config.use_managed_identity:
                    credential = DefaultAzureCredential()
                    account_url = f"https://{self.config.account_name}.blob.core.windows.net"
                    self._client = BlobServiceClient(account_url=account_url, credential=credential)
                else:
                    account_url = f"https://{self.config.account_name}.blob.core.windows.net"
                    self._client = BlobServiceClient(
                        account_url=account_url,
                        credential=self.config.access_key
                    )

                # Ensure container exists
                if self.config.auto_create_container:
                    try:
                        container_client = self._client.get_container_client(self.config.container_name)
                        container_client.create_container()
                        logger.info(f"Created container: {self.config.container_name}")
                    except Exception as e:
                        if "ContainerAlreadyExists" not in str(e):
                            logger.warning(f"Failed to create container: {e}")

                logger.info(f"Connected to Azure Blob Storage account: {self.config.account_name}")
            except Exception as e:
                raise AzureBlobConnectionError(f"Failed to connect to Azure Blob Storage: {e}")
        return self._client

    @property
    def async_client(self) -> "AsyncBlobClient":
        """Get or create asynchronous Azure Blob client."""
        if self._async_client is None:
            try:
                if self.config.connection_string:
                    self._async_client = AsyncBlobServiceClient.from_connection_string(
                        self.config.connection_string
                    )
                elif self.config.use_managed_identity:
                    credential = AsyncDefaultAzureCredential()
                    account_url = f"https://{self.config.account_name}.blob.core.windows.net"
                    self._async_client = AsyncBlobServiceClient(account_url=account_url, credential=credential)
                else:
                    account_url = f"https://{self.config.account_name}.blob.core.windows.net"
                    self._async_client = AsyncBlobServiceClient(
                        account_url=account_url,
                        credential=self.config.access_key
                    )

                logger.info(f"Created async Azure Blob client for account: {self.config.account_name}")
            except Exception as e:
                raise AzureBlobConnectionError(f"Failed to create async Azure Blob client: {e}")
        return self._async_client

    def _build_blob_name(self, entry: MemoryEntry) -> str:
        """
        Build blob name from MemoryEntry.

        Format: {prefix}/{env}/{agent_id}/{user_id}/{session_id}/{channel}/{id}.json
        """
        scope = entry.metadata
        return f"{self.config.blob_prefix}/{scope.env}/{scope.agent_id}/{scope.user_id}/{scope.session_id}/{entry.channel_name}/{entry.id}.json"

    def _serialize_entry(self, entry: MemoryEntry) -> str:
        """Serialize MemoryEntry to JSON string."""
        try:
            entry_dict = entry.model_dump()
            entry_dict["metadata"] = entry.metadata.model_dump()
            return json.dumps(entry_dict, indent=2)
        except Exception as e:
            raise AzureBlobAdapterError(f"Failed to serialize entry: {e}")

    def _deserialize_entry(self, data: str) -> MemoryEntry:
        """Deserialize JSON string to MemoryEntry."""
        try:
            entry_dict = json.loads(data)
            # Convert metadata back to MemoryScope object
            if "metadata" in entry_dict:
                entry_dict["metadata"] = MemoryScope(**entry_dict["metadata"])
            return MemoryEntry(**entry_dict)
        except Exception as e:
            raise AzureBlobAdapterError(f"Failed to deserialize entry: {e}")

    async def write(self, entries: List[MemoryEntry]) -> None:
        """
        Write memory entries to Azure Blob Storage.

        Args:
            entries: List of MemoryEntry objects to write
        """
        if not entries:
            return

        try:
            async_client = self.async_client
            container_client = async_client.get_container_client(self.config.container_name)

            # Ensure container exists
            if self.config.auto_create_container:
                try:
                    await container_client.create_container()
                    logger.info(f"Created container: {self.config.container_name}")
                except Exception as e:
                    if "ContainerAlreadyExists" not in str(e):
                        logger.warning(f"Failed to create container: {e}")

            for entry in entries:
                blob_name = self._build_blob_name(entry)
                blob_data = self._serialize_entry(entry)

                blob_client = container_client.get_blob_client(blob_name)
                await blob_client.upload_blob(
                    blob_data,
                    overwrite=True,
                    content_type="application/json"
                )

                logger.debug(f"Wrote entry to blob: {blob_name}")

        except Exception as e:
            raise AzureBlobAdapterError(f"Failed to write entries: {e}")

    async def read(self, filter: MemoryFilter) -> List[MemoryEntry]:
        """
        Read memory entries from Azure Blob Storage based on filter.

        Args:
            filter: MemoryFilter object specifying search criteria

        Returns:
            List of MemoryEntry objects matching the filter
        """
        try:
            async_client = self.async_client
            container_client = async_client.get_container_client(self.config.container_name)

            # Build prefix for filtering
            scope = filter.memory_scope
            prefix = f"{self.config.blob_prefix}/{scope.env}/{scope.agent_id}/{scope.user_id}"
            if scope.session_id:
                prefix += f"/{scope.session_id}"
            if filter.channel:
                prefix += f"/{filter.channel}"

            entries = []
            async for blob in container_client.list_blobs(name_starts_with=prefix):
                try:
                    blob_client = container_client.get_blob_client(blob.name)
                    blob_data = await blob_client.download_blob()
                    content = await blob_data.readall()
                    entry = self._deserialize_entry(content.decode('utf-8'))

                    # Apply additional filtering
                    if self._matches_filter(entry, filter):
                        entries.append(entry)

                except Exception as e:
                    logger.warning(f"Failed to read blob {blob.name}: {e}")

            # Apply limit if specified
            if filter.limit and len(entries) > filter.limit:
                entries = entries[:filter.limit]

            logger.debug(f"Read {len(entries)} entries from Azure Blob Storage")
            return entries

        except Exception as e:
            raise AzureBlobAdapterError(f"Failed to read entries: {e}")

    def _matches_filter(self, entry: MemoryEntry, filter: MemoryFilter) -> bool:
        """Check if entry matches the filter criteria."""
        # Check tags if specified
        if filter.tags:
            entry_tags = set(entry.tags or [])
            filter_tags = set(filter.tags)
            if not filter_tags.issubset(entry_tags):
                return False

        # Check timestamp range if specified
        if filter.start_time and entry.timestamp < filter.start_time:
            return False
        if filter.end_time and entry.timestamp > filter.end_time:
            return False

        return True

    async def close(self) -> None:
        """Close connections and cleanup resources."""
        if self._async_client:
            await self._async_client.close()
            self._async_client = None

        if self._client:
            self._client.close()
            self._client = None

        logger.info("Azure Blob Storage adapter connections closed")