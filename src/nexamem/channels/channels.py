"""
Channel configuration and management for AIMemory.
"""
import os
import re
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator

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
        if not isinstance(v, str):
            raise ValueError("Channel name must be a string")
        if not v:
            raise ValueError("Channel name cannot be empty")
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError(
                "Channel name must be snake_case: start with lowercase letter, "
                "followed by lowercase letters, numbers, or underscores ([a-z][a-z0-9_]*)"
            )
        if len(v) > 50:
            raise ValueError("Channel name cannot exceed 50 characters")
        return v
    
    @field_validator('ttl_sec')
    @classmethod
    def validate_ttl(cls, v: int) -> int:
        """Validate TTL is positive and <= 7 days."""
        if not isinstance(v, int):
            raise ValueError("TTL must be an integer")
        max_ttl = 7 * 24 * 60 * 60  # 7 days in seconds
        min_ttl = 60  # 1 minute minimum
        if v < min_ttl:
            raise ValueError(f"TTL must be at least {min_ttl} seconds (1 minute)")
        if v > max_ttl:
            raise ValueError(f"TTL cannot exceed {max_ttl} seconds (7 days)")
        return v
    
    @field_validator('quota_bytes')
    @classmethod
    def validate_quota_bytes(cls, v: Optional[int]) -> Optional[int]:
        """Validate quota_bytes if provided."""
        if v is not None:
            if not isinstance(v, int):
                raise ValueError("quota_bytes must be an integer")
            if v <= 0:
                raise ValueError("quota_bytes must be positive")
            if v > 1_000_000_000:  # 1GB limit
                raise ValueError("quota_bytes cannot exceed 1GB (1,000,000,000 bytes)")
        return v


