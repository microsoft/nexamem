import pytest
from nexamem import initialize, ChatHistory
import os

def test_add_and_get_history():
    history = ChatHistory()
    history.add_message('user', 'Hello!')
    history.add_message('bot', 'Hi!')
    assert history.get_history() == [
        {'role': 'user', 'content': 'Hello!'},
        {'role': 'bot', 'content': 'Hi!'}
    ]

def test_clear_history():
    history = ChatHistory()
    history.add_message('user', 'Hello!')
    history.clear()
    assert history.get_history() == []

def test_add_and_get_history_debug(capsys):
    initialize({"history_storage": "memory", "debug": True})
    history = ChatHistory()
    history.add_message('user', 'Hello!')
    history.add_message('bot', 'Hi!')
    out = capsys.readouterr().out
    assert "[DEBUG]" in out
    assert history.get_history() == [
        {'role': 'user', 'content': 'Hello!'},
        {'role': 'bot', 'content': 'Hi!'}
    ]

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
    assert os.path.exists(file_path)
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
    assert history.get_history() == []
    out = capsys.readouterr().out
    assert "[DEBUG] Cleared SQLite chat history table." in out

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
    assert history.get_message_at(0) == {'role': 'user', 'content': 'First'}
    assert history.get_message_at(1) == {'role': 'bot', 'content': 'Second'}
    with pytest.raises(IndexError):
        history.get_message_at(2)

def test_get_message_at_file(tmp_path):
    file_path = tmp_path / "chat.json"
    initialize({"history_storage": "file", "file_path": str(file_path)})
    history = ChatHistory()
    history.add_message('user', 'File1')
    history.add_message('bot', 'File2')
    assert history.get_message_at(0) == {'role': 'user', 'content': 'File1'}
    assert history.get_message_at(1) == {'role': 'bot', 'content': 'File2'}
    with pytest.raises(IndexError):
        history.get_message_at(2)

def test_get_message_at_sqlite(tmp_path):
    sqlite_path = tmp_path / "chat.db"
    initialize({"history_storage": "sqlite", "sqlite_path": str(sqlite_path)})
    history = ChatHistory()
    history.add_message('user', 'SQL1')
    history.add_message('bot', 'SQL2')
    assert history.get_message_at(0) == {'role': 'user', 'content': 'SQL1'}
    assert history.get_message_at(1) == {'role': 'bot', 'content': 'SQL2'}
    with pytest.raises(IndexError):
        history.get_message_at(2)
