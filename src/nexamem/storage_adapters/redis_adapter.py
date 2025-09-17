"""
Redis storage adapter implementation.
Implements the IStorageAdapter interface for Redis storage.
"""

import json
import time
import logging
from typing import List, Optional, Dict, Any, Union, TYPE_CHECKING

try:
    import redis
    import redis.asyncio as redis_async
    from redis.exceptions import RedisError, ConnectionError, TimeoutError
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    redis_async = None
    RedisError = Exception
    ConnectionError = Exception
    TimeoutError = Exception
    REDIS_AVAILABLE = False

# Type checking imports
if TYPE_CHECKING:
    from redis import Redis
    from redis.asyncio import Redis as AsyncRedis
else:
    Redis = Any
    AsyncRedis = Any

from nexamem.schemas.memory_filter import MemoryFilter
from nexamem.schemas.memory_scope import MemoryScope
from nexamem.schemas.memory_entry import MemoryEntry
from nexamem.storage_adapters.configs.redis_adapter_config import RedisAdapterConfig

logger = logging.getLogger(__name__)


class RedisAdapterError(Exception):
    """Base exception for Redis adapter errors."""
    pass


class RedisConnectionError(RedisAdapterError):
    """Raised when Redis connection fails."""
    pass


class RedisAdapter:
    """
    Redis storage adapter implementing IStorageAdapter interface.
    
    Key Design:
    - Keys follow pattern: {env}:{agent_id}:{user_id}:{session_id}:{channel}:{uuid}
    - Values are JSON-serialized MemoryEntry objects
    - TTL is applied at the key level
    - Supports pattern-based querying for filtering
    """

    def __init__(self, config: RedisAdapterConfig):
        """
        Initialize the Redis storage adapter.

        Args:
            config: Redis adapter configuration
        """
        if not REDIS_AVAILABLE:
            raise RedisAdapterError(
                "Redis package is not installed. Install with: pip install redis"
            )

        self.config = config
        self._client: Optional["Redis"] = None
        self._async_client: Optional["AsyncRedis"] = None
        self.key_prefix = "nexamem"

    @property
    def client(self) -> "Redis":
        """Get or create synchronous Redis client."""
        if self._client is None:
            try:
                kwargs = self.config.to_redis_kwargs()
                if redis is not None:
                    self._client = redis.Redis(**kwargs)
                    # Test connection
                    self._client.ping()
                    logger.info(f"Connected to Redis at {self.config.host}:{self.config.port}")
                else:
                    raise RedisAdapterError("Redis package not available")
            except Exception as e:
                raise RedisConnectionError(f"Failed to connect to Redis: {e}")
        return self._client

    @property
    def async_client(self) -> "AsyncRedis":
        """Get or create asynchronous Redis client."""
        if self._async_client is None:
            try:
                kwargs = self.config.to_redis_kwargs()
                if redis_async is not None:
                    self._async_client = redis_async.Redis(**kwargs)
                    logger.info(f"Created async Redis client for {self.config.host}:{self.config.port}")
                else:
                    raise RedisAdapterError("Redis async package not available")
            except Exception as e:
                raise RedisConnectionError(f"Failed to create async Redis client: {e}")
        return self._async_client

    def _build_key(self, entry: MemoryEntry) -> str:
        """
        Build Redis key from MemoryEntry.

        Format: {prefix}:{env}:{agent_id}:{user_id}:{session_id}:{channel}:{id}
        """
        scope = entry.metadata
        return f"{self.key_prefix}:{scope.env}:{scope.agent_id}:{scope.user_id}:{scope.session_id}:{entry.channel_name}:{entry.id}"

    def _parse_key(self, key: str) -> Optional[Dict[str, str]]:
        """
        Parse Redis key to extract components.

        Returns:
            Dictionary with key components or None if invalid format
        """
        try:
            parts = key.split(":")
            if len(parts) < 7 or parts[0] != self.key_prefix:
                return None
            
            return {
                "env": parts[1],
                "agent_id": parts[2],
                "user_id": parts[3],
                "session_id": parts[4],
                "channel": parts[5],
                "id": parts[6]
            }
        except (IndexError, ValueError):
            return None

    def _serialize_entry(self, entry: MemoryEntry) -> str:
        """Serialize MemoryEntry to JSON string."""
        try:
            # Convert to dict and handle special types
            entry_dict = entry.model_dump()
            entry_dict["metadata"] = entry.metadata.model_dump()
            return json.dumps(entry_dict)
        except Exception as e:
            raise RedisAdapterError(f"Failed to serialize entry: {e}")

    def _deserialize_entry(self, data: str) -> MemoryEntry:
        """Deserialize JSON string to MemoryEntry."""
        try:
            entry_dict = json.loads(data)
            # Reconstruct MemoryScope
            entry_dict["metadata"] = MemoryScope(**entry_dict["metadata"])
            return MemoryEntry(**entry_dict)
        except Exception as e:
            raise RedisAdapterError(f"Failed to deserialize entry: {e}")

    def _build_filter_pattern(self, filter_obj: MemoryFilter) -> str:
        """
        Build Redis key pattern for filtering.

        Args:
            filter_obj: Memory filter criteria

        Returns:
            Redis key pattern for SCAN command
        """
        # Build pattern: prefix:env:agent_id:user_id:session:channel:*
        # Use filter.session for session_id and filter.source for env/agent_id
        
        # For now, use wildcard matching - can be enhanced with more specific patterns
        if filter_obj.channel_names:
            # If specific channels, we'll need to scan multiple patterns
            # For simplicity, start with single pattern
            channel = filter_obj.channel_names[0] if len(filter_obj.channel_names) == 1 else "*"
        else:
            channel = "*"

        # Extract session info
        session = filter_obj.session or "*"
        
        # Build basic pattern - this can be enhanced based on filter requirements
        pattern = f"{self.key_prefix}:*:*:*:{session}:{channel}:*"
        
        return pattern

    async def write(self, entries: List[MemoryEntry]) -> None:
        """
        Write memory entries to Redis.

        Args:
            entries: List of memory entries to store
        """
        if not entries:
            return

        try:
            client = self.async_client
            pipe = client.pipeline()

            for entry in entries:
                key = self._build_key(entry)
                value = self._serialize_entry(entry)
                
                # Set the key-value pair
                pipe.set(key, value)
                
                # Apply TTL if specified
                if entry.ttl_override:
                    pipe.expire(key, entry.ttl_override)

            # Execute all commands in pipeline
            await pipe.execute()
            
            logger.debug(f"Successfully wrote {len(entries)} entries to Redis")

        except Exception as e:
            logger.error(f"Failed to write entries to Redis: {e}")
            raise RedisAdapterError(f"Write operation failed: {e}")

    async def read(self, filter_obj: MemoryFilter) -> List[MemoryEntry]:
        """
        Read memory entries from Redis based on filter.

        Args:
            filter_obj: Filter criteria for selecting entries

        Returns:
            List of matching memory entries
        """
        try:
            client = self.async_client
            pattern = self._build_filter_pattern(filter_obj)
            
            # Use SCAN to find matching keys
            entries = []
            cursor = 0
            
            while True:
                cursor, keys = await client.scan(
                    cursor=cursor,
                    match=pattern,
                    count=1000  # Batch size
                )
                
                if keys:
                    # Get values for all keys in batch
                    values = await client.mget(keys)
                    
                    for key, value in zip(keys, values):
                        if value:
                            try:
                                entry = self._deserialize_entry(value)
                                
                                # Apply additional filtering
                                if self._matches_filter(entry, filter_obj):
                                    entries.append(entry)
                                    
                            except Exception as e:
                                logger.warning(f"Failed to deserialize entry for key {key}: {e}")
                                continue
                
                if cursor == 0:  # Scan complete
                    break

            # Apply post-processing filters
            entries = self._apply_additional_filters(entries, filter_obj)
            
            # Sort by timestamp (newest first)
            entries.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Apply max_msgs limit
            if filter_obj.max_msgs:
                entries = entries[:filter_obj.max_msgs]

            logger.debug(f"Retrieved {len(entries)} entries from Redis")
            return entries

        except Exception as e:
            logger.error(f"Failed to read entries from Redis: {e}")
            raise RedisAdapterError(f"Read operation failed: {e}")

    def _matches_filter(self, entry: MemoryEntry, filter_obj: MemoryFilter) -> bool:
        """
        Check if entry matches filter criteria.

        Args:
            entry: Memory entry to check
            filter_obj: Filter criteria

        Returns:
            True if entry matches filter
        """
        # Check channel names
        if filter_obj.channel_names and entry.channel_name not in filter_obj.channel_names:
            return False

        # Check source
        if filter_obj.source and entry.source != filter_obj.source:
            return False

        # Check type
        if filter_obj.type and entry.type != filter_obj.type:
            return False

        # Check session (using metadata.session_id)
        if filter_obj.session and entry.metadata.session_id != filter_obj.session:
            return False

        return True

    def _apply_additional_filters(self, entries: List[MemoryEntry], filter_obj: MemoryFilter) -> List[MemoryEntry]:
        """
        Apply timestamp and other filters to entries.

        Args:
            entries: List of entries to filter
            filter_obj: Filter criteria

        Returns:
            Filtered list of entries
        """
        filtered_entries = []
        
        for entry in entries:
            # Check timestamp filters
            if filter_obj.starting_timestamp:
                start_ts = int(filter_obj.starting_timestamp.timestamp())
                if entry.timestamp < start_ts:
                    continue

            if filter_obj.ending_timestamp:
                end_ts = int(filter_obj.ending_timestamp.timestamp())
                if entry.timestamp > end_ts:
                    continue

            filtered_entries.append(entry)

        return filtered_entries

    async def delete(self, keys: List[str]) -> int:
        """
        Delete entries by keys.

        Args:
            keys: List of Redis keys to delete

        Returns:
            Number of keys deleted
        """
        if not keys:
            return 0

        try:
            client = self.async_client
            deleted_count = await client.delete(*keys)
            logger.debug(f"Deleted {deleted_count} keys from Redis")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete keys from Redis: {e}")
            raise RedisAdapterError(f"Delete operation failed: {e}")

    async def delete_by_filter(self, filter_obj: MemoryFilter) -> int:
        """
        Delete entries matching filter criteria.

        Args:
            filter_obj: Filter criteria for selecting entries to delete

        Returns:
            Number of entries deleted
        """
        try:
            # First, find matching keys
            client = self.async_client
            pattern = self._build_filter_pattern(filter_obj)
            
            keys_to_delete = []
            cursor = 0
            
            while True:
                cursor, keys = await client.scan(
                    cursor=cursor,
                    match=pattern,
                    count=1000
                )
                
                if keys:
                    # For more precise filtering, we could load and check each entry
                    # For now, use pattern matching
                    keys_to_delete.extend(keys)
                
                if cursor == 0:
                    break

            # Delete the keys
            if keys_to_delete:
                deleted_count = await self.delete(keys_to_delete)
                return deleted_count

            return 0

        except Exception as e:
            logger.error(f"Failed to delete by filter: {e}")
            raise RedisAdapterError(f"Delete by filter failed: {e}")

    async def health_check(self) -> bool:
        """
        Check Redis connection health.

        Returns:
            True if Redis is healthy, False otherwise
        """
        try:
            client = self.async_client
            result = await client.ping()
            return result == True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            return False

    async def close(self) -> None:
        """Close Redis connections."""
        try:
            if self._async_client:
                await self._async_client.close()
                self._async_client = None
            
            if self._client:
                self._client.close()
                self._client = None
                
            logger.debug("Redis connections closed")

        except Exception as e:
            logger.warning(f"Error closing Redis connections: {e}")

    def __del__(self):
        """Cleanup on object destruction."""
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass