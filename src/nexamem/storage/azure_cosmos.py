"""
Azure Cosmos DB storage implementation.
Provides both sync and async storage adapters with enterprise features.
"""

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager, suppress
from typing import Any, Dict, List, Optional

try:
    from azure.cosmos import CosmosClient, PartitionKey
    from azure.cosmos import exceptions as cosmos_exceptions
    from azure.cosmos.aio import CosmosClient as AsyncCosmosClient
except ImportError:
    CosmosClient = None
    AsyncCosmosClient = None
    cosmos_exceptions = None
    PartitionKey = None

try:
    from azure.identity import ClientSecretCredential, DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient
except ImportError:
    DefaultAzureCredential = None
    ClientSecretCredential = None
    SecretClient = None

try:
    from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential
    from azure.keyvault.secrets.aio import SecretClient as AsyncSecretClient
except ImportError:
    AsyncDefaultAzureCredential = None
    AsyncSecretClient = None

from ..config.storage import AzureAuthMethod, AzureCosmosConfig
from .base import BaseAsyncStorage, BaseStorage

# Configure logging
logger = logging.getLogger(__name__)


class AzureCosmosConnectionError(Exception):
    """Raised when Azure Cosmos DB connection fails."""
    pass


class AzureCosmosHealthCheck:
    """Health check utilities for Azure Cosmos DB connections."""

    @staticmethod
    async def async_health_check(container) -> Dict[str, Any]:
        """Perform comprehensive async health check."""
        try:
            start_time = time.time()

            # Test connection with a simple query
            query = "SELECT TOP 1 c.id FROM c"
            items = []
            async for item in container.query_items(query=query, enable_cross_partition_query=True):
                items.append(item)
                break  # Just need one item to test connection

            latency = (time.time() - start_time) * 1000  # Convert to ms

            return {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "can_query": True,
                "container_accessible": True
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "error_type": type(e).__name__
            }

    @staticmethod
    def sync_health_check(container) -> Dict[str, Any]:
        """Perform comprehensive sync health check."""
        try:
            start_time = time.time()

            # Test connection with a simple query
            query = "SELECT TOP 1 c.id FROM c"
            items = list(container.query_items(query=query, enable_cross_partition_query=True, max_item_count=1))

            latency = (time.time() - start_time) * 1000  # Convert to ms

            return {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "can_query": True,
                "container_accessible": True,
                "test_items_count": len(items)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "error_type": type(e).__name__
            }


