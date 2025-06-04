from typing import List, Dict
import os
import json
import sqlite3
from pydantic import BaseModel
from .config import get_config, ConfigError

class Message(BaseModel):
    role: str
    content: str

class ChatHistory:
    """
    Stores and manages NexaMem chatbot conversation history using Pydantic models.
    Supports in-memory, file, and SQLite storage based on configuration.
    """
    def __init__(self):
        config = get_config()
        if not config:
            raise ConfigError("NexaMem must be initialized before using ChatHistory.")
        self._storage = config["history_storage"]
        self._debug = config.get("debug", False)
        self._history: List[Message] = []
        if self._storage == "file":
            self._file_path = config["file_path"]
            self._load_from_file()
        elif self._storage == "sqlite":
            self._sqlite_path = config["sqlite_path"]
            self._init_sqlite()
            self._load_from_sqlite()
        if self._debug:
            print(f"[DEBUG] ChatHistory initialized with storage='{self._storage}'")

    def add_message(self, role: str, content: str):
        msg = Message(role=role, content=content)
        if self._storage == "memory":
            self._history.append(msg)
        elif self._storage == "file":
            self._history.append(msg)
            self._save_to_file()
        elif self._storage == "sqlite":
            self._save_to_sqlite(msg)
        if self._debug:
            print(f"[DEBUG] Added message: role='{role}' content='{content}'")

    def get_history(self) -> List[Dict[str, str]]:
        if self._storage == "sqlite":
            self._load_from_sqlite()
        if self._debug:
            print(f"[DEBUG] get_history called. Returning {len(self._history)} messages.")
        return [msg.model_dump() for msg in self._history]

    def clear(self):
        self._history.clear()
        if self._storage == "file":
            self._save_to_file()
        elif self._storage == "sqlite":
            self._clear_sqlite()
        if self._debug:
            print("[DEBUG] Cleared history.")

    def get_message_at(self, index: int) -> Dict[str, str]:
        """
        Get the message at the specified index in the history.

        Args:
            index (int): The index of the message to retrieve.
        Returns:
            Dict[str, str]: The message as a dictionary.
        Raises:
            IndexError: If the index is out of range.
        """
        if self._storage == "sqlite":
            self._load_from_sqlite()
        if index < 0 or index >= len(self._history):
            raise IndexError(f"Message index {index} out of range.")
        if self._debug:
            print(f"[DEBUG] get_message_at called for index={index}.")
        return self._history[index].model_dump()

    # --- File storage helpers ---
    def _load_from_file(self):
        if os.path.exists(self._file_path):
            with open(self._file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._history = [Message(**msg) for msg in data]
            if self._debug:
                print(f"[DEBUG] Loaded {len(self._history)} messages from file '{self._file_path}'")
        else:
            self._history = []
            if self._debug:
                print(f"[DEBUG] No history file found at '{self._file_path}'. Starting with empty history.")

    def _save_to_file(self):
        with open(self._file_path, "w", encoding="utf-8") as f:
            json.dump([msg.model_dump() for msg in self._history], f, ensure_ascii=False, indent=2)
        if self._debug:
            print(f"[DEBUG] Saved {len(self._history)} messages to file '{self._file_path}'")

    # --- SQLite storage helpers ---
    def _init_sqlite(self):
        self._conn = sqlite3.connect(self._sqlite_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL
            )
            """
        )
        self._conn.commit()
        if self._debug:
            print(f"[DEBUG] Initialized SQLite database at '{self._sqlite_path}'")

    def _save_to_sqlite(self, msg: Message):
        self._conn.execute(
            "INSERT INTO chat_history (role, content) VALUES (?, ?)",
            (msg.role, msg.content)
        )
        self._conn.commit()
        if self._debug:
            print(f"[DEBUG] Saved message to SQLite: role='{msg.role}' content='{msg.content}'")

    def _load_from_sqlite(self):
        self._history = []
        cursor = self._conn.execute("SELECT role, content FROM chat_history ORDER BY id ASC")
        for row in cursor:
            self._history.append(Message(role=row[0], content=row[1]))
        if self._debug:
            print(f"[DEBUG] Loaded {len(self._history)} messages from SQLite database.")

    def _clear_sqlite(self):
        self._conn.execute("DELETE FROM chat_history")
        self._conn.commit()
        self._history = []
        if self._debug:
            print("[DEBUG] Cleared SQLite chat history table.")

    def query_sqlite(self, where: str = "", params: tuple = ()) -> list:
        """
        Query the SQLite chat history table with a custom WHERE clause.

        Args:
            where (str): SQL WHERE clause (without the 'WHERE' keyword). Optional.
            params (tuple): Parameters to safely substitute into the WHERE clause. Optional.
        Returns:
            list: List of dictionaries representing the matching messages.
        Raises:
            ConfigError: If not using SQLite storage.
        """
        if self._storage != "sqlite":
            raise ConfigError("query_sqlite is only available when using SQLite storage.")
        query = "SELECT role, content FROM chat_history"
        if where:
            query += f" WHERE {where}"
        query += " ORDER BY id ASC"
        cursor = self._conn.execute(query, params)
        results = [dict(role=row[0], content=row[1]) for row in cursor]
        if self._debug:
            print(f"[DEBUG] query_sqlite returned {len(results)} messages with where='{where}' and params={params}")
        return results
