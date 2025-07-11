"""
Base storage adapter interfaces for NexaMem.
Defines the contract that all storage implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union

from ..memory_scope import MemoryScope


class StorageAdapter(ABC):
    """Base synchronous storage adapter interface."""
    
    @abstractmethod
    def write_message(
        self,
        scope: MemoryScope,
        channel: str,
        content: Union[str, bytes],
        ttl_sec: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Write a message to storage.
        
        Args:
            scope: Memory scope defining the context
            channel: Channel name
            content: Message content to store
            ttl_sec: Time-to-live in seconds
            metadata: Optional metadata dictionary
            
        Returns:
            Message UUID
        """
        pass
    
    @abstractmethod
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
        Read messages from storage.
        
        Args:
            scope: Memory scope defining the context
            channel: Channel name
            since_sec: Only messages newer than this (seconds ago)
            max_msgs: Maximum number of messages to return
            max_bytes: Maximum total bytes to return
            
        Returns:
            Tuple of (messages, metadata)
        """
        pass
    
    @abstractmethod
    def bulk_erase(self, scope: MemoryScope) -> int:
        """
        Erase all messages for a scope across all channels.
        
        Args:
            scope: Memory scope to erase
            
        Returns:
            Number of messages deleted
        """
        pass
    
    @abstractmethod
    def count_bytes(self, scope: MemoryScope, channel: str) -> int:
        """
        Count total bytes for a scope and channel.
        
        Args:
            scope: Memory scope
            channel: Channel name
            
        Returns:
            Total bytes
        """
        pass
    
    @abstractmethod
    def checkpoint_set(self, scope: MemoryScope, key: str, payload: dict) -> None:
        """
        Set a checkpoint value.
        
        Args:
            scope: Memory scope
            key: Checkpoint key
            payload: Data to store
        """
        pass
    
    @abstractmethod
    def checkpoint_get(self, scope: MemoryScope, key: str) -> Optional[dict]:
        """
        Get a checkpoint value.
        
        Args:
            scope: Memory scope
            key: Checkpoint key
            
        Returns:
            Stored data or None if not found
        """
        pass
    
    @abstractmethod
    def ping(self) -> bool:
        """
        Test storage connectivity.
        
        Returns:
            True if storage is accessible
        """
        pass
    
    def close(self) -> None:
        """Close storage connection. Default implementation does nothing."""
        pass


class AsyncStorageAdapter(ABC):
    """Base asynchronous storage adapter interface."""
    
    @abstractmethod
    async def write_message(
        self,
        scope: MemoryScope,
        channel: str,
        content: Union[str, bytes],
        ttl_sec: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Async version of write_message."""
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def bulk_erase(self, scope: MemoryScope) -> int:
        """Async version of bulk_erase."""
        pass
    
    @abstractmethod
    async def count_bytes(self, scope: MemoryScope, channel: str) -> int:
        """Async version of count_bytes."""
        pass
    
    @abstractmethod
    async def checkpoint_set(self, scope: MemoryScope, key: str, payload: dict) -> None:
        """Async version of checkpoint_set."""
        pass
    
    @abstractmethod
    async def checkpoint_get(self, scope: MemoryScope, key: str) -> Optional[dict]:
        """Async version of checkpoint_get."""
        pass
    
    @abstractmethod
    async def ping(self) -> bool:
        """Async version of ping."""
        pass
    
    async def close(self) -> None:
        """Close async storage connection. Default implementation does nothing."""
        pass
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