class AsyncAzureCosmosStorage(BaseAsyncStorage):
    """Async Azure Cosmos DB storage adapter with production features."""

    def __init__(self, config: AzureCosmosConfig):
        self.config = config
        self._client: Optional[AsyncCosmosClient] = None
        self._database = None
        self._container = None
        self._connection_lock = asyncio.Lock()

    async def _get_auth_credential(self):
        """Get authentication credential based on configured method."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if self.config.auth_method == AzureAuthMethod.ACCESS_KEY:
                    if not self.config.account_key:
                        raise AzureCosmosConnectionError("Account key required for ACCESS_KEY auth method")
                    return self.config.account_key

                elif self.config.auth_method == AzureAuthMethod.ENTRA_ID:
                    if not AsyncDefaultAzureCredential:
                        raise ImportError("azure-identity package required for Entra ID auth")
                    return AsyncDefaultAzureCredential()

                elif self.config.auth_method == AzureAuthMethod.KEYVAULT:
                    if not AsyncSecretClient or not AsyncDefaultAzureCredential:
                        raise ImportError("azure-keyvault-secrets and azure-identity packages required for Key Vault auth")

                    # Get secret from Key Vault
                    credential = AsyncDefaultAzureCredential()
                    secret_client = AsyncSecretClient(
                        vault_url=self.config.keyvault_url,
                        credential=credential
                    )
                    secret = await secret_client.get_secret(self.config.secret_name)
                    return secret.value

                else:
                    raise AzureCosmosConnectionError(f"Unsupported auth method: {self.config.auth_method}")

            except Exception as e:
                logger.warning(f"Auth attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise AzureCosmosConnectionError(f"Failed to get auth credential after {max_retries} attempts: {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

    async def _ensure_connection(self) -> None:
        """Ensure connection with automatic reconnection."""
        if self._container:
            return

        async with self._connection_lock:
            # Double-check after acquiring lock
            if self._container:
                return

            await self._connect_with_retry()

    async def _connect_with_retry(self) -> None:
        """Connect with retry logic and exponential backoff."""
        max_retries = self.config.retry_total

        for attempt in range(max_retries):
            try:
                await self._establish_connection()
                logger.info("Successfully connected to Azure Cosmos DB")
                return
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise AzureCosmosConnectionError(f"Failed to connect after {max_retries} attempts: {e}")
                await asyncio.sleep(min(2 ** attempt, 10))  # Cap at 10 seconds

    async def _establish_connection(self) -> None:
        """Establish the actual Cosmos DB connection."""
        if not AsyncCosmosClient:
            raise ImportError("azure-cosmos package required for Azure Cosmos DB operations")

        # Get authentication credential
        credential = await self._get_auth_credential()

        # Close existing connection if any
        if self._client:
            with suppress(Exception):
                await self._client.close()

        # Create Cosmos client
        if isinstance(credential, str):
            # Using access key
            self._client = AsyncCosmosClient(
                self.config.endpoint,
                credential,
                consistency_level=self.config.consistency_level,
                request_timeout=self.config.request_timeout,
                connection_timeout=self.config.connection_timeout
            )
        else:
            # Using credential object (Entra ID)
            self._client = AsyncCosmosClient(
                self.config.endpoint,
                credential,
                consistency_level=self.config.consistency_level,
                request_timeout=self.config.request_timeout,
                connection_timeout=self.config.connection_timeout
            )

        # Get database reference
        self._database = self._client.get_database_client(self.config.database_name)

        # Get or create container
        if self.config.auto_create_container:
            try:
                self._container = await self._database.create_container_if_not_exists(
                    id=self.config.container_name,
                    partition_key=PartitionKey(path=self.config.partition_key),
                    offer_throughput=self.config.throughput
                )
            except Exception as e:
                logger.warning(f"Failed to create container, trying to get existing: {e}")
                self._container = self._database.get_container_client(self.config.container_name)
        else:
            self._container = self._database.get_container_client(self.config.container_name)

    async def connect(self) -> None:
        """Establish connection to Azure Cosmos DB."""
        await self._ensure_connection()

    @asynccontextmanager
    async def _cosmos_operation(self):
        """Context manager for Cosmos operations with auto-reconnection."""
        try:
            await self._ensure_connection()
            yield self._container
        except (cosmos_exceptions.CosmosHttpResponseError, ConnectionError) as e:
            logger.warning(f"Cosmos operation failed, attempting reconnection: {e}")
            # Reset client to force reconnection
            self._container = None
            await self._ensure_connection()
            yield self._container
        except Exception as e:
            logger.error(f"Unexpected error in Cosmos operation: {e}")
            raise

    async def store_memory(
        self,
        memory_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        scope: Optional[str] = None
    ) -> bool:
        """Store a memory in Azure Cosmos DB (async) with resilience."""
        try:
            async with self._cosmos_operation() as container:
                memory_data = {
                    'id': memory_id,
                    'content': content,
                    'metadata': metadata or {},
                    'scope': scope or 'default',
                    'created_at': time.time(),
                    'updated_at': time.time(),
                    'memory_type': 'conversation_memory'
                }

                await container.create_item(body=memory_data)

                # Add to audit log
                audit_entry = {
                    'id': f"audit_{memory_id}_{uuid.uuid4()}",
                    'memory_id': memory_id,
                    'action': 'store',
                    'timestamp': time.time(),
                    'scope': scope or 'default',
                    'memory_type': 'audit_log'
                }
                try:
                    await container.create_item(body=audit_entry)
                except Exception as audit_error:
                    logger.warning(f"Failed to create audit entry: {audit_error}")

                return True
        except Exception as e:
            logger.error(f"Failed to store memory {memory_id}: {e}")
            return False

    async def retrieve_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a memory from Azure Cosmos DB (async) with resilience."""
        try:
            async with self._cosmos_operation() as container:
                try:
                    item = await container.read_item(item=memory_id, partition_key=memory_id)
                    if item.get('memory_type') == 'conversation_memory':
                        return item
                except cosmos_exceptions.CosmosResourceNotFoundError:
                    return None
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve memory {memory_id}: {e}")
            return None

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory from Azure Cosmos DB (async) with resilience."""
        try:
            async with self._cosmos_operation() as container:
                # Get memory data first for audit log
                memory_data = await self.retrieve_memory(memory_id)
                if not memory_data:
                    return False

                scope = memory_data.get('scope', 'default')

                # Delete the memory
                await container.delete_item(item=memory_id, partition_key=memory_id)

                # Add to audit log
                audit_entry = {
                    'id': f"audit_{memory_id}_{uuid.uuid4()}",
                    'memory_id': memory_id,
                    'action': 'delete',
                    'timestamp': time.time(),
                    'scope': scope,
                    'memory_type': 'audit_log'
                }
                try:
                    await container.create_item(body=audit_entry)
                except Exception as audit_error:
                    logger.warning(f"Failed to create audit entry: {audit_error}")

                return True
        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            return False

    async def list_memories(
        self,
        scope: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[str]:
        """List memory IDs from Azure Cosmos DB (async) with resilience."""
        try:
            async with self._cosmos_operation() as container:
                if scope:
                    query = "SELECT c.id FROM c WHERE c.scope = @scope AND c.memory_type = 'conversation_memory'"
                    parameters = [{"name": "@scope", "value": scope}]
                else:
                    query = "SELECT c.id FROM c WHERE c.memory_type = 'conversation_memory'"
                    parameters = []

                memory_ids = []
                async for item in container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                    max_item_count=limit
                ):
                    memory_ids.append(item['id'])
                    if limit and len(memory_ids) >= limit:
                        break

                return memory_ids
        except Exception as e:
            logger.error(f"Failed to list memories: {e}")
            return []

    async def search_memories(
        self,
        query: str,
        scope: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[str]:
        """Search memories by content in Azure Cosmos DB (async) with resilience."""
        try:
            async with self._cosmos_operation() as container:
                # Build search query with CONTAINS for text search
                base_query = "SELECT c.id FROM c WHERE CONTAINS(LOWER(c.content), @query) AND c.memory_type = 'conversation_memory'"
                parameters = [{"name": "@query", "value": query.lower()}]

                if scope:
                    base_query += " AND c.scope = @scope"
                    parameters.append({"name": "@scope", "value": scope})

                matching_ids = []
                async for item in container.query_items(
                    query=base_query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                    max_item_count=limit
                ):
                    matching_ids.append(item['id'])
                    if limit and len(matching_ids) >= limit:
                        break

                return matching_ids
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []

    async def get_audit_log(
        self,
        memory_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get audit log entries from Azure Cosmos DB (async) with resilience."""
        try:
            async with self._cosmos_operation() as container:
                if memory_id:
                    query = "SELECT * FROM c WHERE c.memory_id = @memory_id AND c.memory_type = 'audit_log' ORDER BY c.timestamp DESC"
                    parameters = [{"name": "@memory_id", "value": memory_id}]
                else:
                    query = "SELECT * FROM c WHERE c.memory_type = 'audit_log' ORDER BY c.timestamp DESC"
                    parameters = []

                audit_entries = []
                async for item in container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                    max_item_count=limit or 100
                ):
                    audit_entries.append(item)
                    if limit and len(audit_entries) >= limit:
                        break

                return audit_entries
        except Exception as e:
            logger.error(f"Failed to get audit log: {e}")
            return []

    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics from Azure Cosmos DB (async) with resilience."""
        try:
            async with self._cosmos_operation() as container:
                # Count total memories
                memory_query = "SELECT VALUE COUNT(1) FROM c WHERE c.memory_type = 'conversation_memory'"
                memory_count = 0
                async for count in container.query_items(query=memory_query, enable_cross_partition_query=True):
                    memory_count = count
                    break

                # Count unique scopes
                scope_query = "SELECT DISTINCT VALUE c.scope FROM c WHERE c.memory_type = 'conversation_memory'"
                scopes = []
                async for scope in container.query_items(query=scope_query, enable_cross_partition_query=True):
                    scopes.append(scope)

                # Count audit entries
                audit_query = "SELECT VALUE COUNT(1) FROM c WHERE c.memory_type = 'audit_log'"
                audit_count = 0
                async for count in container.query_items(query=audit_query, enable_cross_partition_query=True):
                    audit_count = count
                    break

                return {
                    'total_memories': memory_count,
                    'total_scopes': len(scopes),
                    'audit_entries': audit_count,
                    'storage_type': 'azure_cosmos_async'
                }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                'total_memories': 0,
                'total_scopes': 0,
                'audit_entries': 0,
                'storage_type': 'azure_cosmos_async',
                'error': str(e)
            }

    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status of Azure Cosmos DB connection."""
        try:
            await self._ensure_connection()
            return await AzureCosmosHealthCheck.async_health_check(self._container)
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "error_type": type(e).__name__
            }

    async def ping(self) -> bool:
        """Test Azure Cosmos DB connection with auto-reconnection."""
        try:
            health = await self.get_health_status()
            return health.get("status") == "healthy"
        except Exception as e:
            logger.warning(f"Ping failed: {e}")
            return False

    async def close(self) -> None:
        """Close Azure Cosmos DB connection and cleanup resources."""
        if self._client:
            try:
                await self._client.close()
            except Exception as e:
                logger.warning(f"Error closing Cosmos client: {e}")
            finally:
                self._client = None
                self._database = None
                self._container = None