class ChannelsYamlSchema(BaseModel):
    """Schema for the complete channels.yaml file."""
    
    channels: Dict[str, Dict[str, Any]] = Field(..., description="Channel configurations")
    
    @field_validator('channels')
    @classmethod
    def validate_channels_dict(cls, v: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Validate the channels dictionary structure."""
        if not isinstance(v, dict):
            raise ValueError("'channels' must be a dictionary")
        
        if not v:
            raise ValueError("At least one channel must be defined")
        
        # Reserved channel names that shouldn't be used
        reserved_names = {'admin', 'system', 'internal', 'redis', 'audit'}
        
        for channel_name, channel_config in v.items():
            # Validate channel name at top level
            if not isinstance(channel_name, str):
                raise ValueError(f"Channel name must be string, got {type(channel_name)}")
            
            if channel_name in reserved_names:
                raise ValueError(f"Channel name '{channel_name}' is reserved")
            
            # Validate channel config structure
            if not isinstance(channel_config, dict):
                raise ValueError(f"Channel '{channel_name}' config must be a dictionary")
            
            # Check required fields
            if 'ttl_sec' not in channel_config:
                raise ValueError(f"Channel '{channel_name}' missing required field 'ttl_sec'")
            
            # Check for unknown fields
            allowed_fields = {'ttl_sec', 'encrypt', 'quota_bytes'}
            unknown_fields = set(channel_config.keys()) - allowed_fields
            if unknown_fields:
                raise ValueError(
                    f"Channel '{channel_name}' has unknown fields: {', '.join(unknown_fields)}. "
                    f"Allowed fields: {', '.join(allowed_fields)}"
                )
        
        return v


class YamlSchemaError(Exception):
    """Raised when YAML schema validation fails."""
    pass


class ChannelAlreadyExists(Exception):
    """Raised when attempting to register an existing channel."""
    pass


def validate_yaml_schema(yaml_path: str) -> Dict[str, Any]:
    """
    Validate YAML file against the channels schema.

    Args:
        yaml_path: Path to the YAML file

    Returns:
        Validated YAML data

    Raises:
        YamlSchemaError: If validation fails
    """
    if not yaml:
        raise YamlSchemaError("PyYAML is required for YAML validation")

    try:
        with open(yaml_path, encoding='utf-8') as f:
            raw_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise YamlSchemaError(f"Invalid YAML syntax: {e}") from e
    except FileNotFoundError as e:
        raise YamlSchemaError(f"YAML file not found: {yaml_path}") from e
    except Exception as e:
        raise YamlSchemaError(f"Failed to read YAML file: {e}") from e

    if not raw_data:
        raise YamlSchemaError("YAML file is empty")

    # Validate overall schema structure
    try:
        ChannelsYamlSchema(**raw_data)
    except ValidationError as e:
        error_details = []
        for error in e.errors():
            loc = " -> ".join(str(x) for x in error['loc'])
            error_details.append(f"{loc}: {error['msg']}")
        raise YamlSchemaError("Schema validation failed:\n" + "\n".join(error_details)) from e

    # Validate individual channel configs
    validation_errors = []
    for channel_name, channel_data in raw_data['channels'].items():
        try:
            ChannelConfig(name=channel_name, **channel_data)
        except ValidationError as e:
            for error in e.errors():
                field = error['loc'][0] if error['loc'] else 'unknown'
                validation_errors.append(f"Channel '{channel_name}', field '{field}': {error['msg']}")

    if validation_errors:
        raise YamlSchemaError("Channel validation failed:\n" + "\n".join(validation_errors))

    return raw_data


def generate_yaml_schema_docs() -> str:
    """Generate documentation for the YAML schema."""
    return """
# channels.yaml Schema Documentation

The channels.yaml file must follow this structure:

```yaml
channels:
  channel_name:
    ttl_sec: <integer>      # Required: 60 to 604800 (1 min to 7 days)
    encrypt: <boolean>      # Optional: true/false (default: false)
    quota_bytes: <integer>  # Optional: 1 to 1000000000 (1B to 1GB)
```

## Field Validation Rules:

### Channel Names:
- Must be snake_case: start with lowercase letter, followed by letters/numbers/underscores
- Cannot be empty or exceed 50 characters  
- Cannot use reserved names: admin, system, internal, redis, audit

### ttl_sec:
- Must be integer between 60 (1 minute) and 604800 (7 days)

### encrypt:
- Optional boolean (default: false)
- When true, enables client-side encryption

### quota_bytes:
- Optional integer between 1 and 1,000,000,000 (1GB)
- Daily quota limit per (agent, user, channel)

## Example:

```yaml
channels:
  working:
    ttl_sec: 14400      # 4 hours
    encrypt: true
    quota_bytes: 1000000 # 1MB

  routing:
    ttl_sec: 86400      # 24 hours  
    encrypt: false
```
"""


class ChannelManager:
    """Manages channel configurations from YAML and runtime registration."""
    
    def __init__(self, yaml_path: Optional[str] = None, strict_validation: bool = True):
        self.channels: Dict[str, ChannelConfig] = {}
        self._yaml_path = yaml_path
        self._strict_validation = strict_validation
        
        if yaml_path and os.path.exists(yaml_path):
            self.load_from_yaml(yaml_path)
    
    def load_from_yaml(self, yaml_path: str) -> None:
        """Load channel configurations from YAML file with schema validation."""
        try:
            if self._strict_validation:
                # Use strict schema validation
                validated_data = validate_yaml_schema(yaml_path)
                channels_data = validated_data['channels']
            else:
                # Fallback to basic loading (backward compatibility)
                with open(yaml_path, encoding='utf-8') as f:
                    data = yaml.safe_load(f)

                if not data or 'channels' not in data:
                    return
                channels_data = data['channels']

            # Load validated channels
            for name, config in channels_data.items():
                channel_config = ChannelConfig(
                    name=name,
                    ttl_sec=config['ttl_sec'],
                    encrypt=config.get('encrypt', False),
                    quota_bytes=config.get('quota_bytes')
                )
                self.channels[name] = channel_config

        except YamlSchemaError as e:
            raise ValueError(f"YAML schema validation failed for {yaml_path}: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to load channels from {yaml_path}: {e}") from e

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
