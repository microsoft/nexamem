# NexaMem / AIMemory

A Python library providing governed, Redis-backed conversational memory for AI components. Designed for easy integration with AI agents, orchestrators, and chatbot systems.

## Features

### AIMemory API (Recommended) - v0.3
- **Redis-backed channels** with user-defined configuration
- **Sync and async client classes** for high-performance applications  
- **YAML channel configuration** with TTL, encryption, and quota settings
- **Policy enforcement** for TTL, PII detection, and quota management
- **Scope-based access control** with environment isolation
- **Dynamic channel registration** for runtime flexibility
- **Checkpoint operations** for workflow state management
- **Content processing chain** with PII detection/redaction
- **Audit logging** to Redis Stream for compliance
- **Base metrics capturing** for monitoring and observability

### Legacy ChatHistory API
- Store, retrieve, and manage chatbot conversation history
- Multiple storage backends: Memory, File, SQLite, and Redis
- Simple API for integration with LLM-based chatbots

## Installation

```sh
pip install nexamem

# Development/testing
pip install -i https://test.pypi.org/simple/ nexamem
```

### Or from GitHub

```sh
pip install git+https://github.com/microsoft/nexamem.git
uv add git+https://github.com/microsoft/nexamem.git  
```

## Quick Start - AIMemory (Recommended)

The new AIMemory API provides enterprise-grade conversational memory:

```python
from nexamem import AIMemory, MemoryScope

# Initialize with Redis (or fakeredis for testing)
memory = AIMemory(
    redis_host="localhost",
    redis_port=6379,
    channels_yaml="channels.yaml",  # Optional: load channel config
    use_fakeredis=True,  # For testing
    enable_audit=True,
    enable_metrics=True,
    enable_content_processing=True
)

# Create a memory scope (defines access control)
scope = MemoryScope(
    agent_id="investment_agent",
    user_id="user_12345",
    session_id="session_abc123",
    env="prod"  # Environment isolation
)

# Write to a channel
message_uuid = memory.write(
    scope=scope,
    channel="working",
    content="User asked about portfolio diversification",
    auto_pii=True  # Auto-detect and handle PII
)

# Read from a channel
messages, metadata = memory.read(
    scope=scope,
    channel="working",
    max_msgs=10,
    since_sec=3600  # Last hour only
)

print(f"Retrieved {len(messages)} messages")
```

### Channel Configuration (channels.yaml)

Define your channels with specific policies:

```yaml
channels:
  working:          # Recent dialogue
    ttl_sec: 14400  # 4 hours
    encrypt: true
    quota_bytes: 1000000  # 1MB daily quota

  procedure:        # Workflow checkpoints  
    ttl_sec: 604800 # 7 days
    encrypt: true

  routing:          # Breadcrumbs, classifier hints
    ttl_sec: 86400  # 24 hours
    encrypt: false
```

### Enhanced Features

```python
# Dynamic channel registration
memory.register_channel(
    name="debug_logs",
    ttl_sec=3600,      # 1 hour
    encrypt=False,
    quota_bytes=500000  # 500KB
)

# Checkpoint operations for workflow state
memory.checkpoint(scope, "workflow_state", {
    "current_step": "risk_assessment",
    "completed_steps": ["onboarding", "kyc"],
    "progress": 0.6
})

# Atomic updates
def advance_step(current_state):
    return {"step": current_state["step"] + 1}

updated = memory.checkpoint_atomic(scope, "counter", advance_step)

# Metrics and audit
metrics_data = memory.metrics.get_all_metrics()
audit_records = memory.audit.get_audit_records(count=10)
```

## Legacy ChatHistory API

The original simple API is still supported for backward compatibility:

```python
from nexamem import initialize, get_config, ChatHistory

# Initialize with your preferred storage
initialize({
    "history_storage": "memory",
    "debug": True  # Optional: enable debug output
})

# Example: File-based storage
initialize({
    "history_storage": "file",
    "file_path": "./chat_history.json",
    "debug": False
})

# Example: SQLite storage
initialize({
    "history_storage": "sqlite",
    "sqlite_path": "./chat_history.db",
    "debug": False
})

print(get_config())  # View current configuration

history = ChatHistory()
history.add_message('user', 'Hello!')
history.add_message('bot', 'Hi! How can I help you?')
print(history.get_history())
```

### Configuration Options

- `history_storage` (str, required): Storage backend. One of `'memory'`, `'file'`, or `'sqlite'`.
- `file_path` (str, required if `history_storage='file'`): Path to the JSON file for storing history.
- `sqlite_path` (str, required if `history_storage='sqlite'`): Path to the SQLite database file.
- `debug` (bool, optional): Enable debug output (default: `False`).

### API Methods

- `initialize(config: dict)`: Initialize the library with configuration.
- `get_config() -> dict`: Get the current configuration.
- `ChatHistory.add_message(role: str, content: str)`: Add a message to the history.
- `ChatHistory.get_history() -> list`: Retrieve the conversation history.
- `ChatHistory.clear()`: Clear the conversation history.
- `ChatHistory.query_sqlite(where: str = "", params: tuple = ()) -> list`: Query SQLite history (only if using SQLite backend).
- `ChatHistory.get_message_at(index: int) -> dict`: Retrieve the message at the specified index in the conversation history. Raises `IndexError` if out of range.

## Development

1. Create a virtual environment:
   ```sh
   python -m venv .venv
   ```
2. Activate the virtual environment:
   - On Windows:
     ```sh
     .venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```sh
     source .venv/bin/activate
     ```
3. Install dependencies:
   ```sh
   pip install -e .
   pip install -r requirements.txt
   ```

## Testing

```sh
pytest
```

## Building a Binary Distribution

To build a binary wheel (for manual installation or distribution):

1. Make sure you have the latest build tools:
   ```sh
   pip install --upgrade build
   ```
2. Build the wheel file:
   ```sh
   python -m build --wheel
   ```
   This will create a `.whl` file in the `dist/` directory.
3. (Optional) Install the built wheel manually:
   ```sh
   pip install dist/nexamem-*.whl
   ```

For more details, see the [Python Packaging User Guide](https://packaging.python.org/tutorials/packaging-projects/).

## License

This project is licensed under the MIT License.
