# Unit Tests for Class and Method Existence

This directory contains unit tests that verify the existence of classes, methods, enums, and values in the nexamem package. These tests ensure that the public API remains stable and all expected components are present.

## Test Files

### `test_class_method_existence.py`
Comprehensive tests for:
- **Package Structure**: Verifies `__version__` and `__all__` exports
- **Core Classes**: Tests existence of `AIMemory`, `AsyncAIMemory`, `MemoryScope`, `ChatHistory`
- **Channel Management**: Tests `ChannelConfig`, `ChannelManager`, and related exceptions
- **Policy Engine**: Tests `PolicyEngine`, `PIIDetector`, and policy exceptions
- **Content Processing**: Tests `ContentProcessorChain`, `PIIRedactor`, `ContentEnricher`
- **Audit System**: Tests `AuditSink` and `AsyncAuditSink`
- **Metrics**: Tests metrics module structure
- **Method Signatures**: Validates method parameters and async methods
- **Import Compatibility**: Ensures all symbols can be imported correctly

### `test_enums_and_constants.py`
Focused tests for:
- **Constants and Enums**: PII detection patterns, default values, limits
- **Validation Constants**: TTL limits (60s min, 7 days max), quota limits (1GB max)
- **Reserved Names**: Tests for reserved channel names (`admin`, `system`, etc.)
- **Exception Hierarchies**: Validates inheritance relationships
- **Default Values**: Environment defaults, stream names, connection parameters
- **Pattern Validation**: Snake_case naming patterns, regex validation

## Key Components Tested

### Classes
- `AIMemory` and `AsyncAIMemory` - Main memory management classes
- `MemoryScope` - Key structure for memory operations  
- `ChannelConfig` and `ChannelManager` - Channel configuration management
- `PolicyEngine` and `PIIDetector` - Policy enforcement and PII detection
- `ContentProcessorChain`, `PIIRedactor`, `ContentEnricher` - Content processing
- `AuditSink` and `AsyncAuditSink` - Audit logging
- `ChatHistory` and `Message` - Legacy history management

### Methods
- **AIMemory**: `write`, `read`, `checkpoint`, `bulk_erase`, `count_bytes`, etc.
- **MemoryScope**: `get_key_prefix`, `get_index_key`, `model_dump_dict`
- **PolicyEngine**: `validate_write`, `post_write_update`
- **PIIDetector**: `detect_pii`, `has_pii`
- **Content processors**: `process` method for all processors

### Constants and Enums
- **PII Patterns**: `email`, `phone`, `ssn`, `credit_card` regex patterns
- **Validation Limits**: TTL ranges, quota bytes, name length limits
- **Reserved Names**: System-reserved channel names
- **Default Values**: Environment (`prod`), ports (6379), database (0)

### Exception Hierarchies
- `PolicyViolation` → `QuotaExceeded`, `EncryptionRequired`, `TTLViolation`
- `AIMemoryError` → `ChannelNotFound`
- `ChannelAlreadyExists`, `YamlSchemaError`, `ConfigError`, `RedisConnectionError`

## Running the Tests

```bash
# Run all existence tests
python -m pytest tests/test_class_method_existence.py -v

# Run constants and enums tests
python -m pytest tests/test_enums_and_constants.py -v

# Run a specific test class
python -m pytest tests/test_class_method_existence.py::TestAIMemoryClass -v

# Run a specific test
python -m pytest tests/test_enums_and_constants.py::TestEnumsAndConstants::test_pii_detector_patterns_constants -v
```

## Test Coverage

These tests provide comprehensive coverage of:
- ✅ All public classes and their existence
- ✅ All public methods and their signatures  
- ✅ All exception classes and inheritance
- ✅ All constants, patterns, and default values
- ✅ Package structure and exports
- ✅ Import compatibility across modules
- ✅ Async method detection
- ✅ Validation limits and patterns

## Purpose

These tests serve as:
1. **API Stability Checks**: Ensure no breaking changes to public interface
2. **Documentation**: Living documentation of the package structure
3. **Regression Tests**: Catch unintended removal of classes/methods
4. **Contract Validation**: Verify the package provides expected functionality

The tests focus on *existence* rather than *functionality* - they verify that components are present and have the expected structure without testing their actual behavior.
