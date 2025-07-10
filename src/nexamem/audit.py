"""
Audit sink for mirroring operations to Redis Stream.
"""
import json
import time
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class AuditSink:
    """
    Mirrors every AIMemory operation as JSON into a Redis Stream.
    TTL: 365 days for compliance and audit trails.
    """
    
    def __init__(self, redis_adapter, stream_name: str = "aimemory:audit"):
        self.redis_adapter = redis_adapter
        self.stream_name = stream_name
        self.ttl_days = 365
        self.enabled = True
    
    def log_operation(
        self,
        operation: str,
        scope_dict: Dict[str, Any],
        channel: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an operation to the audit stream.
        
        Args:
            operation: Operation type (write, read, checkpoint, etc.)
            scope_dict: MemoryScope as dict
            channel: Channel name (if applicable)
            metadata: Additional operation metadata
        """
        if not self.enabled:
            return
        
        try:
            audit_record = {
                "timestamp": time.time(),
                "operation": operation,
                "scope": scope_dict,
                "channel": channel,
                "metadata": metadata or {}
            }
            
            # Add to Redis Stream
            self._add_to_stream(audit_record)
            
        except Exception as e:
            logger.warning(f"Failed to log audit record: {e}")
    
    def _add_to_stream(self, record: Dict[str, Any]) -> None:
        """Add record to Redis Stream."""
        try:
            # Convert record to string fields for Redis Stream
            fields = {
                "data": json.dumps(record, default=str)
            }
            
            # Add to stream with TTL
            self.redis_adapter.client.xadd(
                self.stream_name,
                fields,
                id='*'  # Auto-generate ID
            )
            
            # Set TTL on the stream (Redis doesn't support per-message TTL in streams)
            ttl_seconds = self.ttl_days * 24 * 60 * 60
            self.redis_adapter.client.expire(self.stream_name, ttl_seconds)
            
        except Exception as e:
            logger.warning(f"Failed to add audit record to stream: {e}")
    
    def get_audit_records(
        self,
        start: str = '-',
        end: str = '+',
        count: Optional[int] = None
    ) -> list:
        """
        Retrieve audit records from the stream.
        
        Args:
            start: Start ID (default: from beginning)
            end: End ID (default: to end)
            count: Maximum number of records
            
        Returns:
            List of audit records
        """
        try:
            kwargs = {'start': start, 'end': end}
            if count:
                kwargs['count'] = count
            
            records = self.redis_adapter.client.xrange(self.stream_name, **kwargs)
            
            # Parse JSON data
            parsed_records = []
            for record_id, fields in records:
                try:
                    data = json.loads(fields[b'data'].decode('utf-8'))
                    data['stream_id'] = record_id.decode('utf-8')
                    parsed_records.append(data)
                except (json.JSONDecodeError, KeyError, UnicodeDecodeError) as e:
                    logger.warning(f"Failed to parse audit record {record_id}: {e}")
                    continue
            
            return parsed_records
            
        except Exception as e:
            logger.warning(f"Failed to retrieve audit records: {e}")
            return []
    
    def disable(self) -> None:
        """Disable audit logging."""
        self.enabled = False
    
    def enable(self) -> None:
        """Enable audit logging."""
        self.enabled = True


class AsyncAuditSink:
    """Async version of AuditSink."""
    
    def __init__(self, redis_adapter, stream_name: str = "aimemory:audit"):
        self.redis_adapter = redis_adapter
        self.stream_name = stream_name
        self.ttl_days = 365
        self.enabled = True
    
    async def log_operation(
        self,
        operation: str,
        scope_dict: Dict[str, Any],
        channel: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Async version of log_operation."""
        if not self.enabled:
            return
        
        try:
            audit_record = {
                "timestamp": time.time(),
                "operation": operation,
                "scope": scope_dict,
                "channel": channel,
                "metadata": metadata or {}
            }
            
            await self._add_to_stream(audit_record)
            
        except Exception as e:
            logger.warning(f"Failed to log audit record: {e}")
    
    async def _add_to_stream(self, record: Dict[str, Any]) -> None:
        """Async version of _add_to_stream."""
        try:
            fields = {
                "data": json.dumps(record, default=str)
            }
            
            await self.redis_adapter.client.xadd(
                self.stream_name,
                fields,
                id='*'
            )
            
            ttl_seconds = self.ttl_days * 24 * 60 * 60
            await self.redis_adapter.client.expire(self.stream_name, ttl_seconds)
            
        except Exception as e:
            logger.warning(f"Failed to add audit record to stream: {e}")
    
    def disable(self) -> None:
        """Disable audit logging."""
        self.enabled = False
    
    def enable(self) -> None:
        """Enable audit logging."""
        self.enabled = True
