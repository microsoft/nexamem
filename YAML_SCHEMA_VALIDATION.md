# YAML Schema Validation for AIMemory Channels

## Overview

AIMemory now supports **strict YAML schema validation** to ensure channel configurations are correct, secure, and follow best practices. This prevents runtime errors and enforces consistent configuration across teams.

## Features

### ✅ **Comprehensive Field Validation**
- **Channel Names**: Must be `snake_case` (lowercase letters, numbers, underscores only)
- **TTL Limits**: Between 60 seconds (1 minute) and 604,800 seconds (7 days)
- **Quota Limits**: Between 1 byte and 1GB (1,000,000,000 bytes)
- **Required Fields**: All channels must have `ttl_sec`
- **Field Types**: Strict type checking for integers, booleans, strings

### ✅ **Security & Best Practices**
- **Reserved Names**: Prevents use of `admin`, `system`, `internal`, `redis`, `audit`
- **Unknown Fields**: Rejects configuration with unrecognized properties
- **Empty Validation**: Requires at least one channel to be defined

### ✅ **Clear Error Messages**
- Detailed validation errors with field-level specificity
- Multiple error reporting (shows all issues at once)
- YAML syntax error detection and reporting

## Usage

### Basic Usage (Strict Validation Enabled by Default)

```python
from nexamem import AIMemory

# Strict validation enabled by default
memory = AIMemory(
    channels_yaml="path/to/channels.yaml",
    strict_yaml_validation=True  # Default: True
)
```

### Backward Compatibility Mode

```python
# Disable strict validation for legacy configurations
memory = AIMemory(
    channels_yaml="path/to/channels.yaml", 
    strict_yaml_validation=False
)
```

### Standalone Validation

```python
from nexamem.channels import validate_yaml_schema, YamlSchemaError

try:
    validated_data = validate_yaml_schema("channels.yaml")
    print("✅ Configuration is valid!")
    print(f"Found {len(validated_data['channels'])} channels")
except YamlSchemaError as e:
    print(f"❌ Validation failed: {e}")
```

## YAML Schema Reference

### Valid Configuration Example

```yaml
channels:
  working:          # Channel name: snake_case required
    ttl_sec: 14400  # Required: 60-604800 (1 min to 7 days)
    encrypt: true   # Optional: true/false (default: false)
    quota_bytes: 1000000  # Optional: 1 to 1,000,000,000 bytes

  procedure:
    ttl_sec: 604800
    encrypt: true

  routing:
    ttl_sec: 86400
    encrypt: false
```

### Validation Rules

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `ttl_sec` | `integer` | ✅ Yes | 60 ≤ value ≤ 604,800 |
| `encrypt` | `boolean` | ❌ No | `true` or `false` (default: `false`) |
| `quota_bytes` | `integer` | ❌ No | 1 ≤ value ≤ 1,000,000,000 |

### Channel Name Rules

- ✅ **Valid**: `working`, `procedure`, `routing`, `debug_logs`, `user_context`
- ❌ **Invalid**: `Working`, `user-context`, `123channel`, `admin`, `system`

**Pattern**: `^[a-z][a-z0-9_]*$` (start with lowercase letter, followed by letters/numbers/underscores)

### Reserved Names (Not Allowed)

- `admin` - Administrative functions
- `system` - System-level operations  
- `internal` - Internal processing
- `redis` - Redis operations
- `audit` - Audit logging

## Error Examples

### Invalid Channel Name
```yaml
channels:
  Invalid-Channel:  # ❌ Hyphens not allowed
    ttl_sec: 14400
```
**Error**: `Channel name must be snake_case ([a-z][a-z0-9_]*)`

### TTL Out of Range
```yaml
channels:
  working:
    ttl_sec: 999999  # ❌ Over 7 days
```
**Error**: `TTL cannot exceed 604800 seconds (7 days)`

### Missing Required Field
```yaml
channels:
  working:
    encrypt: true  # ❌ Missing ttl_sec
```
**Error**: `Channel 'working' missing required field 'ttl_sec'`

### Unknown Field
```yaml
channels:
  working:
    ttl_sec: 14400
    unknown_field: "value"  # ❌ Not recognized
```
**Error**: `Channel 'working' has unknown fields: unknown_field`

### Reserved Name
```yaml
channels:
  admin:  # ❌ Reserved name
    ttl_sec: 3600
```
**Error**: `Channel name 'admin' is reserved`

## Migration Guide

### From Legacy Configuration

If you have existing `channels.yaml` files that don't pass strict validation:

1. **Check channel names**: Convert `camelCase` or `kebab-case` to `snake_case`
2. **Verify TTL values**: Ensure they're between 60 and 604,800 seconds
3. **Remove unknown fields**: Only `ttl_sec`, `encrypt`, and `quota_bytes` are allowed
4. **Avoid reserved names**: Rename channels using `admin`, `system`, etc.

### Gradual Migration

```python
# Phase 1: Disable strict validation temporarily
memory = AIMemory(
    channels_yaml="legacy_channels.yaml",
    strict_yaml_validation=False
)

# Phase 2: Fix configuration issues
# Phase 3: Enable strict validation
memory = AIMemory(
    channels_yaml="fixed_channels.yaml", 
    strict_yaml_validation=True
)
```

## CLI Tools

### Generate Schema Documentation

```python
from nexamem.channels import generate_yaml_schema_docs

print(generate_yaml_schema_docs())
```

### Validate Configuration File

```python
from nexamem.channels import validate_yaml_schema

try:
    validate_yaml_schema("your_channels.yaml")
    print("✅ Configuration is valid!")
except Exception as e:
    print(f"❌ Validation failed: {e}")
```

## Benefits

1. **Early Error Detection**: Catch configuration issues before runtime
2. **Consistent Standards**: Enforce naming and structure conventions
3. **Security**: Prevent reserved name conflicts and invalid configurations  
4. **Documentation**: Clear schema serves as living documentation
5. **IDE Support**: Better autocomplete and validation in IDEs that support JSON Schema
6. **Team Collaboration**: Consistent configuration format across teams

## Future Enhancements

- JSON Schema export for IDE integration
- Configuration validation in CI/CD pipelines
- Auto-completion support for popular editors
- Configuration migration tools
- Real-time validation in configuration UIs
