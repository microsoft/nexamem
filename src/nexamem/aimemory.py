"""
Main AIMemory class implementing the requirements specification.

⚠️  DEPRECATED: This module is deprecated and will be removed in a future version.
Please migrate to the new DI-based AIMemory API. See LEGACY_API.md for migration guidance.
"""
import time
from typing import List, Dict, Optional, Tuple, Union, Callable, Any

from .memory_scope import MemoryScope
from .channels import ChannelManager, ChannelConfig
from .policy import PolicyEngine
from .redis_adapter import RedisAdapter, AsyncRedisAdapter
from .content_processor import ContentProcessorChain
from .audit import AuditSink
from . import metrics


class AIMemoryError(Exception):
    """Base exception for AIMemory operations."""
    pass


class ChannelNotFound(AIMemoryError):
    """Raised when channel is not found."""
    pass


class AIMemory:
    """
    Main AIMemory facade implementing Redis-backed conversational memory.
    Provides governed memory with channels, policies, and scope-based access.
    
    ⚠️  DEPRECATED: This class is deprecated and will be removed in a future version.
    Please migrate to the new DI-based AIMemory API. See LEGACY_API.md for migration guidance.
    """
    
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_password: Optional[str] = None,
        redis_ssl: bool = False,
        redis_db: int = 0,
        channels_yaml: Optional[str] = None,
        use_fakeredis: bool = False,
        enable_audit: bool = True,
        enable_metrics: bool = True,
        enable_content_processing: bool = False,
        strict_yaml_validation: bool = True,
        **redis_kwargs
    ):
        """
        Initialize AIMemory.
        
        Args:
            redis_host: Redis server hostname
            redis_port: Redis server port
            redis_password: Redis password
            redis_ssl: Use SSL connection
            redis_db: Redis database number
            channels_yaml: Path to channels configuration YAML
            use_fakeredis: Use fakeredis for testing
            enable_audit: Enable audit logging to Redis Stream
            enable_metrics: Enable metrics collection
            enable_content_processing: Enable content processor chain
            strict_yaml_validation: Enable strict YAML schema validation
            **redis_kwargs: Additional Redis connection parameters
        """
        # Initialize Redis adapter
        self.redis = RedisAdapter(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            ssl=redis_ssl,
            db=redis_db,
            use_fakeredis=use_fakeredis,
            **redis_kwargs
        )
        
        # Initialize channel manager
        self.channels = ChannelManager(channels_yaml, strict_validation=strict_yaml_validation)
        
        # Initialize policy engine
        self.policy = PolicyEngine()
        
        # Initialize audit sink
        self.audit = AuditSink(self.redis) if enable_audit else None
        
        # Initialize content processor chain
        self.content_processor = ContentProcessorChain() if enable_content_processing else None
        
        # Enable/disable metrics
        if not enable_metrics:
            metrics.get_metrics().disable()
    
    def write(
        self,
        scope: MemoryScope,
        channel: str,
        content: Union[str, bytes],
        *,
        pii: bool = False,
        ttl_override: Optional[int] = None,
        auto_pii: bool = False
    ) -> str:
        """
        Write content to a memory channel.
        
        Args:
            scope: Memory scope defining key structure
            channel: Channel name
            content: Content to store
            pii: Explicitly mark as PII
            ttl_override: Override channel TTL (must not exceed channel limit)
            auto_pii: Auto-detect PII in content
            
        Returns:
            Message UUID
            
        Raises:
            ChannelNotFound: If channel doesn't exist
            PolicyViolation: If any policy is violated
        """
        start_time = time.time()
        success = False
        
        try:
            # Get channel configuration
            channel_config = self.channels.get_channel(channel)
            if not channel_config:
                raise ChannelNotFound(f"Channel '{channel}' not found")
            
            # Process content through chain if enabled
            processed_content = content
            content_metadata = {}
            
            if self.content_processor and auto_pii:
                if isinstance(content, str):
                    processed_content, content_metadata = self.content_processor.process(content)
                    # Update auto_pii based on detection
                    if content_metadata.get('pii_detected'):
                        auto_pii = True
            
            # Validate against policies
            validation_result = self.policy.validate_write(
                content=processed_content,
                channel_config=channel_config,
                scope_dict=scope.model_dump(),
                pii=pii,
                ttl_override=ttl_override,
                auto_pii=auto_pii
            )
            
            # Write to Redis
            message_uuid = self.redis.write_message(
                scope=scope,
                channel=channel,
                content=processed_content,
                ttl_sec=validation_result["effective_ttl"],
                metadata={
                    "has_pii": validation_result["has_pii"],
                    "detected_pii": validation_result["detected_pii"],
                    "requires_encryption": validation_result["requires_encryption"],
                    **content_metadata
                }
            )
            
            # Update quotas
            self.policy.post_write_update(
                validation_result["content_bytes"],
                scope.model_dump(),
                channel
            )
            
            success = True
            
            # Log to audit stream
            if self.audit:
                self.audit.log_operation(
                    operation="write",
                    scope_dict=scope.model_dump(),
                    channel=channel,
                    metadata={
                        "message_uuid": message_uuid,
                        "content_length": len(str(content)),
                        "has_pii": validation_result["has_pii"],
                        "ttl_sec": validation_result["effective_ttl"]
                    }
                )
            
            return message_uuid
            
        finally:
            # Record metrics
            duration = time.time() - start_time
            metrics.record_write_operation(channel, success, duration)
    
    def read(
        self,
        scope: MemoryScope,
        channel: str,
        *,
        since_sec: Optional[int] = None,
        max_bytes: Optional[int] = None,
        max_msgs: Optional[int] = None,
        max_tokens: Optional[int] = None
    ) -> Tuple[List[str], Dict[str, Any]]:
        """
        Read messages from a memory channel.
        
        Args:
            scope: Memory scope
            channel: Channel name
            since_sec: Only messages newer than this (seconds ago)
            max_bytes: Maximum total bytes
            max_msgs: Maximum number of messages
            max_tokens: Maximum total tokens (not implemented in MVP)
            
        Returns:
            Tuple of (messages, metadata)
            
        Raises:
            ChannelNotFound: If channel doesn't exist
        """
        start_time = time.time()
        success = False
        
        try:
            # Verify channel exists
            if not self.channels.channel_exists(channel):
                raise ChannelNotFound(f"Channel '{channel}' not found")
            
            # TODO: Implement token-based truncation when max_tokens is specified
            # NOTE: This is legacy code - new API handles this differently
            if max_tokens is not None:
                # For MVP, ignore max_tokens and add to metadata
                pass
            
            messages, metadata = self.redis.read_messages(
                scope=scope,
                channel=channel,
                since_sec=since_sec,
                max_msgs=max_msgs,
                max_bytes=max_bytes
            )
            
            # Add token info to metadata (placeholder for MVP)
            if max_tokens is not None:
                metadata["max_tokens_requested"] = max_tokens
                metadata["token_truncation"] = "not_implemented_in_mvp"
            
            success = True
            
            # Log to audit stream
            if self.audit:
                self.audit.log_operation(
                    operation="read",
                    scope_dict=scope.model_dump(),
                    channel=channel,
                    metadata={
                        "messages_returned": len(messages),
                        "total_bytes": metadata.get("total_bytes", 0),
                        "since_sec": since_sec,
                        "max_msgs": max_msgs,
                        "max_bytes": max_bytes
                    }
                )
            
            return messages, metadata
            
        finally:
            # Record metrics
            duration = time.time() - start_time
            metrics.record_read_operation(channel, success, duration)
    
    def checkpoint(self, scope: MemoryScope, key: str, payload: dict) -> None:
        """
        Set a checkpoint value.
        
        Args:
            scope: Memory scope
            key: Checkpoint key
            payload: Data to store
        """
        start_time = time.time()
        success = False
        
        try:
            self.redis.checkpoint_set(scope, key, payload)
            success = True
            
            # Log to audit stream
            if self.audit:
                self.audit.log_operation(
                    operation="checkpoint",
                    scope_dict=scope.model_dump(),
                    metadata={
                        "checkpoint_key": key,
                        "payload_size": len(str(payload))
                    }
                )
        finally:
            # Record metrics
            duration = time.time() - start_time
            metrics.record_checkpoint_operation("set", success, duration)
    
    def checkpoint_atomic(
        self,
        scope: MemoryScope,
        key: str,
        update_fn: Callable[[Optional[dict]], dict]
    ) -> dict:
        """
        Atomically update a checkpoint value.
        
        Args:
            scope: Memory scope
            key: Checkpoint key
            update_fn: Function to update the value
            
        Returns:
            Updated payload
            
        Note: For MVP, this is not truly atomic. Production would use Redis Lua scripts.
        """
        # Get current value
        current = self.redis.checkpoint_get(scope, key)
        
        # Apply update function
        updated = update_fn(current)
        
        # Store updated value
        self.redis.checkpoint_set(scope, key, updated)
        
        return updated
    
    def bulk_erase(self, scope: MemoryScope) -> int:
        """
        Erase all messages for a scope across all channels.
        
        Args:
            scope: Memory scope
            
        Returns:
            Number of keys deleted
        """
        return self.redis.bulk_erase(scope)
    
    def count_bytes(self, scope: MemoryScope, channel: str) -> int:
        """
        Count total bytes for a scope and channel.
        
        Args:
            scope: Memory scope
            channel: Channel name
            
        Returns:
            Total bytes
            
        Raises:
            ChannelNotFound: If channel doesn't exist
        """
        if not self.channels.channel_exists(channel):
            raise ChannelNotFound(f"Channel '{channel}' not found")
        
        return self.redis.count_bytes(scope, channel)
    
    def register_channel(
        self,
        name: str,
        *,
        ttl_sec: int,
        encrypt: bool,
        quota_bytes: Optional[int] = None
    ) -> None:
        """
        Register a new channel at runtime.
        
        Args:
            name: Channel name (snake_case)
            ttl_sec: Time-to-live in seconds (max 7 days)
            encrypt: Enable client-side encryption
            quota_bytes: Optional daily quota in bytes
            
        Raises:
            ChannelAlreadyExists: If channel already exists
        """
        self.channels.register_channel(
            name=name,
            ttl_sec=ttl_sec,
            encrypt=encrypt,
            quota_bytes=quota_bytes
        )
    
    def list_channels(self) -> Dict[str, ChannelConfig]:
        """List all registered channels."""
        return self.channels.list_channels()
    
    def get_channel_config(self, name: str) -> Optional[ChannelConfig]:
        """Get configuration for a specific channel."""
        return self.channels.get_channel(name)


