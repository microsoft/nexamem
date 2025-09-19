"""
Azure Cosmos DB adapter implementation.
Implements the IStorageAdapter interface for Azure Cosmos DB.
"""

import json
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

try:
    from azure.cosmos import CosmosClient
    from azure.cosmos.aio import CosmosClient as AsyncCosmosClient
    from azure.identity import DefaultAzureCredential
    from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential
    from azure.core.exceptions import AzureError, CosmosResourceNotFoundError
    AZURE_COSMOS_AVAILABLE = True
except ImportError:
    CosmosClient = None
    AsyncCosmosClient = None
    DefaultAzureCredential = None
    AsyncDefaultAzureCredential = None
    AzureError = Exception
    CosmosResourceNotFoundError = Exception
    AZURE_COSMOS_AVAILABLE = False

# Type checking imports
if TYPE_CHECKING:
    from azure.cosmos import CosmosClient as CosmosClientType
    from azure.cosmos.aio import CosmosClient as AsyncCosmosClientType
else:
    CosmosClientType = Any
    AsyncCosmosClientType = Any

from nexamem.schemas.memory_entry import MemoryEntry
from nexamem.schemas.memory_filter import MemoryFilter
from nexamem.schemas.memory_scope import MemoryScope
from nexamem.storage_adapters.configs.azure_cosmos_adapter_config import AzureCosmosAdapterConfig

logger = logging.getLogger(__name__)


class AzureCosmosAdapterError(Exception):
    """Base exception for Azure Cosmos adapter errors."""
    pass


class AzureCosmosConnectionError(AzureCosmosAdapterError):
    """Raised when Azure Cosmos connection fails."""
    pass


