"""Base storage interfaces for NexaMem.

This module defines the contracts that all storage implementations must follow.
Provides both synchronous and asynchronous interfaces for maximum flexibility.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseStorage(ABC):
    """Base synchronous storage interface for AI memory management."""

    @abstractmethod
    def store_memory(
        self,
        memory_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        scope: Optional[str] = None
    ) -> bool:
        """Store a memory with the given ID and content.
        
        Args:
            memory_id: Unique identifier for the memory
            content: The memory content to store
            metadata: Optional metadata associated with the memory
            scope: Optional scope to group memories
            
        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def retrieve_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a memory by its ID.
        
        Args:
            memory_id: The unique identifier of the memory
            
        Returns:
            Dictionary containing memory data if found, None otherwise
        """
        pass

    @abstractmethod
    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by its ID.
        
        Args:
            memory_id: The unique identifier of the memory
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass

    @abstractmethod
    def list_memories(
        self, 
        scope: Optional[str] = None, 
        limit: Optional[int] = None
    ) -> List[str]:
        """List memory IDs, optionally filtered by scope.
        
        Args:
            scope: Optional scope to filter by
            limit: Optional limit on number of results
            
        Returns:
            List of memory IDs
        """
        pass

    @abstractmethod
    def search_memories(
        self, 
        query: str, 
        scope: Optional[str] = None, 
        limit: Optional[int] = None
    ) -> List[str]:
        """Search memories by content.
        
        Args:
            query: Search query string
            scope: Optional scope to search within
            limit: Optional limit on number of results
            
        Returns:
            List of matching memory IDs
        """
        pass

    @abstractmethod
    def get_audit_log(
        self, 
        memory_id: Optional[str] = None, 
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get audit log entries.
        
        Args:
            memory_id: Optional memory ID to filter by
            limit: Optional limit on number of entries
            
        Returns:
            List of audit log entries
        """
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics.
        
        Returns:
            Dictionary containing storage statistics
        """
        pass


class BaseAsyncStorage(ABC):
    """Base asynchronous storage interface for AI memory management."""

    @abstractmethod
    async def store_memory(
        self,
        memory_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        scope: Optional[str] = None
    ) -> bool:
        """Store a memory with the given ID and content (async).
        
        Args:
            memory_id: Unique identifier for the memory
            content: The memory content to store
            metadata: Optional metadata associated with the memory
            scope: Optional scope to group memories
            
        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def retrieve_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a memory by its ID (async).
        
        Args:
            memory_id: The unique identifier of the memory
            
        Returns:
            Dictionary containing memory data if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by its ID (async).
        
        Args:
            memory_id: The unique identifier of the memory
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass

    @abstractmethod
    async def list_memories(
        self, 
        scope: Optional[str] = None, 
        limit: Optional[int] = None
    ) -> List[str]:
        """List memory IDs, optionally filtered by scope (async).
        
        Args:
            scope: Optional scope to filter by
            limit: Optional limit on number of results
            
        Returns:
            List of memory IDs
        """
        pass

    @abstractmethod
    async def search_memories(
        self, 
        query: str, 
        scope: Optional[str] = None, 
        limit: Optional[int] = None
    ) -> List[str]:
        """Search memories by content (async).
        
        Args:
            query: Search query string
            scope: Optional scope to search within
            limit: Optional limit on number of results
            
        Returns:
            List of matching memory IDs
        """
        pass

    @abstractmethod
    async def get_audit_log(
        self, 
        memory_id: Optional[str] = None, 
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get audit log entries (async).
        
        Args:
            memory_id: Optional memory ID to filter by
            limit: Optional limit on number of entries
            
        Returns:
            List of audit log entries
        """
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics (async).
        
        Returns:
            Dictionary containing storage statistics
        """
        pass


# Legacy aliases for backward compatibility
StorageAdapter = BaseStorage
AsyncStorageAdapter = BaseAsyncStorage
