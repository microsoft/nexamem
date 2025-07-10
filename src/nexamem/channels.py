"""
Channel configuration and management for AIMemory.
"""
from typing import Dict, Optional
from pydantic import BaseModel, Field, field_validator
import re
import os

try:
    import yaml
except ImportError:
    # Fallback for when PyYAML is not installed
    yaml = None


class ChannelConfig(BaseModel):
    """Configuration for a memory channel."""
    
    name: str = Field(..., description="Channel name (snake_case)")
    ttl_sec: int = Field(..., description="Time-to-live in seconds (max 7 days)")
    encrypt: bool = Field(default=False, description="Enable client-side encryption")
    quota_bytes: Optional[int] = Field(default=None, description="Daily quota in bytes")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate channel name is snake_case."""
        if not re.match(r'^[a-z_]+$', v):
            raise ValueError("Channel name must be snake_case ([a-z_]+)")
        return v
    
    @field_validator('ttl_sec')
    @classmethod
    def validate_ttl(cls, v: int) -> int:
        """Validate TTL is positive and <= 7 days."""
        max_ttl = 7 * 24 * 60 * 60  # 7 days in seconds
        if v <= 0:
            raise ValueError("TTL must be positive")
        if v > max_ttl:
            raise ValueError(f"TTL cannot exceed 7 days ({max_ttl} seconds)")
        return v


class ChannelAlreadyExists(Exception):
    """Raised when attempting to register an existing channel."""
    pass


class ChannelManager:
    """Manages channel configurations from YAML and runtime registration."""
    
    def __init__(self, yaml_path: Optional[str] = None):
        self.channels: Dict[str, ChannelConfig] = {}
        self._yaml_path = yaml_path
        if yaml_path and os.path.exists(yaml_path):
            self.load_from_yaml(yaml_path)
    
    def load_from_yaml(self, yaml_path: str) -> None:
        """Load channel configurations from YAML file."""
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data or 'channels' not in data:
                return
            
            for name, config in data['channels'].items():
                channel_config = ChannelConfig(
                    name=name,
                    ttl_sec=config['ttl_sec'],
                    encrypt=config.get('encrypt', False),
                    quota_bytes=config.get('quota_bytes')
                )
                self.channels[name] = channel_config
                
        except Exception as e:
            raise ValueError(f"Failed to load channels from {yaml_path}: {e}")
    
    def register_channel(
        self, 
        name: str, 
        *, 
        ttl_sec: int, 
        encrypt: bool = False, 
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
            ChannelAlreadyExists: If channel name already exists
            ValueError: If channel configuration is invalid
        """
        if name in self.channels:
            raise ChannelAlreadyExists(f"Channel '{name}' already exists")
        
        channel_config = ChannelConfig(
            name=name,
            ttl_sec=ttl_sec,
            encrypt=encrypt,
            quota_bytes=quota_bytes
        )
        self.channels[name] = channel_config
    
    def get_channel(self, name: str) -> Optional[ChannelConfig]:
        """Get channel configuration by name."""
        return self.channels.get(name)
    
    def list_channels(self) -> Dict[str, ChannelConfig]:
        """List all registered channels."""
        return self.channels.copy()
    
    def channel_exists(self, name: str) -> bool:
        """Check if channel exists."""
        return name in self.channels


def get_default_channels_config() -> str:
    """Return default channels YAML configuration."""
    return """
channels:
  working:
    ttl_sec: 14400      # 4 hours
    encrypt: true

  procedure:
    ttl_sec: 604800     # 7 days
    encrypt: true

  routing:
    ttl_sec: 86400      # 24 hours
    encrypt: false
"""


def create_default_channels_yaml(path: str) -> None:
    """Create a default channels.yaml file."""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(get_default_channels_config().strip())
