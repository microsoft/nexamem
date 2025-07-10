# NexaMem

A simple Python package to store and manage AI memory. Designed for easy integration with Python projects.

## Features
- Store, retrieve, and manage chatbot conversation history
- Multiple storage backends: Memory, File, SQLite, and Redis (including Azure Redis Cache)
- Simple API for integration with LLM-based chatbots
- Azure Redis Cache support for scalable, distributed applications

## Installation

```sh
pip install nexamem

(FOR TESTING)
pip install -i https://test.pypi.org/simple/ nexamem
```

### OR with GitHub

```sh
pip install git+https://github.com/microsoft/nexamem.git

uv add git+https://github.com/microsoft/nexamem.git  
```

### OR with GitHub branch?

```sh
pip install git+https://github.com/microsoft/nexamem.git@branch_or_tag_name

uv add git+https://github.com/microsoft/nexamem.git@branch_or_tag_name
```

## Usage

Before using NexaMem, initialize the configuration with your preferred storage backend:

```python
from nexamem import initialize, get_config, ChatHistory

# Example: In-memory storage (default)
initialize({
    "history_storage": "memory",
    "chat_id": "my-chat-session",  # Optional: specify chat ID
    "debug": True  # Optional: enable debug output
})

# Example: File-based storage with auto-generated chat ID
initialize({
    "history_storage": "file",
    "file_path": "./chat_history.json",
    # chat_id will be auto-generated if not provided
    "debug": False
})

# Example: SQLite storage with specific chat ID
initialize({
    "history_storage": "sqlite",
    "sqlite_path": "./chat_history.db",
    "chat_id": "session-abc123",  # Optional: custom chat ID
    "debug": False
})

# Example: Redis storage (local development)
initialize({
    "history_storage": "redis",
    "redis_host": "localhost",
    "redis_port": 6379,
    "redis_ssl": False,
    "redis_db": 0,
    "redis_key_prefix": "nexamem:",
    "chat_id": "user-456-session",  # Optional: specify chat ID
    "debug": False
})

# Example: Azure Redis Cache (production)
initialize({
    "history_storage": "redis",
    "redis_host": "your-cache.redis.cache.windows.net",
    "redis_port": 6380,  # Azure Redis default SSL port
    "redis_password": "your-redis-access-key",
    "redis_ssl": True,   # Azure Redis requires SSL
    "redis_db": 0,
    "redis_key_prefix": "myapp:",
    "debug": False
})

# Example: Azure Redis Cache with Microsoft Entra ID (recommended)
initialize({
    "history_storage": "redis",
    "redis_host": "your-cache.redis.cache.windows.net",
    "redis_port": 6380,
    "redis_ssl": True,
    "redis_auth_method": "entra_id",  # Use Entra ID instead of access keys
    "redis_key_prefix": "myapp:",
    "debug": False
})

print(get_config())  # View current configuration

history = ChatHistory()
print(f"Chat ID: {history.get_chat_id()}")  # Get the current chat ID
history.add_message('user', 'Hello!')
history.add_message('bot', 'Hi! How can I help you?')
print(history.get_history())
```

### Configuration Options

#### Storage Backend Options
- `history_storage` (str, required): Storage backend. One of `'memory'`, `'file'`, `'sqlite'`, or `'redis'`.
- `chat_id` (str, optional): Unique identifier for this chat session. Auto-generated UUID if not provided.

#### File Storage Options
- `file_path` (str, required if `history_storage='file'`): Path to the JSON file for storing history.

#### SQLite Storage Options  
- `sqlite_path` (str, required if `history_storage='sqlite'`): Path to the SQLite database file.

#### Redis Storage Options
- `redis_host` (str, required if `history_storage='redis'`): Redis server hostname.
- `redis_port` (int, optional): Redis server port. Defaults to 6380 (Azure Redis default).
- `redis_password` (str, optional): Redis password/access key. Required for access key authentication.
- `redis_ssl` (bool, optional): Use SSL connection. Defaults to True (recommended for Azure).
- `redis_db` (int, optional): Redis database number. Defaults to 0.
- `redis_key_prefix` (str, optional): Prefix for Redis keys. Defaults to "nexamem:".
- `redis_auth_method` (str, optional): Authentication method - "access_key" or "entra_id". Defaults to "access_key".
- `redis_entra_scope` (str, optional): Microsoft Entra ID scope. Defaults to Azure Redis scope.

#### General Options
- `debug` (bool, optional): Enable debug output (default: `False`).

### Chat ID Management

Each chat session is identified by a unique `chat_id`. This allows you to manage multiple separate conversations:

- **Auto-generation**: If no `chat_id` is provided, a UUID4 is automatically generated
- **Manual specification**: Provide a custom `chat_id` string for predictable session management
- **Storage separation**: Different storage backends handle chat separation as follows:
  - **Memory**: Each ChatHistory instance maintains its own in-memory data
  - **File**: Chat ID is appended to the filename (e.g., `chat_history_abc123.json`)
  - **SQLite**: Chat messages are stored with a `chat_id` column for separation
  - **Redis**: Chat ID is included in the Redis key structure (`nexamem:history:chat_id`)

```python
# Example: Managing multiple chats
initialize({"history_storage": "sqlite", "sqlite_path": "./chats.db", "chat_id": "customer-support-001"})
support_chat = ChatHistory()

initialize({"history_storage": "sqlite", "sqlite_path": "./chats.db", "chat_id": "customer-support-002"})  
another_chat = ChatHistory()

print(f"Support chat ID: {support_chat.get_chat_id()}")  # customer-support-001
print(f"Another chat ID: {another_chat.get_chat_id()}")   # customer-support-002
```

### API Methods