class AzureCosmosStorage(BaseStorage):
    """Sync Azure Cosmos DB storage adapter with production features."""

    def __init__(self, config: AzureCosmosConfig):
        self.config = config
        self._client: Optional[CosmosClient] = None
        self._database = None
        self._container = None

    def _get_auth_credential(self):
        """Get authentication credential based on configured method."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if self.config.auth_method == AzureAuthMethod.ACCESS_KEY:
                    if not self.config.account_key:
                        raise AzureCosmosConnectionError("Account key required for ACCESS_KEY auth method")
                    return self.config.account_key

                elif self.config.auth_method == AzureAuthMethod.ENTRA_ID:
                    if not DefaultAzureCredential:
                        raise ImportError("azure-identity package required for Entra ID auth")
                    return DefaultAzureCredential()

                elif self.config.auth_method == AzureAuthMethod.KEYVAULT:
                    if not SecretClient or not DefaultAzureCredential:
                        raise ImportError("azure-keyvault-secrets and azure-identity packages required for Key Vault auth")

                    # Get secret from Key Vault
                    credential = DefaultAzureCredential()
                    secret_client = SecretClient(
                        vault_url=self.config.keyvault_url,
                        credential=credential
                    )
                    secret = secret_client.get_secret(self.config.secret_name)
                    return secret.value

                else:
                    raise AzureCosmosConnectionError(f"Unsupported auth method: {self.config.auth_method}")

            except Exception as e:
                logger.warning(f"Auth attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise AzureCosmosConnectionError(f"Failed to get auth credential after {max_retries} attempts: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff

    def _ensure_connection(self) -> None:
        """Ensure connection with automatic reconnection."""
        if self._container:
            return

        self._connect_with_retry()

    def _connect_with_retry(self) -> None:
        """Connect with retry logic and exponential backoff."""
        max_retries = self.config.retry_total

        for attempt in range(max_retries):
            try:
                self._establish_connection()
                logger.info("Successfully connected to Azure Cosmos DB")
                return
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise AzureCosmosConnectionError(f"Failed to connect after {max_retries} attempts: {e}")
                time.sleep(min(2 ** attempt, 10))  # Cap at 10 seconds

    def _establish_connection(self) -> None:
        """Establish the actual Cosmos DB connection."""
        if not CosmosClient:
            raise ImportError("azure-cosmos package required for Azure Cosmos DB operations")

        # Get authentication credential
        credential = self._get_auth_credential()

        # Create Cosmos client
        if isinstance(credential, str):
            # Using access key
            self._client = CosmosClient(
                self.config.endpoint,
                credential,
                consistency_level=self.config.consistency_level,
                request_timeout=self.config.request_timeout,
                connection_timeout=self.config.connection_timeout
            )
        else:
            # Using credential object (Entra ID)
            self._client = CosmosClient(
                self.config.endpoint,
                credential,
                consistency_level=self.config.consistency_level,
                request_timeout=self.config.request_timeout,
                connection_timeout=self.config.connection_timeout
            )

        # Get database reference
        self._database = self._client.get_database_client(self.config.database_name)

        # Get or create container
        if self.config.auto_create_container:
            try:
                self._container = self._database.create_container_if_not_exists(
                    id=self.config.container_name,
                    partition_key=PartitionKey(path=self.config.partition_key),
                    offer_throughput=self.config.throughput
                )
            except Exception as e:
                logger.warning(f"Failed to create container, trying to get existing: {e}")
                self._container = self._database.get_container_client(self.config.container_name)
        else:
            self._container = self._database.get_container_client(self.config.container_name)

    def connect(self) -> None:
        """Establish connection to Azure Cosmos DB."""
        self._ensure_connection()

    def store_memory(
        self,
        memory_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        scope: Optional[str] = None
    ) -> bool:
        """Store a memory in Azure Cosmos DB with resilience."""
        try:
            self._ensure_connection()

            memory_data = {
                'id': memory_id,
                'content': content,
                'metadata': metadata or {},
                'scope': scope or 'default',
                'created_at': time.time(),
                'updated_at': time.time(),
                'memory_type': 'conversation_memory'
            }

            self._container.create_item(body=memory_data)

            # Add to audit log
            audit_entry = {
                'id': f"audit_{memory_id}_{uuid.uuid4()}",
                'memory_id': memory_id,
                'action': 'store',
                'timestamp': time.time(),
                'scope': scope or 'default',
                'memory_type': 'audit_log'
            }
            try:
                self._container.create_item(body=audit_entry)
            except Exception as audit_error:
                logger.warning(f"Failed to create audit entry: {audit_error}")

            return True
        except Exception as e:
            logger.error(f"Failed to store memory {memory_id}: {e}")
            return False

    def retrieve_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a memory from Azure Cosmos DB with resilience."""
        try:
            self._ensure_connection()

            try:
                item = self._container.read_item(item=memory_id, partition_key=memory_id)
                if item.get('memory_type') == 'conversation_memory':
                    return item
            except cosmos_exceptions.CosmosResourceNotFoundError:
                return None
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve memory {memory_id}: {e}")
            return None

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory from Azure Cosmos DB with resilience."""
        try:
            self._ensure_connection()

            # Get memory data first for audit log
            memory_data = self.retrieve_memory(memory_id)
            if not memory_data:
                return False

            scope = memory_data.get('scope', 'default')

            # Delete the memory
            self._container.delete_item(item=memory_id, partition_key=memory_id)

            # Add to audit log
            audit_entry = {
                'id': f"audit_{memory_id}_{uuid.uuid4()}",
                'memory_id': memory_id,
                'action': 'delete',
                'timestamp': time.time(),
                'scope': scope,
                'memory_type': 'audit_log'
            }
            try:
                self._container.create_item(body=audit_entry)
            except Exception as audit_error:
                logger.warning(f"Failed to create audit entry: {audit_error}")

            return True
        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            return False

    def list_memories(
        self,
        scope: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[str]:
        """List memory IDs from Azure Cosmos DB with resilience."""
        try:
            self._ensure_connection()

            if scope:
                query = "SELECT c.id FROM c WHERE c.scope = @scope AND c.memory_type = 'conversation_memory'"
                parameters = [{"name": "@scope", "value": scope}]
            else:
                query = "SELECT c.id FROM c WHERE c.memory_type = 'conversation_memory'"
                parameters = []

            memory_ids = []
            for item in self._container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
                max_item_count=limit
            ):
                memory_ids.append(item['id'])
                if limit and len(memory_ids) >= limit:
                    break

            return memory_ids
        except Exception as e:
            logger.error(f"Failed to list memories: {e}")
            return []

    def search_memories(
        self,
        query: str,
        scope: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[str]:
        """Search memories by content in Azure Cosmos DB with resilience."""
        try:
            self._ensure_connection()

            # Build search query with CONTAINS for text search
            base_query = "SELECT c.id FROM c WHERE CONTAINS(LOWER(c.content), @query) AND c.memory_type = 'conversation_memory'"
            parameters = [{"name": "@query", "value": query.lower()}]

            if scope:
                base_query += " AND c.scope = @scope"
                parameters.append({"name": "@scope", "value": scope})

            matching_ids = []
            for item in self._container.query_items(
                query=base_query,
                parameters=parameters,
                enable_cross_partition_query=True,
                max_item_count=limit
            ):
                matching_ids.append(item['id'])
                if limit and len(matching_ids) >= limit:
                    break

            return matching_ids
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []

    def get_audit_log(
        self,
        memory_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get audit log entries from Azure Cosmos DB with resilience."""
        try:
            self._ensure_connection()

            if memory_id:
                query = "SELECT * FROM c WHERE c.memory_id = @memory_id AND c.memory_type = 'audit_log' ORDER BY c.timestamp DESC"
                parameters = [{"name": "@memory_id", "value": memory_id}]
            else:
                query = "SELECT * FROM c WHERE c.memory_type = 'audit_log' ORDER BY c.timestamp DESC"
                parameters = []

            audit_entries = []
            for item in self._container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
                max_item_count=limit or 100
            ):
                audit_entries.append(item)
                if limit and len(audit_entries) >= limit:
                    break

            return audit_entries
        except Exception as e:
            logger.error(f"Failed to get audit log: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics from Azure Cosmos DB with resilience."""
        try:
            self._ensure_connection()

            # Count total memories
            memory_query = "SELECT VALUE COUNT(1) FROM c WHERE c.memory_type = 'conversation_memory'"
            memory_count = 0
            for count in self._container.query_items(query=memory_query, enable_cross_partition_query=True):
                memory_count = count
                break

            # Count unique scopes
            scope_query = "SELECT DISTINCT VALUE c.scope FROM c WHERE c.memory_type = 'conversation_memory'"
            scopes = []
            for scope in self._container.query_items(query=scope_query, enable_cross_partition_query=True):
                scopes.append(scope)

            # Count audit entries
            audit_query = "SELECT VALUE COUNT(1) FROM c WHERE c.memory_type = 'audit_log'"
            audit_count = 0
            for count in self._container.query_items(query=audit_query, enable_cross_partition_query=True):
                audit_count = count
                break

            return {
                'total_memories': memory_count,
                'total_scopes': len(scopes),
                'audit_entries': audit_count,
                'storage_type': 'azure_cosmos'
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                'total_memories': 0,
                'total_scopes': 0,
                'audit_entries': 0,
                'storage_type': 'azure_cosmos',
                'error': str(e)
            }

    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status of Azure Cosmos DB connection."""
        try:
            self._ensure_connection()
            return AzureCosmosHealthCheck.sync_health_check(self._container)
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "error_type": type(e).__name__
            }

    def ping(self) -> bool:
        """Test Azure Cosmos DB connection with auto-reconnection."""
        try:
            health = self.get_health_status()
            return health.get("status") == "healthy"
        except Exception as e:
            logger.warning(f"Ping failed: {e}")
            return False

    def close(self) -> None:
        """Close Azure Cosmos DB connection."""
        if self._client:
            try:
                self._client.close()
            except Exception as e:
                logger.warning(f"Error closing Cosmos client: {e}")
            finally:
                self._client = None
                self._database = None
                self._container = None
