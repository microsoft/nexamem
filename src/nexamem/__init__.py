from .history import ChatHistory
from .config import initialize, get_config
from .aimemory import AIMemory, AsyncAIMemory
from .memory_scope import MemoryScope
from .channels import ChannelConfig, ChannelManager, ChannelAlreadyExists
from .policy import PolicyEngine, PIIDetector, PolicyViolation, QuotaExceeded, EncryptionRequired, TTLViolation
from .content_processor import ContentProcessorChain, PIIRedactor, ContentEnricher
from .audit import AuditSink, AsyncAuditSink
from . import metrics

# Version information
__version__ = "0.3.4"

__all__ = [
    # Version
    "__version__",
    # Legacy API (backward compatibility)
    "ChatHistory",
    "initialize",
    "get_config",
    # New AIMemory API
    "AIMemory",
    "AsyncAIMemory",
    "MemoryScope",
    "ChannelConfig",
    "ChannelManager",
    "ChannelAlreadyExists",
    "PolicyEngine",
    "PIIDetector",
    "PolicyViolation",
    "QuotaExceeded",
    "EncryptionRequired",
    "TTLViolation",
    # Content Processing
    "ContentProcessorChain",
    "PIIRedactor",
    "ContentEnricher",
    # Audit and Metrics
    "AuditSink",
    "AsyncAuditSink",
    "metrics"
]