class AsyncAIMemory:
    """
    Asynchronous version of AIMemory for high-throughput scenarios.
    
    ⚠️  DEPRECATED: This class is deprecated and will be removed in a future version.
    Please migrate to the new DI-based AsyncAIMemory API. See LEGACY_API.md for migration guidance.
    """
    
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_password: Optional[str] = None,
        redis_ssl: bool = False,
        redis_db: int = 0,
        channels_yaml: Optional[str] = None,
        **redis_kwargs
    ):
        """Initialize AsyncAIMemory."""
        # Initialize async Redis adapter
        self.redis = AsyncRedisAdapter(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            ssl=redis_ssl,
            db=redis_db,
            **redis_kwargs
        )
        
        # Initialize channel manager (sync)
        self.channels = ChannelManager(channels_yaml)
        
        # Initialize policy engine (sync)
        self.policy = PolicyEngine()
    
    async def write(
        self,
        scope: MemoryScope,
        channel: str,
        content: Union[str, bytes],
        *,
        pii: bool = False,
        ttl_override: Optional[int] = None,
        auto_pii: bool = False
    ) -> str:
        """Async version of write."""
        channel_config = self.channels.get_channel(channel)
        if not channel_config:
            raise ChannelNotFound(f"Channel '{channel}' not found")
        
        validation_result = self.policy.validate_write(
            content=content,
            channel_config=channel_config,
            scope_dict=scope.model_dump(),
            pii=pii,
            ttl_override=ttl_override,
            auto_pii=auto_pii
        )
        
        message_uuid = await self.redis.write_message(
            scope=scope,
            channel=channel,
            content=content,
            ttl_sec=validation_result["effective_ttl"],
            metadata={
                "has_pii": validation_result["has_pii"],
                "detected_pii": validation_result["detected_pii"],
                "requires_encryption": validation_result["requires_encryption"]
            }
        )
        
        self.policy.post_write_update(
            validation_result["content_bytes"],
            scope.model_dump(),
            channel
        )
        
        return message_uuid
    
    async def read(
        self,
        scope: MemoryScope,
        channel: str,
        *,
        since_sec: Optional[int] = None,
        max_bytes: Optional[int] = None,
        max_msgs: Optional[int] = None,
        max_tokens: Optional[int] = None
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Async version of read."""
        if not self.channels.channel_exists(channel):
            raise ChannelNotFound(f"Channel '{channel}' not found")
        
        messages, metadata = await self.redis.read_messages(
            scope=scope,
            channel=channel,
            since_sec=since_sec,
            max_msgs=max_msgs,
            max_bytes=max_bytes
        )
        
        if max_tokens is not None:
            metadata["max_tokens_requested"] = max_tokens
            metadata["token_truncation"] = "not_implemented_in_mvp"
        
        return messages, metadata
    
    async def checkpoint(self, scope: MemoryScope, key: str, payload: dict) -> None:
        """Async version of checkpoint."""
        await self.redis.checkpoint_set(scope, key, payload)
    
    async def checkpoint_atomic(
        self,
        scope: MemoryScope,
        key: str,
        update_fn: Callable[[Optional[dict]], dict]
    ) -> dict:
        """Async version of checkpoint_atomic."""
        current = await self.redis.checkpoint_get(scope, key)
        updated = update_fn(current)
        await self.redis.checkpoint_set(scope, key, updated)
        return updated
    
    async def bulk_erase(self, scope: MemoryScope) -> int:
        """Async version of bulk_erase."""
        return await self.redis.bulk_erase(scope)
    
    async def count_bytes(self, scope: MemoryScope, channel: str) -> int:
        """Async version of count_bytes."""
        if not self.channels.channel_exists(channel):
            raise ChannelNotFound(f"Channel '{channel}' not found")
        
        return await self.redis.count_bytes(scope, channel)
    
    def register_channel(
        self,
        name: str,
        *,
        ttl_sec: int,
        encrypt: bool,
        quota_bytes: Optional[int] = None
    ) -> None:
        """Register a new channel (sync operation)."""
        self.channels.register_channel(
            name=name,
            ttl_sec=ttl_sec,
            encrypt=encrypt,
            quota_bytes=quota_bytes
        )
    
    def list_channels(self) -> Dict[str, ChannelConfig]:
        """List all registered channels (sync operation)."""
        return self.channels.list_channels()
    
    def get_channel_config(self, name: str) -> Optional[ChannelConfig]:
        """Get channel configuration (sync operation)."""
        return self.channels.get_channel(name)
    
    async def close(self):
        """Close the async Redis connection."""
        await self.redis.close()
