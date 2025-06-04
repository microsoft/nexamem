# NexaMem

A simple Python package to store and manage AI memory. Designed for easy integration with Python projects.

## Features
- Store, retrieve, and manage chatbot conversation history
- Simple API for integration with LLM-based chatbots

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