#### Core Methods
- `initialize(config: dict)`: Initialize the library with configuration.
- `get_config() -> dict`: Get the current configuration.
- `ChatHistory.get_chat_id() -> str`: Get the current chat ID.
- `ChatHistory.add_message(role: str, content: str)`: Add a message to the history.
- `ChatHistory.get_history() -> list`: Retrieve the conversation history.
- `ChatHistory.clear()`: Clear the conversation history.
- `ChatHistory.get_message_at(index: int) -> dict`: Retrieve the message at the specified index in the conversation history. Raises `IndexError` if out of range.

#### Storage-Specific Methods
- `ChatHistory.query_sqlite(where: str = "", params: tuple = ()) -> list`: Query SQLite history (SQLite backend only).
- `ChatHistory.query_redis(pattern: str = None, limit: int = None) -> list`: Query Redis history with optional pattern matching (Redis backend only).
- `ChatHistory.get_redis_info() -> dict`: Get Redis connection info and statistics (Redis backend only).

## Azure Redis Cache Usage

For production applications, Azure Redis Cache provides a scalable, managed Redis service with two authentication methods:

### Option 1: Access Key Authentication
```python
import os
from nexamem import initialize, ChatHistory

# Configure for Azure Redis Cache with access key
initialize({
    "history_storage": "redis",
    "redis_host": "your-cache.redis.cache.windows.net", 
    "redis_port": 6380,
    "redis_password": os.getenv("AZURE_REDIS_ACCESS_KEY"),
    "redis_ssl": True,
    "redis_auth_method": "access_key",  # Default method
    "redis_key_prefix": "myapp:",
    "debug": False
})
```

### Option 2: Microsoft Entra ID Authentication (Recommended)
```python
from nexamem import initialize, ChatHistory

# Configure for Azure Redis Cache with Entra ID
initialize({
    "history_storage": "redis",
    "redis_host": "your-cache.redis.cache.windows.net",
    "redis_port": 6380,
    "redis_ssl": True,
    "redis_auth_method": "entra_id",  # Use Entra ID
    "redis_key_prefix": "myapp:",
    "debug": False
})

history = ChatHistory()

# Redis-specific features work with both authentication methods
info = history.get_redis_info()
print(f"Connected to Redis: {info['host']}:{info['port']}")

# Query messages with pattern matching
matching_messages = history.query_redis(pattern="error", limit=10)
print(f"Found {len(matching_messages)} messages containing 'error'")
```

### Microsoft Entra ID Benefits
- **No shared secrets**: Token-based authentication
- **Centralized identity**: Integrated with Azure AD tenant  
- **Role-based access**: Fine-grained permissions (Redis Data Contributor, etc.)
- **Automatic token refresh**: Handled by azure-identity library
- **Better auditing**: Centralized logging and compliance

### Setting up Azure Redis Cache

#### For Access Key Authentication:
1. Create an Azure Redis Cache instance in the Azure portal
2. Get the hostname (e.g., `your-cache.redis.cache.windows.net`)
3. Get the access key from the "Access keys" section
4. Use port 6380 (SSL) for secure connections
5. Set the `redis_password` to your access key

#### For Microsoft Entra ID Authentication (Recommended):
1. Create an Azure Redis Cache instance
2. Enable "Microsoft Entra Authentication" in the Redis cache settings
3. Assign the "Redis Data Contributor" role to your identity:
   - For development: Your user account (after `az login`)
   - For App Service: Enable Managed Identity and assign role
   - For Service Principal: Create app registration and assign role
4. Configure NexaMem with `redis_auth_method: "entra_id"`

#### Setting up Azure Identity:
```bash
# For local development
az login

# For App Service - enable Managed Identity in portal, then assign Redis Data Contributor role

# For Service Principal - set environment variables:
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"  
export AZURE_TENANT_ID="your-tenant-id"
```

## Examples

Check the `examples/` directory for complete usage examples:
- `azure_redis_example.py` - Azure Redis Cache with access key authentication
- `azure_entra_id_example.py` - Azure Redis Cache with Microsoft Entra ID authentication  
- `local_redis_example.py` - Local Redis development setup
- `redis_demo.py` - Interactive demo using fakeredis

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

## 🎯 Type-Safe Configuration with Enums

NexaMem provides enums for configuration values to improve code clarity and prevent configuration errors:

```python
from nexamem import initialize, ChatHistory, StorageType, RedisAuthMethod

# Type-safe configuration using enums
config = {
    "history_storage": StorageType.REDIS,  # IDE auto-completion!
    "redis_host": "your-cache.redis.cache.windows.net",
    "redis_port": 6380,
    "redis_ssl": True,
    "redis_auth_method": RedisAuthMethod.ENTRA_ID,  # No typos!
    "debug": True
}

initialize(config)
history = ChatHistory()
```

### Available Enums

**StorageType:**
- `StorageType.MEMORY` = "memory"
- `StorageType.FILE` = "file" 
- `StorageType.SQLITE` = "sqlite"
- `StorageType.REDIS` = "redis"

**RedisAuthMethod:**
- `RedisAuthMethod.ACCESS_KEY` = "access_key"
- `RedisAuthMethod.ENTRA_ID` = "entra_id"
- `RedisAuthMethod.AZURE_AD` = "entra_id" (alias)

### Benefits of Using Enums

✅ **IDE Support**: Auto-completion and IntelliSense  
✅ **Type Safety**: Catch configuration errors at development time  
✅ **No Typos**: Enum values prevent spelling mistakes  
✅ **Self-Documenting**: Enum names are clearer than strings  
✅ **Refactoring**: IDE can safely rename enum values  
✅ **Backward Compatible**: String values still work

## License

This project is licensed under the MIT License.
