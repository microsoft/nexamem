"""
Redis adapter for AIMemory with sync and async support.
"""
from typing import List, Dict, Optional, Tuple, Any, Union
import json
import time
import uuid

try:
    import redis
    import redis.asyncio as redis_async
except ImportError:
    redis = None
    redis_async = None

try:
    import fakeredis
except ImportError:
    fakeredis = None

from .memory_scope import MemoryScope


class RedisConnectionError(Exception):
    """Raised when Redis connection fails."""
    pass


class RedisAdapter:
    """Synchronous Redis adapter for AIMemory."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        ssl: bool = False,
        db: int = 0,
        use_fakeredis: bool = False,
        **kwargs
    ):
        self.host = host
        self.port = port
        self.password = password
        self.ssl = ssl
        self.db = db
        self.use_fakeredis = use_fakeredis
        
        if redis is None and not use_fakeredis:
            raise ImportError("redis package is required. Install with: pip install redis")
        
        if use_fakeredis:
            if fakeredis is None:
                raise ImportError("fakeredis package is required. Install with: pip install fakeredis")
            self.client = fakeredis.FakeRedis(decode_responses=True)
        else:
            self.client = redis.Redis(
                host=host,
                port=port,
                password=password,
                ssl=ssl,
                db=db,
                decode_responses=True,
                **kwargs
            )
        
        # Test connection
        try:
            self.client.ping()
        except Exception as e:
            raise RedisConnectionError(f"Failed to connect to Redis: {e}")
    
    def write_message(
        self,
        scope: MemoryScope,
        channel: str,
        content: Union[str, bytes],
        ttl_sec: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Write a message to Redis.
        
        Args:
            scope: Memory scope
            channel: Channel name
            content: Message content
            ttl_sec: Time-to-live in seconds
            metadata: Optional metadata
            
        Returns:
            Message UUID
        """
        message_uuid = str(uuid.uuid4())
        timestamp = int(time.time())
        
        # Create message object
        message = {
            "uuid": message_uuid,
            "timestamp": timestamp,
            "content": content if isinstance(content, str) else content.decode('utf-8', errors='ignore'),
            "metadata": metadata or {}
        }
        
        # Store message
        message_key = f"{scope.get_key_prefix(channel)}:{message_uuid}"
        self.client.setex(message_key, ttl_sec, json.dumps(message))
        
        # Update sorted set index
        index_key = scope.get_index_key(channel)
        self.client.zadd(index_key, {message_uuid: timestamp})
        self.client.expire(index_key, ttl_sec)
        
        return message_uuid
    
    def read_messages(
        self,
        scope: MemoryScope,
        channel: str,
        *,
        since_sec: Optional[int] = None,
        max_msgs: Optional[int] = None,
        max_bytes: Optional[int] = None
    ) -> Tuple[List[str], Dict[str, Any]]:
        """
        Read messages from Redis.
        
        Args:
            scope: Memory scope
            channel: Channel name
            since_sec: Only messages newer than this (seconds ago)
            max_msgs: Maximum number of messages
            max_bytes: Maximum total bytes
            
        Returns:
            Tuple of (messages, metadata)
        """
        index_key = scope.get_index_key(channel)
        
        # Calculate time range
        max_score = int(time.time())
        min_score = 0
        if since_sec is not None:
            min_score = max_score - since_sec
        
        # Get message UUIDs from sorted set (newest first)
        message_uuids = self.client.zrevrangebyscore(
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
            message_data = self.client.get(message_key)
            
            if message_data is None:
                # Message expired, remove from index
                self.client.zrem(index_key, message_uuid)
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
                self.client.zrem(index_key, message_uuid)
                continue
        
        metadata = {
            "total_messages": retrieved_count,
            "total_bytes": total_bytes,
            "truncated": len(message_uuids) > retrieved_count
        }
        
        return messages, metadata
    
    def bulk_erase(self, scope: MemoryScope) -> int:
        """
        Erase all messages for a scope across all channels.
        
        Args:
            scope: Memory scope
            
        Returns:
            Number of keys deleted
        """
        pattern = f"{scope.env}:{scope.agent_id}:{scope.user_id}:{scope.session_id}:*"
        keys = self.client.keys(pattern)
        
        if keys:
            return self.client.delete(*keys)
        return 0
    
    def count_bytes(self, scope: MemoryScope, channel: str) -> int:
        """
        Count total bytes for a scope and channel.
        
        Args:
            scope: Memory scope
            channel: Channel name
            
        Returns:
            Total bytes
        """
        index_key = scope.get_index_key(channel)
        message_uuids = self.client.zrange(index_key, 0, -1)
        
        total_bytes = 0
        for message_uuid in message_uuids:
            message_key = f"{scope.get_key_prefix(channel)}:{message_uuid}"
            message_data = self.client.get(message_key)
            
            if message_data is None:
                # Message expired, remove from index
                self.client.zrem(index_key, message_uuid)
                continue
            
            try:
                message = json.loads(message_data)
                content = message["content"]
                total_bytes += len(content.encode('utf-8'))
            except (json.JSONDecodeError, KeyError):
                # Invalid message, remove from index
                self.client.zrem(index_key, message_uuid)
                continue
        
        return total_bytes
    
    def checkpoint_set(self, scope: MemoryScope, key: str, payload: dict) -> None:
        """Set a checkpoint value."""
        checkpoint_key = f"{scope.env}:{scope.agent_id}:checkpoint:{key}"
        self.client.set(checkpoint_key, json.dumps(payload))
    
    def checkpoint_get(self, scope: MemoryScope, key: str) -> Optional[dict]:
        """Get a checkpoint value."""
        checkpoint_key = f"{scope.env}:{scope.agent_id}:checkpoint:{key}"
        data = self.client.get(checkpoint_key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return None
        return None
    
    def ping(self) -> bool:
        """Test Redis connection."""
        try:
            return self.client.ping()
        except Exception:
            return False
    
    def get_info(self) -> Dict[str, Any]:
        """Get Redis connection info."""
        return {
            "host": self.host,
            "port": self.port,
            "ssl": self.ssl,
            "db": self.db,
            "connected": self.ping(),
            "use_fakeredis": self.use_fakeredis
        }


class AsyncRedisAdapter:
    """Asynchronous Redis adapter for AIMemory."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        ssl: bool = False,
        db: int = 0,
        **kwargs
    ):
        if redis_async is None:
            raise ImportError("redis[asyncio] package is required. Install with: pip install redis[asyncio]")
        
        self.host = host
        self.port = port
        self.password = password
        self.ssl = ssl
        self.db = db
        
        self.client = redis_async.Redis(
            host=host,
            port=port,
            password=password,
            ssl=ssl,
            db=db,
            decode_responses=True,
            **kwargs
        )
    
    async def write_message(
        self,
        scope: MemoryScope,
        channel: str,
        content: Union[str, bytes],
        ttl_sec: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Async version of write_message."""
        message_uuid = str(uuid.uuid4())
        timestamp = int(time.time())
        
        message = {
            "uuid": message_uuid,
            "timestamp": timestamp,
            "content": content if isinstance(content, str) else content.decode('utf-8', errors='ignore'),
            "metadata": metadata or {}
        }
        
        message_key = f"{scope.get_key_prefix(channel)}:{message_uuid}"
        await self.client.setex(message_key, ttl_sec, json.dumps(message))
        
        index_key = scope.get_index_key(channel)
        await self.client.zadd(index_key, {message_uuid: timestamp})
        await self.client.expire(index_key, ttl_sec)
        
        return message_uuid
    
    async def read_messages(
        self,
        scope: MemoryScope,
        channel: str,
        *,
        since_sec: Optional[int] = None,
        max_msgs: Optional[int] = None,
        max_bytes: Optional[int] = None
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Async version of read_messages."""
        index_key = scope.get_index_key(channel)
        
        max_score = int(time.time())
        min_score = 0
        if since_sec is not None:
            min_score = max_score - since_sec
        
        message_uuids = await self.client.zrevrangebyscore(
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
            message_data = await self.client.get(message_key)
            
            if message_data is None:
                await self.client.zrem(index_key, message_uuid)
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
                await self.client.zrem(index_key, message_uuid)
                continue
        
        metadata = {
            "total_messages": retrieved_count,
            "total_bytes": total_bytes,
            "truncated": len(message_uuids) > retrieved_count
        }
        
        return messages, metadata
    
    async def bulk_erase(self, scope: MemoryScope) -> int:
        """Async version of bulk_erase."""
        pattern = f"{scope.env}:{scope.agent_id}:{scope.user_id}:{scope.session_id}:*"
        keys = await self.client.keys(pattern)
        
        if keys:
            return await self.client.delete(*keys)
        return 0
    
    async def count_bytes(self, scope: MemoryScope, channel: str) -> int:
        """Async version of count_bytes."""
        index_key = scope.get_index_key(channel)
        message_uuids = await self.client.zrange(index_key, 0, -1)
        
        total_bytes = 0
        for message_uuid in message_uuids:
            message_key = f"{scope.get_key_prefix(channel)}:{message_uuid}"
            message_data = await self.client.get(message_key)
            
            if message_data is None:
                await self.client.zrem(index_key, message_uuid)
                continue
            
            try:
                message = json.loads(message_data)
                content = message["content"]
                total_bytes += len(content.encode('utf-8'))
            except (json.JSONDecodeError, KeyError):
                await self.client.zrem(index_key, message_uuid)
                continue
        
        return total_bytes
    
    async def checkpoint_set(self, scope: MemoryScope, key: str, payload: dict) -> None:
        """Async version of checkpoint_set."""
        checkpoint_key = f"{scope.env}:{scope.agent_id}:checkpoint:{key}"
        await self.client.set(checkpoint_key, json.dumps(payload))
    
    async def checkpoint_get(self, scope: MemoryScope, key: str) -> Optional[dict]:
        """Async version of checkpoint_get."""
        checkpoint_key = f"{scope.env}:{scope.agent_id}:checkpoint:{key}"
        data = await self.client.get(checkpoint_key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return None
        return None
    
    async def ping(self) -> bool:
        """Test Redis connection."""
        try:
            return await self.client.ping()
        except Exception:
            return False
    
    async def close(self):
        """Close the Redis connection."""
        await self.client.close()
    
    def get_info(self) -> Dict[str, Any]:
        """Get Redis connection info."""
        return {
            "host": self.host,
            "port": self.port,
            "ssl": self.ssl,
            "db": self.db,
            "async": True
        }
