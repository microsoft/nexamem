"""
Azure Blob Storage implementation.
Provides both sync and async storage adapters with enterprise features.
"""

import asyncio
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union

try:
    from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
    from azure.storage.blob.aio import BlobServiceClient as AsyncBlobServiceClient
    from azure.core.exceptions import ResourceNotFoundError, ServiceRequestError
except ImportError:
    BlobServiceClient = None
    BlobClient = None
    ContainerClient = None
    AsyncBlobServiceClient = None
    ResourceNotFoundError = Exception
    ServiceRequestError = Exception

try:
    from azure.identity import DefaultAzureCredential, ClientSecretCredential
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

from ..config.storage import AzureBlobConfig, AzureAuthMethod
from .base import BaseStorage, BaseAsyncStorage


# Configure logging
logger = logging.getLogger(__name__)


class AzureBlobConnectionError(Exception):
    """Raised when Azure Blob Storage connection fails."""
    pass


class AzureBlobHealthCheck:
    """Health check utilities for Azure Blob Storage connections."""
    
    @staticmethod
    async def async_health_check(container_client) -> Dict[str, Any]:
        """Perform comprehensive async health check."""
        try:
            start_time = time.time()
            
            # Test connection by checking container properties
            properties = await container_client.get_container_properties()
            
            latency = (time.time() - start_time) * 1000  # Convert to ms
            
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "container_accessible": True,
                "container_name": properties.name,
                "last_modified": properties.last_modified.isoformat() if properties.last_modified else None
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    @staticmethod
    def sync_health_check(container_client) -> Dict[str, Any]:
        """Perform comprehensive sync health check."""
        try:
            start_time = time.time()
            
            # Test connection by checking container properties
            properties = container_client.get_container_properties()
            
            latency = (time.time() - start_time) * 1000  # Convert to ms
            
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "container_accessible": True,
                "container_name": properties.name,
                "last_modified": properties.last_modified.isoformat() if properties.last_modified else None
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "error_type": type(e).__name__
            }


