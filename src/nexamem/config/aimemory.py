"""
AIMemory configuration model.
"""

from typing import Optional

from pydantic import BaseModel, Field

from .storage import StorageConfig


class AIMemoryConfig(BaseModel):
    """Configuration for AIMemory instances."""
    
    # Core configuration
    default_scope: Optional[str] = Field(None, description="Default scope for memory operations")
    
    # Storage configuration
    storage: StorageConfig
    
    # Channel configuration
    channels_yaml: Optional[str] = Field(None, description="Path to channels configuration YAML")
    strict_yaml_validation: bool = Field(default=True, description="Enable strict YAML schema validation")
    
    # Feature flags
    enable_audit: bool = Field(default=True, description="Enable audit logging")
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    enable_content_processing: bool = Field(default=False, description="Enable content processing chain")
    
    # Performance tuning
    async_preferred: bool = Field(default=True, description="Prefer async operations when available")
    connection_pool_size: Optional[int] = Field(None, description="Override storage connection pool size")
    
    @classmethod
    def from_env(cls) -> "AIMemoryConfig":
        """Create AIMemory configuration from environment variables."""
        import os
        return cls(
            default_scope=os.getenv('NEXAMEM_DEFAULT_SCOPE', 'default'),
            storage=StorageConfig.from_env(),
            channels_yaml=os.getenv('NEXAMEM_CHANNELS_YAML'),
            strict_yaml_validation=os.getenv('NEXAMEM_STRICT_YAML_VALIDATION', 'true').lower() == 'true',
            enable_audit=os.getenv('NEXAMEM_ENABLE_AUDIT', 'true').lower() == 'true',
            enable_metrics=os.getenv('NEXAMEM_ENABLE_METRICS', 'true').lower() == 'true',
            enable_content_processing=os.getenv('NEXAMEM_ENABLE_CONTENT_PROCESSING', 'false').lower() == 'true',
        )
