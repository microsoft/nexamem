"""
Azure AI Search adapter implementation.
Implements the IStorageAdapter interface for Azure AI Search.
"""

import json
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

try:
    from azure.search.documents import SearchClient
    from azure.search.documents.aio import SearchClient as AsyncSearchClient
    from azure.search.documents.indexes import SearchIndexClient
    from azure.search.documents.indexes.aio import SearchIndexClient as AsyncSearchIndexClient
    from azure.core.credentials import AzureKeyCredential
    from azure.identity import DefaultAzureCredential
    from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential
    from azure.search.documents.models import VectorizedQuery
    from azure.search.documents.indexes.models import (
        SearchIndex,
        SearchField,
        SearchFieldDataType,
        VectorSearch,
        VectorSearchProfile,
        VectorSearchAlgorithmConfiguration,
    )
    from azure.core.exceptions import AzureError, ResourceNotFoundError
    AZURE_SEARCH_AVAILABLE = True
except ImportError:
    SearchClient = None
    AsyncSearchClient = None
    SearchIndexClient = None
    AsyncSearchIndexClient = None
    AzureKeyCredential = None
    DefaultAzureCredential = None
    AsyncDefaultAzureCredential = None
    VectorizedQuery = None
    SearchIndex = None
    SearchField = None
    SearchFieldDataType = None
    VectorSearch = None
    VectorSearchProfile = None
    VectorSearchAlgorithmConfiguration = None
    AzureError = Exception
    ResourceNotFoundError = Exception
    AZURE_SEARCH_AVAILABLE = False

# Type checking imports
if TYPE_CHECKING:
    from azure.search.documents import SearchClient as SearchClientType
    from azure.search.documents.aio import SearchClient as AsyncSearchClientType
else:
    SearchClientType = Any
    AsyncSearchClientType = Any

from nexamem.schemas.memory_entry import MemoryEntry
from nexamem.schemas.memory_filter import MemoryFilter
from nexamem.schemas.memory_scope import MemoryScope
from nexamem.storage_adapters.configs.azure_ai_search_adapter_config import AzureAISearchAdapterConfig

logger = logging.getLogger(__name__)


class AzureAISearchAdapterError(Exception):
    """Base exception for Azure AI Search adapter errors."""
    pass


class AzureAISearchConnectionError(AzureAISearchAdapterError):
    """Raised when Azure AI Search connection fails."""
    pass