class AsyncAzureBlobStorage(BaseAsyncStorage):
    """Async Azure Blob Storage adapter with production features."""

    def __init__(self, config: AzureBlobConfig):
        self.config = config
        self._service_client: Optional[AsyncBlobServiceClient] = None
        self._container_client = None
        self._connection_lock = asyncio.Lock()

    async def _get_auth_credential(self):
        """Get authentication credential based on configured method."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if self.config.auth_method == AzureAuthMethod.ACCESS_KEY:
                    if self.config.connection_string:
                        return self.config.connection_string
                    elif self.config.account_key:
                        return self.config.account_key
                    else:
                        raise AzureBlobConnectionError("Account key or connection string required for ACCESS_KEY auth method")

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
                    raise AzureBlobConnectionError(f"Unsupported auth method: {self.config.auth_method}")

            except Exception as e:
                logger.warning(f"Auth attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise AzureBlobConnectionError(f"Failed to get auth credential after {max_retries} attempts: {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

    async def _ensure_connection(self) -> None:
        """Ensure connection with automatic reconnection."""
        if self._container_client:
            return

        async with self._connection_lock:
            # Double-check after acquiring lock
            if self._container_client:
                return
            
            await self._connect_with_retry()

    async def _connect_with_retry(self) -> None:
        """Connect with retry logic and exponential backoff."""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                await self._establish_connection()
                logger.info("Successfully connected to Azure Blob Storage")
                return
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise AzureBlobConnectionError(f"Failed to connect after {max_retries} attempts: {e}")
                await asyncio.sleep(min(2 ** attempt, 10))  # Cap at 10 seconds

    async def _establish_connection(self) -> None:
        """Establish the actual Blob Storage connection."""
        if not AsyncBlobServiceClient:
            raise ImportError("azure-storage-blob package required for Azure Blob Storage operations")

        # Get authentication credential
        credential = await self._get_auth_credential()

        # Close existing connection if any
        if self._service_client:
            try:
                await self._service_client.close()
            except Exception:
                pass

        # Create Blob service client
        if isinstance(credential, str):
            if self.config.connection_string:
                # Using connection string
                self._service_client = AsyncBlobServiceClient.from_connection_string(credential)
            else:
                # Using account key
                account_url = f"https://{self.config.account_name}.blob.core.windows.net"
                self._service_client = AsyncBlobServiceClient(account_url=account_url, credential=credential)
        else:
            # Using credential object (Entra ID)
            account_url = f"https://{self.config.account_name}.blob.core.windows.net"
            self._service_client = AsyncBlobServiceClient(account_url=account_url, credential=credential)

        # Get or create container
        self._container_client = self._service_client.get_container_client(self.config.container_name)
        
        if self.config.auto_create_container:
            try:
                await self._container_client.create_container()
            except Exception as e:
                # Container might already exist, which is fine
                if "ContainerAlreadyExists" not in str(e):
                    logger.warning(f"Failed to create container: {e}")

    async def connect(self) -> None:
        """Establish connection to Azure Blob Storage."""
        await self._ensure_connection()

    @asynccontextmanager
    async def _blob_operation(self):
        """Context manager for Blob operations with auto-reconnection."""
        try:
            await self._ensure_connection()
            yield self._container_client
        except (ServiceRequestError, ConnectionError) as e:
            logger.warning(f"Blob operation failed, attempting reconnection: {e}")
            # Reset client to force reconnection
            self._container_client = None
            await self._ensure_connection()
            yield self._container_client
        except Exception as e:
            logger.error(f"Unexpected error in Blob operation: {e}")
            raise

    def _get_blob_name(self, memory_id: str, memory_type: str = "memory") -> str:
        """Generate blob name for a memory."""
        return f"{self.config.blob_prefix}/{memory_type}/{memory_id}.json"

    def _get_metadata_blob_name(self, memory_id: str) -> str:
        """Generate blob name for memory metadata."""
        return f"{self.config.blob_prefix}/metadata/{memory_id}.json"

    async def store_memory(
        self,
        memory_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        scope: Optional[str] = None
    ) -> bool:
        """Store a memory in Azure Blob Storage (async) with resilience."""
        try:
            async with self._blob_operation() as container_client:
                memory_data = {
                    'id': memory_id,
                    'content': content,
                    'metadata': metadata or {},
                    'scope': scope or 'default',
                    'created_at': time.time(),
                    'updated_at': time.time(),
                    'memory_type': 'conversation_memory'
                }
                
                # Store memory as blob
                blob_name = self._get_blob_name(memory_id)
                blob_client = container_client.get_blob_client(blob_name)
                
                await blob_client.upload_blob(
                    data=json.dumps(memory_data),
                    overwrite=True,
                    blob_type="BlockBlob",
                    tier=self.config.tier
                )
                
                # Store metadata separately for easier querying
                metadata_blob_name = self._get_metadata_blob_name(memory_id)
                metadata_blob_client = container_client.get_blob_client(metadata_blob_name)
                
                metadata_info = {
                    'memory_id': memory_id,
                    'scope': scope or 'default',
                    'created_at': memory_data['created_at'],
                    'updated_at': memory_data['updated_at'],
                    'content_size': len(content.encode('utf-8')),
                    'has_metadata': bool(metadata)
                }
                
                await metadata_blob_client.upload_blob(
                    data=json.dumps(metadata_info),
                    overwrite=True,
                    blob_type="BlockBlob",
                    tier="Hot"  # Keep metadata in hot tier for faster access
                )
                
                # Add to audit log
                audit_entry = {
                    'memory_id': memory_id,
                    'action': 'store',
                    'timestamp': time.time(),
                    'scope': scope or 'default',
                    'blob_name': blob_name
                }
                
                audit_blob_name = self._get_blob_name(f"audit_{memory_id}_{uuid.uuid4()}", "audit")
                audit_blob_client = container_client.get_blob_client(audit_blob_name)
                
                try:
                    await audit_blob_client.upload_blob(
                        data=json.dumps(audit_entry),
                        overwrite=True,
                        blob_type="BlockBlob",
                        tier="Cool"  # Audit logs can be in cool tier
                    )
                except Exception as audit_error:
                    logger.warning(f"Failed to create audit entry: {audit_error}")
                
                return True
        except Exception as e:
            logger.error(f"Failed to store memory {memory_id}: {e}")
            return False

    async def retrieve_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a memory from Azure Blob Storage (async) with resilience."""
        try:
            async with self._blob_operation() as container_client:
                blob_name = self._get_blob_name(memory_id)
                blob_client = container_client.get_blob_client(blob_name)
                
                try:
                    blob_data = await blob_client.download_blob()
                    content = await blob_data.readall()
                    memory_data = json.loads(content.decode('utf-8'))
                    
                    if memory_data.get('memory_type') == 'conversation_memory':
                        return memory_data
                except ResourceNotFoundError:
                    return None
                
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve memory {memory_id}: {e}")
            return None

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory from Azure Blob Storage (async) with resilience."""
        try:
            async with self._blob_operation() as container_client:
                # Get memory data first for audit log
                memory_data = await self.retrieve_memory(memory_id)
                if not memory_data:
                    return False
                
                scope = memory_data.get('scope', 'default')
                
                # Delete the memory blob
                blob_name = self._get_blob_name(memory_id)
                blob_client = container_client.get_blob_client(blob_name)
                await blob_client.delete_blob()
                
                # Delete the metadata blob
                metadata_blob_name = self._get_metadata_blob_name(memory_id)
                metadata_blob_client = container_client.get_blob_client(metadata_blob_name)
                try:
                    await metadata_blob_client.delete_blob()
                except ResourceNotFoundError:
                    pass  # Metadata blob might not exist
                
                # Add to audit log
                audit_entry = {
                    'memory_id': memory_id,
                    'action': 'delete',
                    'timestamp': time.time(),
                    'scope': scope,
                    'blob_name': blob_name
                }
                
                audit_blob_name = self._get_blob_name(f"audit_{memory_id}_{uuid.uuid4()}", "audit")
                audit_blob_client = container_client.get_blob_client(audit_blob_name)
                
                try:
                    await audit_blob_client.upload_blob(
                        data=json.dumps(audit_entry),
                        overwrite=True,
                        blob_type="BlockBlob",
                        tier="Cool"
                    )
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
        """List memory IDs from Azure Blob Storage (async) with resilience."""
        try:
            async with self._blob_operation() as container_client:
                memory_ids = []
                
                # List metadata blobs to get memory info efficiently
                metadata_prefix = f"{self.config.blob_prefix}/metadata/"
                
                async for blob in container_client.list_blobs(name_starts_with=metadata_prefix):
                    if limit and len(memory_ids) >= limit:
                        break
                    
                    try:
                        # Download metadata blob to check scope
                        blob_client = container_client.get_blob_client(blob.name)
                        blob_data = await blob_client.download_blob()
                        content = await blob_data.readall()
                        metadata_info = json.loads(content.decode('utf-8'))
                        
                        if scope is None or metadata_info.get('scope') == scope:
                            memory_ids.append(metadata_info['memory_id'])
                    
                    except Exception as e:
                        logger.warning(f"Failed to process metadata blob {blob.name}: {e}")
                        continue
                
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
        """Search memories by content in Azure Blob Storage (async) with resilience."""
        try:
            async with self._blob_operation() as container_client:
                matching_ids = []
                query_lower = query.lower()
                
                # List memory blobs and search content
                memory_prefix = f"{self.config.blob_prefix}/memory/"
                
                async for blob in container_client.list_blobs(name_starts_with=memory_prefix):
                    if limit and len(matching_ids) >= limit:
                        break
                    
                    try:
                        # Download blob to search content
                        blob_client = container_client.get_blob_client(blob.name)
                        blob_data = await blob_client.download_blob()
                        content = await blob_data.readall()
                        memory_data = json.loads(content.decode('utf-8'))
                        
                        # Check scope filter
                        if scope and memory_data.get('scope') != scope:
                            continue
                        
                        # Search in content
                        if query_lower in memory_data.get('content', '').lower():
                            matching_ids.append(memory_data['id'])
                    
                    except Exception as e:
                        logger.warning(f"Failed to search blob {blob.name}: {e}")
                        continue
                
                return matching_ids
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []

    async def get_audit_log(
        self,
        memory_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get audit log entries from Azure Blob Storage (async) with resilience."""
        try:
            async with self._blob_operation() as container_client:
                audit_entries = []
                
                # List audit blobs
                audit_prefix = f"{self.config.blob_prefix}/audit/"
                
                async for blob in container_client.list_blobs(name_starts_with=audit_prefix):
                    if limit and len(audit_entries) >= limit:
                        break
                    
                    try:
                        # Download audit blob
                        blob_client = container_client.get_blob_client(blob.name)
                        blob_data = await blob_client.download_blob()
                        content = await blob_data.readall()
                        audit_entry = json.loads(content.decode('utf-8'))
                        
                        # Filter by memory_id if specified
                        if memory_id is None or audit_entry.get('memory_id') == memory_id:
                            audit_entry['blob_name'] = blob.name
                            audit_entry['blob_created'] = blob.creation_time.isoformat() if blob.creation_time else None
                            audit_entries.append(audit_entry)
                    
                    except Exception as e:
                        logger.warning(f"Failed to process audit blob {blob.name}: {e}")
                        continue
                
                # Sort by timestamp (newest first)
                audit_entries.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
                
                return audit_entries[:limit] if limit else audit_entries
        except Exception as e:
            logger.error(f"Failed to get audit log: {e}")
            return []

    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics from Azure Blob Storage (async) with resilience."""
        try:
            async with self._blob_operation() as container_client:
                total_memories = 0
                total_size = 0
                scopes = set()
                audit_count = 0
                
                # Count blobs by prefix
                async for blob in container_client.list_blobs():
                    if blob.name.startswith(f"{self.config.blob_prefix}/memory/"):
                        total_memories += 1
                        total_size += blob.size or 0
                    elif blob.name.startswith(f"{self.config.blob_prefix}/audit/"):
                        audit_count += 1
                
                # Get scopes from metadata blobs (more efficient)
                metadata_prefix = f"{self.config.blob_prefix}/metadata/"
                async for blob in container_client.list_blobs(name_starts_with=metadata_prefix):
                    try:
                        blob_client = container_client.get_blob_client(blob.name)
                        blob_data = await blob_client.download_blob()
                        content = await blob_data.readall()
                        metadata_info = json.loads(content.decode('utf-8'))
                        scopes.add(metadata_info.get('scope', 'default'))
                    except Exception:
                        continue
                
                return {
                    'total_memories': total_memories,
                    'total_scopes': len(scopes),
                    'audit_entries': audit_count,
                    'total_size_bytes': total_size,
                    'storage_type': 'azure_blob_async'
                }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                'total_memories': 0,
                'total_scopes': 0,
                'audit_entries': 0,
                'total_size_bytes': 0,
                'storage_type': 'azure_blob_async',
                'error': str(e)
            }

    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status of Azure Blob Storage connection."""
        try:
            await self._ensure_connection()
            return await AzureBlobHealthCheck.async_health_check(self._container_client)
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "error_type": type(e).__name__
            }

    async def ping(self) -> bool:
        """Test Azure Blob Storage connection with auto-reconnection."""
        try:
            health = await self.get_health_status()
            return health.get("status") == "healthy"
        except Exception as e:
            logger.warning(f"Ping failed: {e}")
            return False

    async def close(self) -> None:
        """Close Azure Blob Storage connection and cleanup resources."""
        if self._service_client:
            try:
                await self._service_client.close()
            except Exception as e:
                logger.warning(f"Error closing Blob service client: {e}")
            finally:
                self._service_client = None
                self._container_client = None


