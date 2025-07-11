"""
Azure Cache for Redis storage implementation.
Provides both sync and async storage adapters with enterprise features.
"""

import json
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import redis
    import redis.asyncio as redis_async
except ImportError:
    redis = None
    redis_async = None

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

from ..config.storage import AzureRedisConfig, AzureAuthMethod
from ..memory_scope import MemoryScope
from .base import AsyncStorageAdapter, StorageAdapter


class AzureRedisConnectionError(Exception):
    """Raised when Azure Redis connection fails."""
    pass


class AzureRedisCollections:
    """Manages Redis data structures for efficient storage."""

    def __init__(self, client: Union[redis.Redis, redis_async.Redis], prefix: str = "nexamem"):
        self.client = client
        self.prefix = prefix
        self.is_async = hasattr(client, 'pipeline') and hasattr(client.pipeline(), '__aenter__')

    async def add_message_to_channel_async(
        self,
        scope: MemoryScope,
        channel: str,
        message_data: Dict[str, Any],
        ttl_sec: int
    ) -> str:
        """Add message using Redis collections (async)."""
        message_uuid = str(uuid.uuid4())
        timestamp = int(time.time())

        # Collection names
        messages_hash = f"{self.prefix}:messages:{scope.env}:{scope.agent_id}"
        channel_index = f"{self.prefix}:index:{scope.env}:{scope.agent_id}:{scope.user_id}:{scope.session_id}:{channel}"

        # Store message in hash (more efficient than individual keys)
        message_key = f"{scope.user_id}:{scope.session_id}:{channel}:{message_uuid}"

        # Use pipeline for atomic operations
        pipe = self.client.pipeline()

        # Store message in hash
        await pipe.hset(messages_hash, message_key, json.dumps({
            **message_data,
            "uuid": message_uuid,
            "timestamp": timestamp
        }))
        await pipe.expire(messages_hash, ttl_sec)

        # Add to sorted set index for efficient range queries
        await pipe.zadd(channel_index, {message_uuid: timestamp})
        await pipe.expire(channel_index, ttl_sec)

        await pipe.execute()
        return message_uuid

    def add_message_to_channel_sync(
        self,
        scope: MemoryScope,
        channel: str,
        message_data: Dict[str, Any],
        ttl_sec: int
    ) -> str:
        """Add message using Redis collections (sync)."""
        message_uuid = str(uuid.uuid4())
        timestamp = int(time.time())

        # Collection names
        messages_hash = f"{self.prefix}:messages:{scope.env}:{scope.agent_id}"
        channel_index = f"{self.prefix}:index:{scope.env}:{scope.agent_id}:{scope.user_id}:{scope.session_id}:{channel}"

        # Store message in hash
        message_key = f"{scope.user_id}:{scope.session_id}:{channel}:{message_uuid}"

        # Use pipeline for atomic operations
        pipe = self.client.pipeline()

        # Store message in hash
        pipe.hset(messages_hash, message_key, json.dumps({
            **message_data,
            "uuid": message_uuid,
            "timestamp": timestamp
        }))
        pipe.expire(messages_hash, ttl_sec)

        # Add to sorted set index for efficient range queries
        pipe.zadd(channel_index, {message_uuid: timestamp})
        pipe.expire(channel_index, ttl_sec)

        pipe.execute()
        return message_uuid

    async def get_messages_from_channel_async(
        self,
        scope: MemoryScope,
        channel: str,
        since_sec: Optional[int] = None,
        max_msgs: Optional[int] = None,
        max_bytes: Optional[int] = None
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Efficiently retrieve messages using sorted sets and hashes (async)."""
        messages_hash = f"{self.prefix}:messages:{scope.env}:{scope.agent_id}"
        channel_index = f"{self.prefix}:index:{scope.env}:{scope.agent_id}:{scope.user_id}:{scope.session_id}:{channel}"

        # Get message UUIDs from sorted set (time-ordered)
        max_score = int(time.time())
        min_score = max_score - since_sec if since_sec else 0

        message_uuids = await self.client.zrevrangebyscore(
            channel_index,
            max_score,
            min_score,
            start=0,
            num=max_msgs or -1
        )

        if not message_uuids:
            return [], {"total_messages": 0, "total_bytes": 0, "truncated": False}

        # Bulk fetch messages from hash
        message_keys = [
            f"{scope.user_id}:{scope.session_id}:{channel}:{uuid_str}"
            for uuid_str in message_uuids
        ]

        messages_data = await self.client.hmget(messages_hash, message_keys)

        # Process and filter messages
        messages = []
        total_bytes = 0
        retrieved_count = 0

        for message_data in messages_data:
            if message_data is None:
                continue

            try:
                message = json.loads(message_data)
                content = message["content"]

                content_bytes = len(content.encode('utf-8'))
                if max_bytes and (total_bytes + content_bytes) > max_bytes:
                    break

                messages.append(content)
                total_bytes += content_bytes
                retrieved_count += 1

            except (json.JSONDecodeError, KeyError):
                continue

        return messages, {
            "total_messages": retrieved_count,
            "total_bytes": total_bytes,
            "truncated": len(message_uuids) > retrieved_count
        }

    def get_messages_from_channel_sync(
        self,
        scope: MemoryScope,
        channel: str,
        since_sec: Optional[int] = None,
        max_msgs: Optional[int] = None,
        max_bytes: Optional[int] = None
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Efficiently retrieve messages using sorted sets and hashes (sync)."""
        messages_hash = f"{self.prefix}:messages:{scope.env}:{scope.agent_id}"
        channel_index = f"{self.prefix}:index:{scope.env}:{scope.agent_id}:{scope.user_id}:{scope.session_id}:{channel}"

        # Get message UUIDs from sorted set (time-ordered)
        max_score = int(time.time())
        min_score = max_score - since_sec if since_sec else 0

        message_uuids = self.client.zrevrangebyscore(
            channel_index,
            max_score,
            min_score,
            start=0,
            num=max_msgs or -1
        )

        if not message_uuids:
            return [], {"total_messages": 0, "total_bytes": 0, "truncated": False}

        # Bulk fetch messages from hash
        message_keys = [
            f"{scope.user_id}:{scope.session_id}:{channel}:{uuid_str}"
            for uuid_str in message_uuids
        ]

        messages_data = self.client.hmget(messages_hash, message_keys)

        # Process and filter messages
        messages = []
        total_bytes = 0
        retrieved_count = 0

        for message_data in messages_data:
            if message_data is None:
                continue

            try:
                message = json.loads(message_data)
                content = message["content"]

                content_bytes = len(content.encode('utf-8'))
                if max_bytes and (total_bytes + content_bytes) > max_bytes:
                    break

                messages.append(content)
                total_bytes += content_bytes
                retrieved_count += 1

            except (json.JSONDecodeError, KeyError):
                continue

        return messages, {
            "total_messages": retrieved_count,
            "total_bytes": total_bytes,
            "truncated": len(message_uuids) > retrieved_count
        }


class AsyncAzureRedisStorage(AsyncStorageAdapter):
    """Async Azure Cache for Redis storage adapter."""

    def __init__(self, config: AzureRedisConfig):
        self.config = config
        self._client: Optional[redis_async.Redis] = None
        self._collections: Optional[AzureRedisCollections] = None
        self._connection_pool: Optional[redis_async.ConnectionPool] = None

    async def _get_auth_token(self) -> str:
        """Get authentication token based on configured method."""
        if self.config.auth_method == AzureAuthMethod.ACCESS_KEY:
            if not self.config.access_key:
                raise AzureRedisConnectionError("Access key required for ACCESS_KEY auth method")
            return self.config.access_key

        elif self.config.auth_method == AzureAuthMethod.ENTRA_ID:
            if not AsyncDefaultAzureCredential:
                raise ImportError("azure-identity package required for Entra ID auth")

            # Use Azure Identity for token
            credential = AsyncDefaultAzureCredential()
            token = await credential.get_token("https://redis.azure.com/.default")
            return token.token

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
            raise AzureRedisConnectionError(f"Unsupported auth method: {self.config.auth_method}")

    async def connect(self) -> None:
        """Establish connection to Azure Cache for Redis."""
        if self._client:
            return

        if not redis_async:
            raise ImportError("redis[asyncio] package required for async operations")

        try:
            # Get authentication token
            password = await self._get_auth_token()

            # Create connection pool for better performance
            self._connection_pool = redis_async.ConnectionPool(
                host=self.config.hostname,
                port=self.config.port,
                password=password,
                ssl=self.config.ssl,
                db=self.config.db,
                max_connections=self.config.max_connections,
                retry_on_timeout=self.config.retry_on_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                socket_timeout=self.config.socket_timeout,
                decode_responses=True
            )

            self._client = redis_async.Redis(connection_pool=self._connection_pool)
            self._collections = AzureRedisCollections(
                self._client,
                self.config.collection_prefix
            )

            # Test connection
            await self._client.ping()

        except Exception as e:
            raise AzureRedisConnectionError(f"Failed to connect to Azure Redis: {e}") from e

    async def write_message(
        self,
        scope: MemoryScope,
        channel: str,
        content: Union[str, bytes],
        ttl_sec: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Write message using Azure Redis collections."""
        await self.connect()

        message_data = {
            "content": content if isinstance(content, str) else content.decode('utf-8', errors='ignore'),
            "metadata": metadata or {}
        }

        if self.config.use_collections:
            return await self._collections.add_message_to_channel_async(
                scope, channel, message_data, ttl_sec
            )
        else:
            # Fallback to individual keys (legacy compatibility)
            return await self._write_message_legacy(scope, channel, message_data, ttl_sec)

    async def read_messages(
        self,
        scope: MemoryScope,
        channel: str,
        *,
        since_sec: Optional[int] = None,
        max_msgs: Optional[int] = None,
        max_bytes: Optional[int] = None
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Read messages using Azure Redis collections."""
        await self.connect()

        if self.config.use_collections:
            return await self._collections.get_messages_from_channel_async(
                scope, channel, since_sec, max_msgs, max_bytes
            )
        else:
            # Fallback to legacy key pattern
            return await self._read_messages_legacy(scope, channel, since_sec, max_msgs, max_bytes)

    async def _write_message_legacy(
        self,
        scope: MemoryScope,
        channel: str,
        message_data: Dict[str, Any],
        ttl_sec: int
    ) -> str:
        """Legacy write using individual keys."""
        message_uuid = str(uuid.uuid4())
        timestamp = int(time.time())

        message = {
            **message_data,
            "uuid": message_uuid,
            "timestamp": timestamp
        }

        # Store message
        message_key = f"{scope.get_key_prefix(channel)}:{message_uuid}"
        await self._client.setex(message_key, ttl_sec, json.dumps(message))

        # Update sorted set index
        index_key = scope.get_index_key(channel)
        await self._client.zadd(index_key, {message_uuid: timestamp})
        await self._client.expire(index_key, ttl_sec)

        return message_uuid

    async def _read_messages_legacy(
        self,
        scope: MemoryScope,
        channel: str,
        since_sec: Optional[int] = None,
        max_msgs: Optional[int] = None,
        max_bytes: Optional[int] = None
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Legacy read using individual keys."""
        index_key = scope.get_index_key(channel)

        # Calculate time range
        max_score = int(time.time())
        min_score = max_score - since_sec if since_sec else 0

        # Get message UUIDs from sorted set (newest first)
        message_uuids = await self._client.zrevrangebyscore(
            index_key,
            max_score,
            min_score,
            start=0,
            num=max_msgs or -1
        )

        messages = []
        total_bytes = 0
        retrieved_count = 0

        for message_uuid in message_uuids:
            message_key = f"{scope.get_key_prefix(channel)}:{message_uuid}"
            message_data = await self._client.get(message_key)

            if message_data is None:
                # Message expired, remove from index
                await self._client.zrem(index_key, message_uuid)
                continue

            try:
                message = json.loads(message_data)
                content = message["content"]

                # Check byte limit
                content_bytes = len(content.encode('utf-8'))
                if max_bytes and (total_bytes + content_bytes) > max_bytes:
                    break

                messages.append(content)
                total_bytes += content_bytes
                retrieved_count += 1

            except (json.JSONDecodeError, KeyError):
                # Invalid message, remove from index
                await self._client.zrem(index_key, message_uuid)
                continue

        metadata = {
            "total_messages": retrieved_count,
            "total_bytes": total_bytes,
            "truncated": len(message_uuids) > retrieved_count
        }

        return messages, metadata

    async def bulk_erase(self, scope: MemoryScope) -> int:
        """Erase all messages for a scope across all channels."""
        await self.connect()

        if self.config.use_collections:
            # Erase from collections
            pattern = f"{self.config.collection_prefix}:*:{scope.env}:{scope.agent_id}*{scope.user_id}*{scope.session_id}*"
        else:
            # Legacy pattern
            pattern = f"{scope.env}:{scope.agent_id}:{scope.user_id}:{scope.session_id}:*"

        keys = await self._client.keys(pattern)

        if keys:
            return await self._client.delete(*keys)
        return 0

    async def count_bytes(self, scope: MemoryScope, channel: str) -> int:
        """Count total bytes for a scope and channel."""
        await self.connect()

        if self.config.use_collections:
            # Count from collections
            messages_hash = f"{self.config.collection_prefix}:messages:{scope.env}:{scope.agent_id}"
            pattern = f"{scope.user_id}:{scope.session_id}:{channel}:*"

            # Get all matching message keys
            all_fields = await self._client.hkeys(messages_hash)
            matching_fields = [f for f in all_fields if f.startswith(f"{scope.user_id}:{scope.session_id}:{channel}:")]

            if not matching_fields:
                return 0

            # Get messages
            messages_data = await self._client.hmget(messages_hash, matching_fields)
            total_bytes = 0

            for message_data in messages_data:
                if message_data:
                    try:
                        message = json.loads(message_data)
                        content = message["content"]
                        total_bytes += len(content.encode('utf-8'))
                    except (json.JSONDecodeError, KeyError):
                        continue

            return total_bytes
        else:
            # Legacy count
            index_key = scope.get_index_key(channel)
            message_uuids = await self._client.zrange(index_key, 0, -1)

            total_bytes = 0
            for message_uuid in message_uuids:
                message_key = f"{scope.get_key_prefix(channel)}:{message_uuid}"
                message_data = await self._client.get(message_key)

                if message_data is None:
                    # Message expired, remove from index
                    await self._client.zrem(index_key, message_uuid)
                    continue

                try:
                    message = json.loads(message_data)
                    content = message["content"]
                    total_bytes += len(content.encode('utf-8'))
                except (json.JSONDecodeError, KeyError):
                    # Invalid message, remove from index
                    await self._client.zrem(index_key, message_uuid)
                    continue

            return total_bytes

    async def checkpoint_set(self, scope: MemoryScope, key: str, payload: dict) -> None:
        """Set a checkpoint value."""
        await self.connect()
        checkpoint_key = f"{scope.env}:{scope.agent_id}:checkpoint:{key}"
        await self._client.set(checkpoint_key, json.dumps(payload))

    async def checkpoint_get(self, scope: MemoryScope, key: str) -> Optional[dict]:
        """Get a checkpoint value."""
        await self.connect()
        checkpoint_key = f"{scope.env}:{scope.agent_id}:checkpoint:{key}"
        data = await self._client.get(checkpoint_key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return None
        return None

    async def ping(self) -> bool:
        """Test Azure Redis connection."""
        try:
            if not self._client:
                await self.connect()
            return await self._client.ping()
        except Exception:
            return False

    async def close(self) -> None:
        """Close Azure Redis connection."""
        if self._client:
            await self._client.close()
        if self._connection_pool:
            await self._connection_pool.disconnect()


class AzureRedisStorage(StorageAdapter):
    """Sync Azure Cache for Redis storage adapter."""

    def __init__(self, config: AzureRedisConfig):
        self.config = config
        self._client: Optional[redis.Redis] = None
        self._collections: Optional[AzureRedisCollections] = None

    def _get_auth_token(self) -> str:
        """Get authentication token based on configured method."""
        if self.config.auth_method == AzureAuthMethod.ACCESS_KEY:
            if not self.config.access_key:
                raise AzureRedisConnectionError("Access key required for ACCESS_KEY auth method")
            return self.config.access_key

        elif self.config.auth_method == AzureAuthMethod.ENTRA_ID:
            if not DefaultAzureCredential:
                raise ImportError("azure-identity package required for Entra ID auth")

            # Use Azure Identity for token
            credential = DefaultAzureCredential()
            token = credential.get_token("https://redis.azure.com/.default")
            return token.token

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
            raise AzureRedisConnectionError(f"Unsupported auth method: {self.config.auth_method}")

    def connect(self) -> None:
        """Establish connection to Azure Cache for Redis."""
        if self._client:
            return

        if not redis:
            raise ImportError("redis package required for sync operations")

        try:
            # Get authentication token
            password = self._get_auth_token()

            # Create Redis client
            self._client = redis.Redis(
                host=self.config.hostname,
                port=self.config.port,
                password=password,
                ssl=self.config.ssl,
                db=self.config.db,
                socket_connect_timeout=self.config.socket_connect_timeout,
                socket_timeout=self.config.socket_timeout,
                decode_responses=True
            )

            self._collections = AzureRedisCollections(
                self._client,
                self.config.collection_prefix
            )

            # Test connection
            self._client.ping()

        except Exception as e:
            raise AzureRedisConnectionError(f"Failed to connect to Azure Redis: {e}") from e

    def write_message(
        self,
        scope: MemoryScope,
        channel: str,
        content: Union[str, bytes],
        ttl_sec: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Write message using Azure Redis collections."""
        self.connect()

        message_data = {
            "content": content if isinstance(content, str) else content.decode('utf-8', errors='ignore'),
            "metadata": metadata or {}
        }

        if self.config.use_collections:
            return self._collections.add_message_to_channel_sync(
                scope, channel, message_data, ttl_sec
            )
        else:
            # Fallback to individual keys (legacy compatibility)
            return self._write_message_legacy(scope, channel, message_data, ttl_sec)

    def read_messages(
        self,
        scope: MemoryScope,
        channel: str,
        *,
        since_sec: Optional[int] = None,
        max_msgs: Optional[int] = None,
        max_bytes: Optional[int] = None
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Read messages using Azure Redis collections."""
        self.connect()

        if self.config.use_collections:
            return self._collections.get_messages_from_channel_sync(
                scope, channel, since_sec, max_msgs, max_bytes
            )
        else:
            # Fallback to legacy key pattern
            return self._read_messages_legacy(scope, channel, since_sec, max_msgs, max_bytes)

    def _write_message_legacy(
        self,
        scope: MemoryScope,
        channel: str,
        message_data: Dict[str, Any],
        ttl_sec: int
    ) -> str:
        """Legacy write using individual keys."""
        message_uuid = str(uuid.uuid4())
        timestamp = int(time.time())

        message = {
            **message_data,
            "uuid": message_uuid,
            "timestamp": timestamp
        }

        # Store message
        message_key = f"{scope.get_key_prefix(channel)}:{message_uuid}"
        self._client.setex(message_key, ttl_sec, json.dumps(message))

        # Update sorted set index
        index_key = scope.get_index_key(channel)
        self._client.zadd(index_key, {message_uuid: timestamp})
        self._client.expire(index_key, ttl_sec)

        return message_uuid

    def _read_messages_legacy(
        self,
        scope: MemoryScope,
        channel: str,
        since_sec: Optional[int] = None,
        max_msgs: Optional[int] = None,
        max_bytes: Optional[int] = None
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Legacy read using individual keys."""
        index_key = scope.get_index_key(channel)

        # Calculate time range
        max_score = int(time.time())
        min_score = max_score - since_sec if since_sec else 0

        # Get message UUIDs from sorted set (newest first)
        message_uuids = self._client.zrevrangebyscore(
            index_key,
            max_score,
            min_score,
            start=0,
            num=max_msgs or -1
        )

        messages = []
        total_bytes = 0
        retrieved_count = 0

        for message_uuid in message_uuids:
            message_key = f"{scope.get_key_prefix(channel)}:{message_uuid}"
            message_data = self._client.get(message_key)

            if message_data is None:
                # Message expired, remove from index
                self._client.zrem(index_key, message_uuid)
                continue

            try:
                message = json.loads(message_data)
                content = message["content"]

                # Check byte limit
                content_bytes = len(content.encode('utf-8'))
                if max_bytes and (total_bytes + content_bytes) > max_bytes:
                    break

                messages.append(content)
                total_bytes += content_bytes
                retrieved_count += 1

            except (json.JSONDecodeError, KeyError):
                # Invalid message, remove from index
                self._client.zrem(index_key, message_uuid)
                continue

        metadata = {
            "total_messages": retrieved_count,
            "total_bytes": total_bytes,
            "truncated": len(message_uuids) > retrieved_count
        }

        return messages, metadata

    def bulk_erase(self, scope: MemoryScope) -> int:
        """Erase all messages for a scope across all channels."""
        self.connect()

        if self.config.use_collections:
            # Erase from collections
            pattern = f"{self.config.collection_prefix}:*:{scope.env}:{scope.agent_id}*{scope.user_id}*{scope.session_id}*"
        else:
            # Legacy pattern
            pattern = f"{scope.env}:{scope.agent_id}:{scope.user_id}:{scope.session_id}:*"

        keys = self._client.keys(pattern)

        if keys:
            return self._client.delete(*keys)
        return 0

    def count_bytes(self, scope: MemoryScope, channel: str) -> int:
        """Count total bytes for a scope and channel."""
        self.connect()

        if self.config.use_collections:
            # Count from collections
            messages_hash = f"{self.config.collection_prefix}:messages:{scope.env}:{scope.agent_id}"
            pattern = f"{scope.user_id}:{scope.session_id}:{channel}:*"

            # Get all matching message keys
            all_fields = self._client.hkeys(messages_hash)
            matching_fields = [f for f in all_fields if f.startswith(f"{scope.user_id}:{scope.session_id}:{channel}:")]

            if not matching_fields:
                return 0

            # Get messages
            messages_data = self._client.hmget(messages_hash, matching_fields)
            total_bytes = 0

            for message_data in messages_data:
                if message_data:
                    try:
                        message = json.loads(message_data)
                        content = message["content"]
                        total_bytes += len(content.encode('utf-8'))
                    except (json.JSONDecodeError, KeyError):
                        continue

            return total_bytes
        else:
            # Legacy count
            index_key = scope.get_index_key(channel)
            message_uuids = self._client.zrange(index_key, 0, -1)

            total_bytes = 0
            for message_uuid in message_uuids:
                message_key = f"{scope.get_key_prefix(channel)}:{message_uuid}"
                message_data = self._client.get(message_key)

                if message_data is None:
                    # Message expired, remove from index
                    self._client.zrem(index_key, message_uuid)
                    continue

                try:
                    message = json.loads(message_data)
                    content = message["content"]
                    total_bytes += len(content.encode('utf-8'))
                except (json.JSONDecodeError, KeyError):
                    # Invalid message, remove from index
                    self._client.zrem(index_key, message_uuid)
                    continue

            return total_bytes

    def checkpoint_set(self, scope: MemoryScope, key: str, payload: dict) -> None:
        """Set a checkpoint value."""
        self.connect()
        checkpoint_key = f"{scope.env}:{scope.agent_id}:checkpoint:{key}"
        self._client.set(checkpoint_key, json.dumps(payload))

    def checkpoint_get(self, scope: MemoryScope, key: str) -> Optional[dict]:
        """Get a checkpoint value."""
        self.connect()
        checkpoint_key = f"{scope.env}:{scope.agent_id}:checkpoint:{key}"
        data = self._client.get(checkpoint_key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return None
        return None

    def ping(self) -> bool:
        """Test Azure Redis connection."""
        try:
            if not self._client:
                self.connect()
            return self._client.ping()
        except Exception:
            return False

    def close(self) -> None:
        """Close Azure Redis connection."""
        if self._client:
            self._client.close()
