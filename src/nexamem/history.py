import json
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel, Field

from .config import ConfigError, get_config

class Message(BaseModel):
    role: str
    content: str
    agent_id: str = Field(default="", description="Agent identifier")
    user_id: str = Field(default="", description="User identifier")
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Session UUID")
    env: str = Field(default="prod", description="Environment (dev/stg/prod)")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Timestamp when recorded")
    tokens: int = Field(default=0, description="Number of tokens used by LLM")
    data: str = Field(default="", description="JSON string for additional data")

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
            self._migrate_sqlite_schema()
            self._load_from_sqlite()
        if self._debug:
            print(f"[DEBUG] ChatHistory initialized with storage='{self._storage}'")

    def add_message(self, role: str, content: str, **kwargs):
        """
        Add a message to the chat history.
        
        Args:
            role: Message role (e.g., 'user', 'assistant', 'system')
            content: Message content
            **kwargs: Additional properties (agent_id, user_id, session_id, env, tokens, data)
        """
        msg = Message(role=role, content=content, **kwargs)
        if self._storage == "memory":
            self._history.append(msg)
        elif self._storage == "file":
            self._history.append(msg)
            self._save_to_file()
        elif self._storage == "sqlite":
            self._save_to_sqlite(msg)
        if self._debug:
            print(f"[DEBUG] Added message: role='{role}' content='{content}' agent_id='{msg.agent_id}' session_id='{msg.session_id}'")

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

    def set_session_context(self, agent_id: str = "", user_id: str = "", session_id: str = None, env: str = "prod"):
        """
        Set default context for future messages in this session.
        
        Args:
            agent_id: Agent identifier
            user_id: User identifier
            session_id: Session UUID (auto-generated if None)
            env: Environment identifier
        """
        self._default_context = {
            "agent_id": agent_id,
            "user_id": user_id,
            "session_id": session_id or str(uuid.uuid4()),
            "env": env
        }
        if self._debug:
            print(f"[DEBUG] Set session context: {self._default_context}")

    def add_user_message(self, content: str, tokens: int = 0, **kwargs):
        """Convenience method to add a user message."""
        context = getattr(self, '_default_context', {})
        self.add_message("user", content, tokens=tokens, **{**context, **kwargs})

    def add_assistant_message(self, content: str, tokens: int = 0, **kwargs):
        """Convenience method to add an assistant message."""
        context = getattr(self, '_default_context', {})
        self.add_message("assistant", content, tokens=tokens, **{**context, **kwargs})

    def add_system_message(self, content: str, tokens: int = 0, **kwargs):
        """Convenience method to add a system message."""
        context = getattr(self, '_default_context', {})
        self.add_message("system", content, tokens=tokens, **{**context, **kwargs})

    # --- File storage helpers ---
    def _load_from_file(self):
        if os.path.exists(self._file_path):
            try:
                with open(self._file_path, encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:  # Only try to parse if file has content
                        data = json.loads(content)
                        self._history = [Message(**msg) for msg in data]
                    else:
                        self._history = []
                if self._debug:
                    print(f"[DEBUG] Loaded {len(self._history)} messages from file '{self._file_path}'")
            except (json.JSONDecodeError, ValueError) as e:
                if self._debug:
                    print(f"[DEBUG] Error loading file '{self._file_path}': {e}. Starting with empty history.")
                self._history = []
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
                content TEXT NOT NULL,
                agent_id TEXT DEFAULT '',
                user_id TEXT DEFAULT '',
                session_id TEXT NOT NULL,
                env TEXT DEFAULT 'prod',
                timestamp TEXT NOT NULL,
                tokens INTEGER DEFAULT 0,
                data TEXT DEFAULT ''
            )
            """
        )
        self._conn.commit()
        
        # Migrate existing schema if needed
        self._migrate_sqlite_schema()
        
        if self._debug:
            print(f"[DEBUG] Initialized SQLite database at '{self._sqlite_path}'")

    def _migrate_sqlite_schema(self):
        """
        Migrate existing SQLite schema to support new columns.
        This ensures backward compatibility with existing databases.
        """
        try:
            # Check if new columns exist by trying to select them
            self._conn.execute("SELECT agent_id FROM chat_history LIMIT 1")
        except sqlite3.OperationalError:
            # Columns don't exist, add them
            if self._debug:
                print("[DEBUG] Migrating SQLite schema to add new columns")
            
            self._conn.execute("ALTER TABLE chat_history ADD COLUMN agent_id TEXT DEFAULT ''")
            self._conn.execute("ALTER TABLE chat_history ADD COLUMN user_id TEXT DEFAULT ''")
            self._conn.execute("ALTER TABLE chat_history ADD COLUMN session_id TEXT DEFAULT ''")
            self._conn.execute("ALTER TABLE chat_history ADD COLUMN env TEXT DEFAULT 'prod'")
            self._conn.execute("ALTER TABLE chat_history ADD COLUMN timestamp TEXT DEFAULT ''")
            self._conn.execute("ALTER TABLE chat_history ADD COLUMN tokens INTEGER DEFAULT 0")
            self._conn.execute("ALTER TABLE chat_history ADD COLUMN data TEXT DEFAULT ''")
            
            # Update existing rows with default values
            current_time = datetime.now().isoformat()
            default_session = str(uuid.uuid4())
            self._conn.execute(
                "UPDATE chat_history SET timestamp = ?, session_id = ? WHERE timestamp = ''",
                (current_time, default_session)
            )
            
            self._conn.commit()
            if self._debug:
                print("[DEBUG] SQLite schema migration completed")

    def _save_to_sqlite(self, msg: Message):
        self._conn.execute(
            "INSERT INTO chat_history (role, content, agent_id, user_id, session_id, env, timestamp, tokens, data) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (msg.role, msg.content, msg.agent_id, msg.user_id, msg.session_id, msg.env, msg.timestamp, msg.tokens, msg.data)
        )
        self._conn.commit()
        if self._debug:
            print(f"[DEBUG] Saved message to SQLite: role='{msg.role}' session_id='{msg.session_id}'")

    def _load_from_sqlite(self):
        self._history = []
        cursor = self._conn.execute("SELECT role, content, agent_id, user_id, session_id, env, timestamp, tokens, data FROM chat_history ORDER BY id ASC")
        for row in cursor:
            self._history.append(Message(
                role=row[0],
                content=row[1],
                agent_id=row[2],
                user_id=row[3],
                session_id=row[4],
                env=row[5],
                timestamp=row[6],
                tokens=row[7],
                data=row[8]
            ))
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
        query = "SELECT role, content, agent_id, user_id, session_id, env, timestamp, tokens, data FROM chat_history"
        if where:
            query += f" WHERE {where}"
        query += " ORDER BY id ASC"
        cursor = self._conn.execute(query, params)
        results = [{
            "role": row[0],
            "content": row[1],
            "agent_id": row[2],
            "user_id": row[3],
            "session_id": row[4],
            "env": row[5],
            "timestamp": row[6],
            "tokens": row[7],
            "data": row[8]
        } for row in cursor]
        if self._debug:
            print(f"[DEBUG] query_sqlite returned {len(results)} messages with where='{where}' and params={params}")
        return results
