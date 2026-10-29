"""
AIMemory configuration model.
"""

from pydantic import BaseModel, Field

from .storage import StorageConfig


class AIMemoryConfig(BaseModel):
    """Configuration for AIMemory instances."""

    # Core configuration
    default_scope: str | None = Field(None, description="Default scope for memory operations")
    default_ttl_sec: int | None = Field(
        default=None, gt=0, description="Default logical record lifetime in seconds"
    )

    # Storage configuration
    storage: StorageConfig

    # Channel configuration
    channels_yaml: str | None = Field(None, description="Path to channels configuration YAML")
    strict_yaml_validation: bool = Field(
        default=True, description="Enable strict YAML schema validation"
    )

    # Feature flags
    enable_audit: bool = Field(default=True, description="Enable audit logging")
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    enable_content_processing: bool = Field(
        default=False, description="Enable content processing chain"
    )

    # Performance tuning
    async_preferred: bool = Field(
        default=True, description="Prefer async operations when available"
    )
    connection_pool_size: int | None = Field(
        default=None, description="Override storage connection pool size"
    )

    @classmethod
    def from_env(cls) -> "AIMemoryConfig":
        """Create AIMemory configuration from environment variables."""
        import os

        return cls(
            default_scope=os.getenv("NEXAMEM_DEFAULT_SCOPE", "default"),
            default_ttl_sec=int(os.environ["NEXAMEM_DEFAULT_TTL_SEC"])
            if os.getenv("NEXAMEM_DEFAULT_TTL_SEC")
            else None,
            storage=StorageConfig.from_env(),
            channels_yaml=os.getenv("NEXAMEM_CHANNELS_YAML"),
            strict_yaml_validation=os.getenv("NEXAMEM_STRICT_YAML_VALIDATION", "true").lower()
            == "true",
            enable_audit=os.getenv("NEXAMEM_ENABLE_AUDIT", "true").lower() == "true",
            enable_metrics=os.getenv("NEXAMEM_ENABLE_METRICS", "true").lower() == "true",
            enable_content_processing=os.getenv(
                "NEXAMEM_ENABLE_CONTENT_PROCESSING", "false"
            ).lower()
            == "true",
        )