class AzureCosmosAdapter:
    """
    Azure Cosmos DB adapter implementing IStorageAdapter interface.

    Key Design:
    - Documents are stored with composite IDs including scope information
    - Each MemoryEntry is stored as a separate document
    - Partition key is configurable (default: "/id")
    - Supports SQL queries for complex filtering
    """

    def __init__(self, config: AzureCosmosAdapterConfig):
        """
        Initialize the Azure Cosmos DB adapter.

        Args:
            config: Azure Cosmos adapter configuration
        """
        if not AZURE_COSMOS_AVAILABLE:
            raise AzureCosmosAdapterError(
                "Azure Cosmos DB packages are not installed. Install with: pip install azure-cosmos azure-identity"
            )

        self.config = config
        config.validate()
        self._client: Optional[CosmosClientType] = None
        self._async_client: Optional[AsyncCosmosClientType] = None

    @property
    def client(self) -> "CosmosClientType":
        """Get or create synchronous Azure Cosmos client."""
        if self._client is None:
            try:
                if self.config.use_managed_identity:
                    credential = DefaultAzureCredential()
                    self._client = CosmosClient(
                        url=self.config.endpoint,
                        credential=credential
                    )
                else:
                    self._client = CosmosClient(
                        url=self.config.endpoint,
                        credential=self.config.primary_key
                    )

                # Ensure database and container exist
                if self.config.auto_create_database:
                    try:
                        database = self._client.create_database(
                            id=self.config.database_name,
                            offer_throughput=self.config.throughput
                        )
                        logger.info(f"Created database: {self.config.database_name}")
                    except Exception as e:
                        if "Conflict" not in str(e):
                            logger.warning(f"Failed to create database: {e}")

                if self.config.auto_create_container:
                    try:
                        database = self._client.get_database_client(self.config.database_name)
                        container = database.create_container(
                            id=self.config.container_name,
                            partition_key={"paths": [self.config.partition_key]},
                            offer_throughput=self.config.throughput
                        )
                        logger.info(f"Created container: {self.config.container_name}")
                    except Exception as e:
                        if "Conflict" not in str(e):
                            logger.warning(f"Failed to create container: {e}")

                logger.info(f"Connected to Azure Cosmos DB: {self.config.endpoint}")
            except Exception as e:
                raise AzureCosmosConnectionError(f"Failed to connect to Azure Cosmos DB: {e}") from e
        return self._client

    @property
    def async_client(self) -> "AsyncCosmosClientType":
        """Get or create asynchronous Azure Cosmos client."""
        if self._async_client is None:
            try:
                if self.config.use_managed_identity:
                    credential = AsyncDefaultAzureCredential()
                    self._async_client = AsyncCosmosClient(
                        url=self.config.endpoint,
                        credential=credential
                    )
                else:
                    self._async_client = AsyncCosmosClient(
                        url=self.config.endpoint,
                        credential=self.config.primary_key
                    )

                logger.info(f"Created async Azure Cosmos client: {self.config.endpoint}")
            except Exception as e:
                raise AzureCosmosConnectionError(f"Failed to create async Azure Cosmos client: {e}") from e
        return self._async_client

    def _build_document_id(self, entry: MemoryEntry) -> str:
        """
        Build document ID from MemoryEntry.

        Format: {env}_{agent_id}_{user_id}_{session_id}_{channel}_{id}
        """
        scope = entry.metadata
        return f"{scope.env}_{scope.agent_id}_{scope.user_id}_{scope.session_id}_{entry.channel_name}_{entry.id}"

    def _entry_to_document(self, entry: MemoryEntry) -> Dict[str, Any]:
        """Convert MemoryEntry to Cosmos DB document."""
        doc = entry.model_dump()
        doc["id"] = self._build_document_id(entry)
        doc["metadata"] = entry.metadata.model_dump()
        
        # Add indexed fields for efficient querying
        scope = entry.metadata
        doc["env"] = scope.env
        doc["agent_id"] = scope.agent_id
        doc["user_id"] = scope.user_id
        doc["session_id"] = scope.session_id
        doc["channel_name"] = entry.channel_name
        doc["timestamp_unix"] = int(entry.timestamp.timestamp())
        
        return doc

    def _document_to_entry(self, doc: Dict[str, Any]) -> MemoryEntry:
        """Convert Cosmos DB document to MemoryEntry."""
        # Remove Cosmos DB specific fields
        entry_dict = {k: v for k, v in doc.items() if k not in ["_rid", "_self", "_etag", "_attachments", "_ts"]}
        
        # Convert metadata back to MemoryScope object
        if "metadata" in entry_dict:
            entry_dict["metadata"] = MemoryScope(**entry_dict["metadata"])
        
        # Remove indexed fields that aren't part of MemoryEntry
        for field in ["env", "agent_id", "user_id", "session_id", "channel_name", "timestamp_unix"]:
            entry_dict.pop(field, None)
            
        return MemoryEntry(**entry_dict)

    async def write(self, entries: List[MemoryEntry]) -> None:
        """
        Write memory entries to Azure Cosmos DB.

        Args:
            entries: List of MemoryEntry objects to write
        """
        if not entries:
            return

        try:
            async_client = self.async_client
            database = async_client.get_database_client(self.config.database_name)
            container = database.get_container_client(self.config.container_name)

            # Ensure database and container exist
            if self.config.auto_create_database:
                try:
                    await database.create_database(
                        id=self.config.database_name,
                        offer_throughput=self.config.throughput
                    )
                    logger.info(f"Created database: {self.config.database_name}")
                except Exception as e:
                    if "Conflict" not in str(e):
                        logger.warning(f"Failed to create database: {e}")

            if self.config.auto_create_container:
                try:
                    await container.create_container(
                        id=self.config.container_name,
                        partition_key={"paths": [self.config.partition_key]},
                        offer_throughput=self.config.throughput
                    )
                    logger.info(f"Created container: {self.config.container_name}")
                except Exception as e:
                    if "Conflict" not in str(e):
                        logger.warning(f"Failed to create container: {e}")

            for entry in entries:
                doc = self._entry_to_document(entry)
                await container.upsert_item(body=doc)
                logger.debug(f"Wrote entry to Cosmos DB: {doc['id']}")

        except Exception as e:
            raise AzureCosmosAdapterError(f"Failed to write entries: {e}") from e

    async def read(self, filter: MemoryFilter) -> List[MemoryEntry]:
        """
        Read memory entries from Azure Cosmos DB based on filter.

        Args:
            filter: MemoryFilter object specifying search criteria

        Returns:
            List of MemoryEntry objects matching the filter
        """
        try:
            async_client = self.async_client
            database = async_client.get_database_client(self.config.database_name)
            container = database.get_container_client(self.config.container_name)

            # Build SQL query
            query = self._build_query(filter)
            
            entries = []
            async for item in container.query_items(query=query, enable_cross_partition_query=True):
                try:
                    entry = self._document_to_entry(item)
                    entries.append(entry)
                except Exception as e:
                    logger.warning(f"Failed to deserialize document: {e}")

            # Apply limit if specified
            if filter.limit and len(entries) > filter.limit:
                entries = entries[:filter.limit]

            logger.debug(f"Read {len(entries)} entries from Azure Cosmos DB")
            return entries

        except Exception as e:
            raise AzureCosmosAdapterError(f"Failed to read entries: {e}") from e

    def _build_query(self, filter: MemoryFilter) -> str:
        """Build SQL query from MemoryFilter."""
        conditions = []
        
        # Add scope conditions
        scope = filter.memory_scope
        conditions.append(f"c.env = '{scope.env}'")
        conditions.append(f"c.agent_id = '{scope.agent_id}'")
        conditions.append(f"c.user_id = '{scope.user_id}'")
        
        if scope.session_id:
            conditions.append(f"c.session_id = '{scope.session_id}'")
            
        if filter.channel:
            conditions.append(f"c.channel_name = '{filter.channel}'")
            
        # Add timestamp conditions
        if filter.start_time:
            start_unix = int(filter.start_time.timestamp())
            conditions.append(f"c.timestamp_unix >= {start_unix}")
            
        if filter.end_time:
            end_unix = int(filter.end_time.timestamp())
            conditions.append(f"c.timestamp_unix <= {end_unix}")
            
        # Add tag conditions
        if filter.tags:
            for tag in filter.tags:
                conditions.append(f"ARRAY_CONTAINS(c.tags, '{tag}')")
        
        where_clause = " AND ".join(conditions)
        query = f"SELECT * FROM c WHERE {where_clause}"
        
        if filter.limit:
            query += f" ORDER BY c.timestamp_unix DESC OFFSET 0 LIMIT {filter.limit}"
            
        return query

    async def close(self) -> None:
        """Close connections and cleanup resources."""
        if self._async_client:
            await self._async_client.close()
            self._async_client = None

        if self._client:
            self._client.close()
            self._client = None

        logger.info("Azure Cosmos DB adapter connections closed")