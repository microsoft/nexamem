# isort: skip_file
# Legacy API imports (deprecated - will be removed in future version)
from .history import ChatHistory
from .config import initialize, get_config
from .aimemory import AIMemory as LegacyAIMemory, AsyncAIMemory as LegacyAsyncAIMemory
from .memory_scope import MemoryScope
from .channels import ChannelConfig, ChannelManager, ChannelAlreadyExists
from .policy import PolicyEngine, PIIDetector, PolicyViolation, QuotaExceeded, EncryptionRequired, TTLViolation
from .content_processor import ContentProcessorChain, PIIRedactor, ContentEnricher
from .audit import AuditSink, AsyncAuditSink
from . import metrics

# New DI-based API
from .new_aimemory import AIMemory, AsyncAIMemory, create_aimemory
from .config.aimemory import AIMemoryConfig
from .config.storage import StorageConfig, AzureRedisConfig, MemoryConfig, FileConfig, SQLiteConfig
from .di import DIContainer, ServiceRegistry, ServiceProvider
from .storage import StorageFactory, create_storage_from_config

# Version information
__version__ = "0.4.2"

__all__ = [
    # Version
    "__version__",
    # Legacy API (deprecated - will be removed in future version)
    "ChatHistory",
    "initialize",
    "get_config",
    "LegacyAIMemory",
    "LegacyAsyncAIMemory",
    # New DI-based AIMemory API (recommended)
    "AIMemory",
    "AsyncAIMemory",
    "create_aimemory",
    "AIMemoryConfig",
    "StorageConfig",
    "AzureRedisConfig",
    "MemoryConfig",
    "FileConfig",
    "SQLiteConfig",
    "DIContainer",
    "ServiceRegistry",
    "ServiceProvider",
    "StorageFactory",
    "create_storage_from_config",
    # Existing components
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
