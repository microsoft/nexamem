# Channel YAML Validation

Channel configuration can be loaded by either API generation. For the new facade, pass settings through `AIMemoryConfig`, not directly as `AIMemory` constructor keywords:

```python
from nexamem import AIMemory, AIMemoryConfig, StorageConfig

memory = AIMemory(
    AIMemoryConfig(
        default_scope="application",
        storage=StorageConfig.memory(),
        channels_yaml="channels.yaml",
        strict_yaml_validation=True,
    )
)
```

## Format

```yaml
channels:
  working:
    ttl_sec: 3600
    encrypt: false
    quota_bytes: 1000000
```

Strict validation checks recognized fields, channel naming, reserved names, and value bounds. TTL is required and must be between 60 and 604800 seconds. When provided, quota must be between 1 and 1000000000 bytes. A configuration must define at least one channel. Runtime registration and non-strict loading are separate paths; do not assume they apply all strict-file checks.

Validate a file independently:

```python
from nexamem.channels import validate_yaml_schema

validated = validate_yaml_schema("channels.yaml")
assert "channels" in validated
```

`YamlSchemaError` reports invalid schema data; file/YAML parsing failures may also raise. `strict_yaml_validation=False` permits the less restrictive compatibility loading path and should be used only for reviewed legacy configuration.

> [!WARNING]
> Channel `ttl_sec` now controls per-record logical expiry in the new facade. This does not guarantee immediate physical erasure, audit/backup deletion, or background cleanup. Validating `encrypt` or `quota_bytes` still does not activate encryption or quota enforcement. See [architecture](NEW_ARCHITECTURE.md) and [security](SECURITY.md).