class AzureAISearchAdapter:
    """
    Azure AI Search adapter implementing IStorageAdapter interface.

    Key Design:
    - Documents are stored with vector embeddings for semantic search
    - Each MemoryEntry is indexed as a separate document
    - Supports both text and vector-based queries
    - Automatic index creation with appropriate schema
    """

    def __init__(self, config: AzureAISearchAdapterConfig):
        """
        Initialize the Azure AI Search adapter.

        Args:
            config: Azure AI Search adapter configuration
        """
        if not AZURE_SEARCH_AVAILABLE:
            raise AzureAISearchAdapterError(
                "Azure AI Search packages are not installed. Install with: pip install azure-search-documents azure-identity"
            )

        self.config = config
        config.validate()
        self._search_client: Optional[SearchClientType] = None
        self._async_search_client: Optional[AsyncSearchClientType] = None
        self._index_client: Optional[Any] = None
        self._async_index_client: Optional[Any] = None

    @property
    def search_client(self) -> "SearchClientType":
        """Get or create synchronous Azure AI Search client."""
        if self._search_client is None:
            try:
                if self.config.use_managed_identity:
                    credential = DefaultAzureCredential()
                else:
                    credential = AzureKeyCredential(self.config.api_key)

                self._search_client = SearchClient(
                    endpoint=self.config.endpoint,
                    index_name=self.config.index_name,
                    credential=credential,
                    api_version=self.config.api_version
                )

                logger.info(f"Connected to Azure AI Search: {self.config.endpoint}")
            except Exception as e:
                raise AzureAISearchConnectionError(f"Failed to connect to Azure AI Search: {e}") from e
        return self._search_client

    @property
    def async_search_client(self) -> "AsyncSearchClientType":
        """Get or create asynchronous Azure AI Search client."""
        if self._async_search_client is None:
            try:
                if self.config.use_managed_identity:
                    credential = AsyncDefaultAzureCredential()
                else:
                    credential = AzureKeyCredential(self.config.api_key)

                self._async_search_client = AsyncSearchClient(
                    endpoint=self.config.endpoint,
                    index_name=self.config.index_name,
                    credential=credential,
                    api_version=self.config.api_version
                )

                logger.info(f"Created async Azure AI Search client: {self.config.endpoint}")
            except Exception as e:
                raise AzureAISearchConnectionError(f"Failed to create async Azure AI Search client: {e}") from e
        return self._async_search_client

    @property
    def index_client(self) -> Any:
        """Get or create synchronous Azure AI Search index client."""
        if self._index_client is None:
            try:
                if self.config.use_managed_identity:
                    credential = DefaultAzureCredential()
                else:
                    credential = AzureKeyCredential(self.config.api_key)

                self._index_client = SearchIndexClient(
                    endpoint=self.config.endpoint,
                    credential=credential,
                    api_version=self.config.api_version
                )
            except Exception as e:
                raise AzureAISearchConnectionError(f"Failed to create index client: {e}") from e
        return self._index_client

    def _create_index_schema(self) -> Any:
        """Create the search index schema."""
        fields = [
            SearchField(name="id", type=SearchFieldDataType.String, key=True, searchable=False),
            SearchField(name=self.config.text_field, type=SearchFieldDataType.String, searchable=True, retrievable=True),
            SearchField(name=self.config.embedding_field, type=SearchFieldDataType.Collection(SearchFieldDataType.Single), 
                       searchable=True, vector_search_dimensions=self.config.vector_dimensions),
        ]

        # Add metadata fields
        for field_name in self.config.metadata_fields:
            fields.append(SearchField(name=field_name, type=SearchFieldDataType.String, searchable=True, filterable=True))

        # Vector search configuration
        vector_search = VectorSearch(
            profiles=[
                VectorSearchProfile(
                    name="default",
                    algorithm_configuration_name="default"
                )
            ],
            algorithms=[
                VectorSearchAlgorithmConfiguration(
                    name="default",
                    kind=self.config.similarity_algorithm
                )
            ]
        )

        return SearchIndex(
            name=self.config.index_name,
            fields=fields,
            vector_search=vector_search
        )

    def _entry_to_document(self, entry: MemoryEntry, embedding: Optional[List[float]] = None) -> Dict[str, Any]:
        """Convert MemoryEntry to AI Search document."""
        doc = {
            "id": self._build_document_id(entry),
            self.config.text_field: entry.content
        }

        if embedding:
            doc[self.config.embedding_field] = embedding

        # Add metadata fields
        scope = entry.metadata
        doc.update({
            "env": scope.env,
            "agent_id": scope.agent_id,
            "user_id": scope.user_id,
            "session_id": scope.session_id,
            "channel_name": entry.channel_name,
            "timestamp": entry.timestamp.isoformat(),
            "tags": entry.tags or []
        })

        return doc

    def _build_document_id(self, entry: MemoryEntry) -> str:
        """Build document ID from MemoryEntry."""
        scope = entry.metadata
        return f"{scope.env}_{scope.agent_id}_{scope.user_id}_{scope.session_id}_{entry.channel_name}_{entry.id}"

    async def write(self, entries: List[MemoryEntry]) -> None:
        """
        Write memory entries to Azure AI Search.

        Args:
            entries: List of MemoryEntry objects to write
        """
        if not entries:
            return

        try:
            # Ensure index exists
            if self.config.auto_create_index:
                await self._ensure_index_exists()

            async_client = self.async_search_client
            documents = []

            for entry in entries:
                # Note: This implementation assumes embeddings are provided elsewhere
                # In a real implementation, you might generate embeddings here
                doc = self._entry_to_document(entry)
                documents.append(doc)

            await async_client.upload_documents(documents)
            logger.debug(f"Uploaded {len(documents)} documents to Azure AI Search")

        except Exception as e:
            raise AzureAISearchAdapterError(f"Failed to write entries: {e}") from e

    async def read(self, filter: MemoryFilter) -> List[MemoryEntry]:
        """
        Read memory entries from Azure AI Search based on filter.

        Args:
            filter: MemoryFilter object specifying search criteria

        Returns:
            List of MemoryEntry objects matching the filter
        """
        try:
            async_client = self.async_search_client

            # Build search query
            search_filter = self._build_search_filter(filter)
            
            results = await async_client.search(
                search_text="*",
                filter=search_filter,
                top=filter.limit or 50,
                include_total_count=True
            )

            entries = []
            async for result in results:
                try:
                    entry = self._document_to_entry(result)
                    entries.append(entry)
                except Exception as e:
                    logger.warning(f"Failed to deserialize search result: {e}")

            logger.debug(f"Read {len(entries)} entries from Azure AI Search")
            return entries

        except Exception as e:
            raise AzureAISearchAdapterError(f"Failed to read entries: {e}") from e

    def _build_search_filter(self, filter: MemoryFilter) -> str:
        """Build OData filter expression from MemoryFilter."""
        conditions = []

        # Add scope conditions
        scope = filter.memory_scope
        conditions.append(f"env eq '{scope.env}'")
        conditions.append(f"agent_id eq '{scope.agent_id}'")
        conditions.append(f"user_id eq '{scope.user_id}'")

        if scope.session_id:
            conditions.append(f"session_id eq '{scope.session_id}'")

        if filter.channel:
            conditions.append(f"channel_name eq '{filter.channel}'")

        # Add timestamp conditions
        if filter.start_time:
            conditions.append(f"timestamp ge {filter.start_time.isoformat()}")

        if filter.end_time:
            conditions.append(f"timestamp le {filter.end_time.isoformat()}")

        # Add tag conditions
        if filter.tags:
            tag_conditions = [f"tags/any(t: t eq '{tag}')" for tag in filter.tags]
            conditions.extend(tag_conditions)

        return " and ".join(conditions)

    def _document_to_entry(self, doc: Dict[str, Any]) -> MemoryEntry:
        """Convert AI Search document to MemoryEntry."""
        # Extract core fields
        content = doc.get(self.config.text_field, "")
        
        # Build MemoryScope from document fields
        scope = MemoryScope(
            env=doc.get("env", ""),
            agent_id=doc.get("agent_id", ""),
            user_id=doc.get("user_id", ""),
            session_id=doc.get("session_id", "")
        )

        # Parse document ID to extract entry ID
        doc_id = doc.get("id", "")
        entry_id = doc_id.split("_")[-1] if doc_id else ""

        return MemoryEntry(
            id=entry_id,
            content=content,
            metadata=scope,
            channel_name=doc.get("channel_name", ""),
            timestamp=doc.get("timestamp", ""),
            tags=doc.get("tags", [])
        )

    async def _ensure_index_exists(self) -> None:
        """Ensure the search index exists."""
        try:
            if self.config.use_managed_identity:
                credential = AsyncDefaultAzureCredential()
            else:
                credential = AzureKeyCredential(self.config.api_key)

            async_index_client = AsyncSearchIndexClient(
                endpoint=self.config.endpoint,
                credential=credential,
                api_version=self.config.api_version
            )

            try:
                await async_index_client.get_index(self.config.index_name)
                logger.debug(f"Index {self.config.index_name} already exists")
            except ResourceNotFoundError:
                # Create the index
                index_schema = self._create_index_schema()
                await async_index_client.create_index(index_schema)
                logger.info(f"Created search index: {self.config.index_name}")

            await async_index_client.close()

        except Exception as e:
            logger.warning(f"Failed to ensure index exists: {e}")

    async def close(self) -> None:
        """Close connections and cleanup resources."""
        if self._async_search_client:
            await self._async_search_client.close()
            self._async_search_client = None

        if self._async_index_client:
            await self._async_index_client.close()
            self._async_index_client = None

        logger.info("Azure AI Search adapter connections closed")