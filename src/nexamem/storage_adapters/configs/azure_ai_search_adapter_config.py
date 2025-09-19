"""
Configuration class for Azure AI Search adapter.
"""

from typing import List, Optional

from .i_storage_adapter_config import IStorageAdapterConfig


class AzureAISearchAdapterConfig(IStorageAdapterConfig):
    """Configuration for Azure AI Search adapter."""

    def __init__(
        self,
        endpoint: str,
        index_name: str,
        api_key: Optional[str] = None,
        use_managed_identity: bool = False,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        api_version: str = "2023-11-01",
        auto_create_index: bool = True,
        embedding_field: str = "content_vector",
        text_field: str = "content",
        metadata_fields: Optional[List[str]] = None,
        vector_dimensions: int = 1536,
        similarity_algorithm: str = "cosine",
        **kwargs
    ):
        """
        Initialize Azure AI Search configuration.

        :param endpoint: AI Search service endpoint URL
        :param index_name: Search index name
        :param api_key: AI Search admin API key (if not using managed identity)
        :param use_managed_identity: Whether to use Azure managed identity for authentication
        :param tenant_id: Azure tenant ID (for service principal auth)
        :param client_id: Azure client ID (for service principal auth)
        :param client_secret: Azure client secret (for service principal auth)
        :param api_version: AI Search API version
        :param auto_create_index: Whether to auto-create index if it doesn't exist
        :param embedding_field: Field name for vector embeddings
        :param text_field: Field name for text content
        :param metadata_fields: List of additional metadata field names
        :param vector_dimensions: Dimensions for vector embeddings
        :param similarity_algorithm: Vector similarity algorithm (cosine, euclidean, dotProduct)
        :param kwargs: Additional configuration parameters
        """
        self.endpoint = endpoint
        self.index_name = index_name
        self.api_key = api_key
        self.use_managed_identity = use_managed_identity
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.api_version = api_version
        self.auto_create_index = auto_create_index
        self.embedding_field = embedding_field
        self.text_field = text_field
        self.metadata_fields = metadata_fields or ["id", "timestamp", "scope", "tags"]
        self.vector_dimensions = vector_dimensions
        self.similarity_algorithm = similarity_algorithm

        # Store additional configuration
        for key, value in kwargs.items():
            setattr(self, key, value)

    def validate(self) -> None:
        """Validate the configuration."""
        if not self.endpoint:
            raise ValueError("endpoint is required")

        if not self.index_name:
            raise ValueError("index_name is required")

        if not self.use_managed_identity and not self.api_key:
            raise ValueError("api_key or use_managed_identity must be provided")

        if self.client_id and not self.client_secret:
            raise ValueError("client_secret is required when client_id is provided")

        if not self.endpoint.startswith(('https://', 'http://')):
            raise ValueError("endpoint must be a valid URL")

        if self.vector_dimensions <= 0:
            raise ValueError("vector_dimensions must be positive")

        if self.similarity_algorithm not in ['cosine', 'euclidean', 'dotProduct']:
            raise ValueError("similarity_algorithm must be one of: cosine, euclidean, dotProduct")

        if not self.embedding_field:
            raise ValueError("embedding_field is required")

        if not self.text_field:
            raise ValueError("text_field is required")