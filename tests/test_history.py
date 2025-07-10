import pytest
from nexamem import initialize, ChatHistory
import os

def test_add_and_get_history():
    history = ChatHistory()
    history.add_message('user', 'Hello!')
    history.add_message('bot', 'Hi!')
    messages = history.get_history()
    assert len(messages) == 2
    assert messages[0]['role'] == 'user'
    assert messages[0]['content'] == 'Hello!'
    assert 'chat_id' in messages[0]
    assert 'data' in messages[0]
    assert messages[1]['role'] == 'bot'
    assert messages[1]['content'] == 'Hi!'
    assert 'chat_id' in messages[1]
    assert 'data' in messages[1]

def test_clear_history():
    history = ChatHistory()
    history.add_message('user', 'Hello!')
    history.clear()
    assert len(history.get_history()) == 0

def test_add_and_get_history_debug(capsys):
    initialize({"history_storage": "memory", "debug": True})
    history = ChatHistory()
    history.add_message('user', 'Hello!')
    history.add_message('bot', 'Hi!')
    out = capsys.readouterr().out
    assert "[DEBUG]" in out
    messages = history.get_history()
    assert len(messages) == 2
    assert messages[0]['role'] == 'user'
    assert messages[0]['content'] == 'Hello!'
    assert 'chat_id' in messages[0]
    assert 'data' in messages[0]
    assert messages[1]['role'] == 'bot'
    assert messages[1]['content'] == 'Hi!'
    assert 'chat_id' in messages[1]
    assert 'data' in messages[1]

def test_clear_history_debug(capsys):
    initialize({"history_storage": "memory", "debug": True})
    history = ChatHistory()
    history.add_message('user', 'Hello!')
    history.clear()
    out = capsys.readouterr().out
    assert "[DEBUG] Cleared history." in out
    assert history.get_history() == []

def test_file_storage_debug(tmp_path, capsys):
    file_path = tmp_path / "chat.json"
    initialize({"history_storage": "file", "file_path": str(file_path), "debug": True})
    history = ChatHistory()
    history.add_message('user', 'File test')
    out = capsys.readouterr().out
    assert "[DEBUG] Saved" in out or "[DEBUG] Loaded" in out
    # File storage now includes chat_id in filename
    # Check for any JSON file in the directory
    json_files = list(tmp_path.glob("*.json"))
    assert len(json_files) == 1
    assert history.get_history()[0]['content'] == 'File test'
    history.clear()
    assert history.get_history() == []

def test_sqlite_storage_debug(tmp_path, capsys):
    sqlite_path = tmp_path / "chat.db"
    initialize({"history_storage": "sqlite", "sqlite_path": str(sqlite_path), "debug": True})
    history = ChatHistory()
    history.add_message('user', 'SQLite test')
    out = capsys.readouterr().out
    assert "[DEBUG] Saved message to SQLite" in out
    assert history.get_history()[0]['content'] == 'SQLite test'
    history.clear()
    assert len(history.get_history()) == 0
    out = capsys.readouterr().out
    assert "[DEBUG] Cleared SQLite chat history for chat_id" in out

def test_query_sqlite_debug(tmp_path, capsys):
    sqlite_path = tmp_path / "chat.db"
    initialize({"history_storage": "sqlite", "sqlite_path": str(sqlite_path), "debug": True})
    history = ChatHistory()
    history.add_message('user', 'A')
    history.add_message('bot', 'B')
    results = history.query_sqlite("role = ?", ("user",))
    out = capsys.readouterr().out
    assert "[DEBUG] query_sqlite returned" in out
    assert results[0]['role'] == 'user'
    assert results[0]['content'] == 'A'

def test_get_message_at_memory():
    initialize({"history_storage": "memory"})
    history = ChatHistory()
    history.add_message('user', 'First')
    history.add_message('bot', 'Second')
    msg0 = history.get_message_at(0)
    msg1 = history.get_message_at(1)
    assert msg0['role'] == 'user'
    assert msg0['content'] == 'First'
    assert 'chat_id' in msg0
    assert 'data' in msg0
    assert msg1['role'] == 'bot'
    assert msg1['content'] == 'Second'
    assert 'chat_id' in msg1
    assert 'data' in msg1
    with pytest.raises(IndexError):
        history.get_message_at(2)

def test_get_message_at_file(tmp_path):
    file_path = tmp_path / "chat.json"
    initialize({"history_storage": "file", "file_path": str(file_path)})
    history = ChatHistory()
    history.add_message('user', 'File1')
    history.add_message('bot', 'File2')
    msg0 = history.get_message_at(0)
    msg1 = history.get_message_at(1)
    assert msg0['role'] == 'user'
    assert msg0['content'] == 'File1'
    assert 'chat_id' in msg0
    assert 'data' in msg0
    assert msg1['role'] == 'bot'
    assert msg1['content'] == 'File2'
    assert 'chat_id' in msg1
    assert 'data' in msg1
    with pytest.raises(IndexError):
        history.get_message_at(2)

def test_get_message_at_sqlite(tmp_path):
    sqlite_path = tmp_path / "chat.db"
    initialize({"history_storage": "sqlite", "sqlite_path": str(sqlite_path)})
    history = ChatHistory()
    history.add_message('user', 'SQL1')
    history.add_message('bot', 'SQL2')
    msg0 = history.get_message_at(0)
    msg1 = history.get_message_at(1)
    assert msg0['role'] == 'user'
    assert msg0['content'] == 'SQL1'
    assert 'chat_id' in msg0
    assert 'data' in msg0
    assert msg1['role'] == 'bot'
    assert msg1['content'] == 'SQL2'
    assert 'chat_id' in msg1
    assert 'data' in msg1
    with pytest.raises(IndexError):
        history.get_message_at(2)