class AzureBlobStorage(BaseStorage):
    """Sync Azure Blob Storage adapter with production features."""

    def __init__(self, config: AzureBlobConfig):
        self.config = config
        self._service_client: Optional[BlobServiceClient] = None
        self._container_client = None

    def _get_auth_credential(self):
        """Get authentication credential based on configured method."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if self.config.auth_method == AzureAuthMethod.ACCESS_KEY:
                    if self.config.connection_string:
                        return self.config.connection_string
                    elif self.config.account_key:
                        return self.config.account_key
                    else:
                        raise AzureBlobConnectionError("Account key or connection string required for ACCESS_KEY auth method")

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
                    raise AzureBlobConnectionError(f"Unsupported auth method: {self.config.auth_method}")

            except Exception as e:
                logger.warning(f"Auth attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise AzureBlobConnectionError(f"Failed to get auth credential after {max_retries} attempts: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff

    def _ensure_connection(self) -> None:
        """Ensure connection with automatic reconnection."""
        if self._container_client:
            return
        
        self._connect_with_retry()

    def _connect_with_retry(self) -> None:
        """Connect with retry logic and exponential backoff."""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                self._establish_connection()
                logger.info("Successfully connected to Azure Blob Storage")
                return
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise AzureBlobConnectionError(f"Failed to connect after {max_retries} attempts: {e}")
                time.sleep(min(2 ** attempt, 10))  # Cap at 10 seconds

    def _establish_connection(self) -> None:
        """Establish the actual Blob Storage connection."""
        if not BlobServiceClient:
            raise ImportError("azure-storage-blob package required for Azure Blob Storage operations")

        # Get authentication credential
        credential = self._get_auth_credential()

        # Create Blob service client
        if isinstance(credential, str):
            if self.config.connection_string:
                # Using connection string
                self._service_client = BlobServiceClient.from_connection_string(credential)
            else:
                # Using account key
                account_url = f"https://{self.config.account_name}.blob.core.windows.net"
                self._service_client = BlobServiceClient(account_url=account_url, credential=credential)
        else:
            # Using credential object (Entra ID)
            account_url = f"https://{self.config.account_name}.blob.core.windows.net"
            self._service_client = BlobServiceClient(account_url=account_url, credential=credential)

        # Get or create container
        self._container_client = self._service_client.get_container_client(self.config.container_name)
        
        if self.config.auto_create_container:
            try:
                self._container_client.create_container()
            except Exception as e:
                # Container might already exist, which is fine
                if "ContainerAlreadyExists" not in str(e):
                    logger.warning(f"Failed to create container: {e}")

    def connect(self) -> None:
        """Establish connection to Azure Blob Storage."""
        self._ensure_connection()

    def _get_blob_name(self, memory_id: str, memory_type: str = "memory") -> str:
        """Generate blob name for a memory."""
        return f"{self.config.blob_prefix}/{memory_type}/{memory_id}.json"

    def _get_metadata_blob_name(self, memory_id: str) -> str:
        """Generate blob name for memory metadata."""
        return f"{self.config.blob_prefix}/metadata/{memory_id}.json"

    def store_memory(
        self,
        memory_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        scope: Optional[str] = None
    ) -> bool:
        """Store a memory in Azure Blob Storage with resilience."""
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
            
            # Store memory as blob
            blob_name = self._get_blob_name(memory_id)
            blob_client = self._container_client.get_blob_client(blob_name)
            
            blob_client.upload_blob(
                data=json.dumps(memory_data),
                overwrite=True,
                blob_type="BlockBlob"
            )
            
            # Store metadata separately for easier querying
            metadata_blob_name = self._get_metadata_blob_name(memory_id)
            metadata_blob_client = self._container_client.get_blob_client(metadata_blob_name)
            
            metadata_info = {
                'memory_id': memory_id,
                'scope': scope or 'default',
                'created_at': memory_data['created_at'],
                'updated_at': memory_data['updated_at'],
                'content_size': len(content.encode('utf-8')),
                'has_metadata': bool(metadata)
            }
            
            metadata_blob_client.upload_blob(
                data=json.dumps(metadata_info),
                overwrite=True,
                blob_type="BlockBlob"
            )
            
            # Add to audit log
            audit_entry = {
                'memory_id': memory_id,
                'action': 'store',
                'timestamp': time.time(),
                'scope': scope or 'default',
                'blob_name': blob_name
            }
            
            audit_blob_name = self._get_blob_name(f"audit_{memory_id}_{uuid.uuid4()}", "audit")
            audit_blob_client = self._container_client.get_blob_client(audit_blob_name)
            
            try:
                audit_blob_client.upload_blob(
                    data=json.dumps(audit_entry),
                    overwrite=True,
                    blob_type="BlockBlob"
                )
            except Exception as audit_error:
                logger.warning(f"Failed to create audit entry: {audit_error}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to store memory {memory_id}: {e}")
            return False

    def retrieve_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a memory from Azure Blob Storage with resilience."""
        try:
            self._ensure_connection()
            
            blob_name = self._get_blob_name(memory_id)
            blob_client = self._container_client.get_blob_client(blob_name)
            
            try:
                blob_data = blob_client.download_blob()
                content = blob_data.readall()
                memory_data = json.loads(content.decode('utf-8'))
                
                if memory_data.get('memory_type') == 'conversation_memory':
                    return memory_data
            except ResourceNotFoundError:
                return None
            
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve memory {memory_id}: {e}")
            return None

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory from Azure Blob Storage with resilience."""
        try:
            self._ensure_connection()
            
            # Get memory data first for audit log
            memory_data = self.retrieve_memory(memory_id)
            if not memory_data:
                return False
            
            scope = memory_data.get('scope', 'default')
            
            # Delete the memory blob
            blob_name = self._get_blob_name(memory_id)
            blob_client = self._container_client.get_blob_client(blob_name)
            blob_client.delete_blob()
            
            # Delete the metadata blob
            metadata_blob_name = self._get_metadata_blob_name(memory_id)
            metadata_blob_client = self._container_client.get_blob_client(metadata_blob_name)
            try:
                metadata_blob_client.delete_blob()
            except ResourceNotFoundError:
                pass  # Metadata blob might not exist
            
            # Add to audit log
            audit_entry = {
                'memory_id': memory_id,
                'action': 'delete',
                'timestamp': time.time(),
                'scope': scope,
                'blob_name': blob_name
            }
            
            audit_blob_name = self._get_blob_name(f"audit_{memory_id}_{uuid.uuid4()}", "audit")
            audit_blob_client = self._container_client.get_blob_client(audit_blob_name)
            
            try:
                audit_blob_client.upload_blob(
                    data=json.dumps(audit_entry),
                    overwrite=True,
                    blob_type="BlockBlob"
                )
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
        """List memory IDs from Azure Blob Storage with resilience."""
        try:
            self._ensure_connection()
            
            memory_ids = []
            
            # List metadata blobs to get memory info efficiently
            metadata_prefix = f"{self.config.blob_prefix}/metadata/"
            
            for blob in self._container_client.list_blobs(name_starts_with=metadata_prefix):
                if limit and len(memory_ids) >= limit:
                    break
                
                try:
                    # Download metadata blob to check scope
                    blob_client = self._container_client.get_blob_client(blob.name)
                    blob_data = blob_client.download_blob()
                    content = blob_data.readall()
                    metadata_info = json.loads(content.decode('utf-8'))
                    
                    if scope is None or metadata_info.get('scope') == scope:
                        memory_ids.append(metadata_info['memory_id'])
                
                except Exception as e:
                    logger.warning(f"Failed to process metadata blob {blob.name}: {e}")
                    continue
            
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
        """Search memories by content in Azure Blob Storage with resilience."""
        try:
            self._ensure_connection()
            
            matching_ids = []
            query_lower = query.lower()
            
            # List memory blobs and search content
            memory_prefix = f"{self.config.blob_prefix}/memory/"
            
            for blob in self._container_client.list_blobs(name_starts_with=memory_prefix):
                if limit and len(matching_ids) >= limit:
                    break
                
                try:
                    # Download blob to search content
                    blob_client = self._container_client.get_blob_client(blob.name)
                    blob_data = blob_client.download_blob()
                    content = blob_data.readall()
                    memory_data = json.loads(content.decode('utf-8'))
                    
                    # Check scope filter
                    if scope and memory_data.get('scope') != scope:
                        continue
                    
                    # Search in content
                    if query_lower in memory_data.get('content', '').lower():
                        matching_ids.append(memory_data['id'])
                
                except Exception as e:
                    logger.warning(f"Failed to search blob {blob.name}: {e}")
                    continue
            
            return matching_ids
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []

    def get_audit_log(
        self,
        memory_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get audit log entries from Azure Blob Storage with resilience."""
        try:
            self._ensure_connection()
            
            audit_entries = []
            
            # List audit blobs
            audit_prefix = f"{self.config.blob_prefix}/audit/"
            
            for blob in self._container_client.list_blobs(name_starts_with=audit_prefix):
                if limit and len(audit_entries) >= limit:
                    break
                
                try:
                    # Download audit blob
                    blob_client = self._container_client.get_blob_client(blob.name)
                    blob_data = blob_client.download_blob()
                    content = blob_data.readall()
                    audit_entry = json.loads(content.decode('utf-8'))
                    
                    # Filter by memory_id if specified
                    if memory_id is None or audit_entry.get('memory_id') == memory_id:
                        audit_entry['blob_name'] = blob.name
                        audit_entry['blob_created'] = blob.creation_time.isoformat() if blob.creation_time else None
                        audit_entries.append(audit_entry)
                
                except Exception as e:
                    logger.warning(f"Failed to process audit blob {blob.name}: {e}")
                    continue
            
            # Sort by timestamp (newest first)
            audit_entries.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
            
            return audit_entries[:limit] if limit else audit_entries
        except Exception as e:
            logger.error(f"Failed to get audit log: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics from Azure Blob Storage with resilience."""
        try:
            self._ensure_connection()
            
            total_memories = 0
            total_size = 0
            scopes = set()
            audit_count = 0
            
            # Count blobs by prefix
            for blob in self._container_client.list_blobs():
                if blob.name.startswith(f"{self.config.blob_prefix}/memory/"):
                    total_memories += 1
                    total_size += blob.size or 0
                elif blob.name.startswith(f"{self.config.blob_prefix}/audit/"):
                    audit_count += 1
            
            # Get scopes from metadata blobs (more efficient)
            metadata_prefix = f"{self.config.blob_prefix}/metadata/"
            for blob in self._container_client.list_blobs(name_starts_with=metadata_prefix):
                try:
                    blob_client = self._container_client.get_blob_client(blob.name)
                    blob_data = blob_client.download_blob()
                    content = blob_data.readall()
                    metadata_info = json.loads(content.decode('utf-8'))
                    scopes.add(metadata_info.get('scope', 'default'))
                except Exception:
                    continue
            
            return {
                'total_memories': total_memories,
                'total_scopes': len(scopes),
                'audit_entries': audit_count,
                'total_size_bytes': total_size,
                'storage_type': 'azure_blob'
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                'total_memories': 0,
                'total_scopes': 0,
                'audit_entries': 0,
                'total_size_bytes': 0,
                'storage_type': 'azure_blob',
                'error': str(e)
            }

    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status of Azure Blob Storage connection."""
        try:
            self._ensure_connection()
            return AzureBlobHealthCheck.sync_health_check(self._container_client)
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "error_type": type(e).__name__
            }

    def ping(self) -> bool:
        """Test Azure Blob Storage connection with auto-reconnection."""
        try:
            health = self.get_health_status()
            return health.get("status") == "healthy"
        except Exception as e:
            logger.warning(f"Ping failed: {e}")
            return False

    def close(self) -> None:
        """Close Azure Blob Storage connection."""
        if self._service_client:
            try:
                self._service_client.close()
            except Exception as e:
                logger.warning(f"Error closing Blob service client: {e}")
            finally:
                self._service_client = None
                self._container_client = None