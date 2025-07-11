"""
Policy engine for AIMemory with TTL, encryption, quota, and PII enforcement.
"""
import re
import time
from typing import Any, Dict, Optional, Union

from .channels import ChannelConfig


class PolicyViolation(Exception):
    """Base exception for policy violations."""
    pass


class QuotaExceeded(PolicyViolation):
    """Raised when quota limits are exceeded."""
    pass


class EncryptionRequired(PolicyViolation):
    """Raised when PII content requires encryption but channel doesn't support it."""
    pass


class TTLViolation(PolicyViolation):
    """Raised when TTL override exceeds channel limit."""
    pass


class PIIDetector:
    """Simple PII detector for MVP. Uses basic regex patterns."""
    
    # Basic patterns for common PII types (MVP implementation)
    PII_PATTERNS = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
    }
    
    def __init__(self, patterns: Optional[Dict[str, str]] = None):
        """Initialize with custom or default PII patterns."""
        self.patterns = patterns or self.PII_PATTERNS
        self.compiled_patterns = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.patterns.items()
        }
    
    def detect_pii(self, content: str) -> Dict[str, bool]:
        """
        Detect PII in content.
        
        Args:
            content: Text to analyze
            
        Returns:
            Dictionary mapping PII type to detection result
        """
        results = {}
        for pii_type, pattern in self.compiled_patterns.items():
            results[pii_type] = bool(pattern.search(content))
        return results
    
    def has_pii(self, content: str) -> bool:
        """Check if content contains any PII."""
        return any(self.detect_pii(content).values())


class QuotaTracker:
    """Tracks daily quotas per (agent, user, channel)."""
    
    def __init__(self):
        # In-memory quota tracking (production would use Redis)
        # Format: {agent_id:user_id:channel} -> {date: str, bytes_used: int}
        self._quotas: Dict[str, Dict[str, Any]] = {}
    
    def _get_quota_key(self, agent_id: str, user_id: str, channel: str) -> str:
        """Generate quota tracking key."""
        return f"{agent_id}:{user_id}:{channel}"
    
    def _get_current_date(self) -> str:
        """Get current date string."""
        return time.strftime("%Y-%m-%d")
    
    def check_quota(
        self, 
        agent_id: str, 
        user_id: str, 
        channel: str, 
        content_bytes: int,
        quota_limit: Optional[int]
    ) -> None:
        """
        Check if adding content would exceed quota.
        
        Raises:
            QuotaExceeded: If quota would be exceeded
        """
        if quota_limit is None:
            return  # No quota limit
        
        quota_key = self._get_quota_key(agent_id, user_id, channel)
        current_date = self._get_current_date()
        
        # Get current usage
        if quota_key not in self._quotas:
            self._quotas[quota_key] = {"date": current_date, "bytes_used": 0}
        
        quota_data = self._quotas[quota_key]
        
        # Reset if new day
        if quota_data["date"] != current_date:
            quota_data = {"date": current_date, "bytes_used": 0}
            self._quotas[quota_key] = quota_data
        
        # Check if adding content would exceed quota
        new_total = quota_data["bytes_used"] + content_bytes
        if new_total > quota_limit:
            raise QuotaExceeded(
                f"Daily quota exceeded for {agent_id}:{user_id}:{channel}. "
                f"Limit: {quota_limit}, Current: {quota_data['bytes_used']}, "
                f"Requested: {content_bytes}"
            )
    
    def update_quota(
        self, 
        agent_id: str, 
        user_id: str, 
        channel: str, 
        content_bytes: int
    ) -> None:
        """Update quota usage after successful write."""
        quota_key = self._get_quota_key(agent_id, user_id, channel)
        current_date = self._get_current_date()
        
        if quota_key not in self._quotas:
            self._quotas[quota_key] = {"date": current_date, "bytes_used": 0}
        
        quota_data = self._quotas[quota_key]
        if quota_data["date"] != current_date:
            quota_data = {"date": current_date, "bytes_used": 0}
        
        quota_data["bytes_used"] += content_bytes
        self._quotas[quota_key] = quota_data


class PolicyEngine:
    """Enforces policy rules for AIMemory operations."""
    
    def __init__(self, pii_detector: Optional[PIIDetector] = None):
        self.pii_detector = pii_detector or PIIDetector()
        self.quota_tracker = QuotaTracker()
    
    def validate_write(
        self,
        content: Union[str, bytes],
        channel_config: ChannelConfig,
        scope_dict: Dict[str, str],
        *,
        pii: bool = False,
        ttl_override: Optional[int] = None,
        auto_pii: bool = False
    ) -> Dict[str, Any]:
        """
        Validate a write operation against all policies.
        
        Args:
            content: Content to write
            channel_config: Channel configuration
            scope_dict: MemoryScope as dictionary
            pii: Explicitly flagged as PII
            ttl_override: Override TTL (must not exceed channel TTL)
            auto_pii: Auto-detect PII
            
        Returns:
            Validation result with metadata
            
        Raises:
            PolicyViolation: If any policy is violated
        """
        # Convert content to string for analysis
        content_str = content if isinstance(content, str) else content.decode('utf-8', errors='ignore')
        content_bytes = len(content.encode('utf-8')) if isinstance(content, str) else len(content)
        
        # TTL validation
        if ttl_override is not None:
            if ttl_override > channel_config.ttl_sec:
                raise TTLViolation(
                    f"TTL override ({ttl_override}s) exceeds channel limit ({channel_config.ttl_sec}s)"
                )
        
        # PII detection and encryption validation
        detected_pii = {}
        has_pii_content = pii  # Start with explicit flag
        
        if auto_pii or not pii:
            detected_pii = self.pii_detector.detect_pii(content_str)
            if auto_pii and any(detected_pii.values()):
                has_pii_content = True
        
        # If content has PII, channel must support encryption
        if has_pii_content and not channel_config.encrypt:
            raise EncryptionRequired(
                f"Content flagged as PII but channel '{channel_config.name}' "
                f"does not have encryption enabled"
            )
        
        # Quota validation
        self.quota_tracker.check_quota(
            scope_dict["agent_id"],
            scope_dict["user_id"],
            channel_config.name,
            content_bytes,
            channel_config.quota_bytes
        )
        
        return {
            "has_pii": has_pii_content,
            "detected_pii": detected_pii,
            "content_bytes": content_bytes,
            "effective_ttl": ttl_override or channel_config.ttl_sec,
            "requires_encryption": has_pii_content and channel_config.encrypt
        }
    
    def post_write_update(
        self,
        content_bytes: int,
        scope_dict: Dict[str, str],
        channel_name: str
    ) -> None:
        """Update quotas after successful write."""
        self.quota_tracker.update_quota(
            scope_dict["agent_id"],
            scope_dict["user_id"],
            channel_name,
            content_bytes
        )
