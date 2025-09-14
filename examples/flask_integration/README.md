# Flask + NexaMem Integration Example

This example demonstrates how to integrate NexaMem into a Flask application for conversational memory management.

## Features

- **Conversation Turn Storage**: Store user and assistant messages
- **History Retrieval**: Get conversation history with configurable limits
- **Search Functionality**: Search across all conversations
- **Summary Creation**: Store conversation summaries
- **Health Monitoring**: Health check endpoint
- **Flexible Storage**: Support for in-memory, Redis, and other backends

## Quick Start

### 1. Install Dependencies

```bash
# Install NexaMem from parent directory
pip install -e ../..

# Install Flask dependencies
pip install -r requirements.txt
```

### 2. Run with In-Memory Storage (Development)

```bash
python app.py
```

The server will start on `http://localhost:5000`

### 3. Run with Azure Redis (Production)

```bash
export NEXAMEM_SERVICE_TYPE=azure_redis
export AZURE_REDIS_HOSTNAME=your-cache.redis.cache.windows.net
export AZURE_REDIS_ACCESS_KEY=your-access-key

python app.py
```

## API Endpoints

### Add Conversation Turn
```bash
POST /conversation/{conversation_id}/turn

{
  "content": "Hello, how can I help you today?",
  "user_id": "user123",
  "turn_type": "assistant",
  "metadata": {
    "intent": "greeting",
    "confidence": 0.95
  }
}
```

### Get Conversation History
```bash
GET /conversation/{conversation_id}/history?limit=10
```

### Search Conversations
```bash
GET /conversations/search?q=python&limit=5
```

### Create Conversation Summary
```bash
POST /conversation/{conversation_id}/summary

{
  "summary": "User asked about Python best practices. Provided recommendations on code style, testing, and documentation."
}
```

### Health Check
```bash
GET /health
```

## Example Usage

```python
import requests

base_url = "http://localhost:5000"

# Add a conversation turn
response = requests.post(f"{base_url}/conversation/chat123/turn", json={
    "content": "What are Python best practices?",
    "user_id": "user456",
    "turn_type": "user"
})
print(response.json())

# Get conversation history
response = requests.get(f"{base_url}/conversation/chat123/history")
print(response.json())

# Search conversations
response = requests.get(f"{base_url}/conversations/search?q=Python")
print(response.json())
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXAMEM_SERVICE_TYPE` | Storage backend type | `memory` |
| `AZURE_REDIS_HOSTNAME` | Azure Redis hostname | - |
| `AZURE_REDIS_ACCESS_KEY` | Azure Redis access key | - |
| `AZURE_REDIS_PORT` | Azure Redis port | `6380` |
| `AZURE_REDIS_SSL` | Use SSL for Redis | `true` |
| `PORT` | Flask server port | `5000` |
| `FLASK_DEBUG` | Enable Flask debug mode | `true` |

### Storage Backends

#### In-Memory (Development)
```bash
export NEXAMEM_SERVICE_TYPE=memory
```

#### Azure Redis (Production)
```bash
export NEXAMEM_SERVICE_TYPE=azure_redis
export AZURE_REDIS_HOSTNAME=your-cache.redis.cache.windows.net
export AZURE_REDIS_ACCESS_KEY=your-access-key
```

#### File Storage (Persistence without Redis)
```bash
export NEXAMEM_SERVICE_TYPE=file
export NEXAMEM_FILE_PATH=./conversation_data
```

#### SQLite (Local database)
```bash
export NEXAMEM_SERVICE_TYPE=sqlite
export NEXAMEM_SQLITE_PATH=./conversations.db
```

## Production Deployment

### Using Gunicorn

```bash
# Install gunicorn
pip install gunicorn

# Run with multiple workers
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]
```

### Environment-specific Configuration

Create `.env` files for different environments:

```bash
# .env.development
NEXAMEM_SERVICE_TYPE=memory
FLASK_DEBUG=true

# .env.production
NEXAMEM_SERVICE_TYPE=azure_redis
AZURE_REDIS_HOSTNAME=prod-cache.redis.cache.windows.net
AZURE_REDIS_ACCESS_KEY=${AZURE_REDIS_ACCESS_KEY}
FLASK_DEBUG=false
```

## Integration Patterns

### Dependency Injection (Flask-Injector)

```python
from flask_injector import FlaskInjector, inject
from nexamem import IConversationMemory, create_conversation_memory

def configure_dependencies(binder):
    memory_service = create_conversation_memory(service_type="azure_redis")
    binder.bind(IConversationMemory, to=memory_service)

@app.route("/conversation/<conversation_id>/turn", methods=["POST"])
@inject
def add_turn(conversation_id: str, memory: IConversationMemory):
    # Use injected memory service
    pass

FlaskInjector(app=app, modules=[configure_dependencies])
```

### Application Factory Pattern

```python
def create_app(config_name='development'):
    app = Flask(__name__)
    
    # Initialize memory service based on config
    if config_name == 'production':
        memory_service = create_conversation_memory(
            service_type="azure_redis",
            config=app.config['NEXAMEM_CONFIG']
        )
    else:
        memory_service = create_conversation_memory(service_type="memory")
    
    app.memory_service = memory_service
    
    return app
```

## Testing

```python
import pytest
from app import create_app

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_add_conversation_turn(client):
    response = client.post('/conversation/test123/turn', json={
        'content': 'Test message',
        'user_id': 'test_user'
    })
    assert response.status_code == 200
    assert response.json['success'] is True
```

## Next Steps

- Add authentication middleware
- Implement rate limiting
- Add input validation with marshmallow/pydantic
- Add async Flask support with Quart
- Implement conversation analytics
- Add real-time updates with WebSockets

This example provides a solid foundation for integrating NexaMem into Flask applications with production-ready patterns and extensibility.