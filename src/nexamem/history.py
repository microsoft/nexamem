from typing import List, Dict
import os
import json
import sqlite3
from enum import Enum
from pydantic import BaseModel
from .config import get_config, ConfigError

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

try:
    from azure.identity import DefaultAzureCredential, ManagedIdentityCredential, ClientSecretCredential
    AZURE_IDENTITY_AVAILABLE = True
except ImportError:
    DefaultAzureCredential = None
    ManagedIdentityCredential = None
    ClientSecretCredential = None
    AZURE_IDENTITY_AVAILABLE = False

class StorageType(Enum):
    """Enum for NexaMem storage backend types."""
    MEMORY = "memory"
    FILE = "file"
    SQLITE = "sqlite"
    REDIS = "redis"

class RedisAuthMethod(Enum):
    """Enum for Redis authentication methods."""
    ACCESS_KEY = "access_key"
    ENTRA_ID = "entra_id"
    AZURE_AD = "entra_id"  # Alias for backward compatibility

class Message(BaseModel):
    role: str
    content: str

class ChatHistory:
    """
    Stores and manages NexaMem chatbot conversation history using Pydantic models.
    Supports in-memory, file, SQLite, and Redis (including Azure Redis Cache) storage based on configuration.
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
        elif self._storage == "redis":
            if not REDIS_AVAILABLE:
                raise ConfigError("Redis is not available. Please install redis package: pip install redis")
            self._init_redis(config)
            self._load_from_redis()
            
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
        elif self._storage == "redis":
            self._save_to_redis(msg)
        if self._debug:
            print(f"[DEBUG] Added message: role='{role}' content='{content}'")

    def get_history(self) -> List[Dict[str, str]]:
        if self._storage == "sqlite":
            self._load_from_sqlite()
        elif self._storage == "redis":
            self._load_from_redis()
        if self._debug:
            print(f"[DEBUG] get_history called. Returning {len(self._history)} messages.")
        return [msg.model_dump() for msg in self._history]

    def clear(self):
        self._history.clear()
        if self._storage == "file":
            self._save_to_file()
        elif self._storage == "sqlite":
            self._clear_sqlite()
        elif self._storage == "redis":
            self._clear_redis()
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
        elif self._storage == "redis":
            self._load_from_redis()
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

    # --- Redis storage helpers ---
    def _init_redis(self, config: Dict):
        """Initialize Redis connection with support for access key and Microsoft Entra ID authentication."""
        try:
            auth_method = config.get("redis_auth_method", "access_key")
            
            if auth_method == "entra_id":
                if not AZURE_IDENTITY_AVAILABLE:
                    raise ConfigError("azure-identity package is required for Entra ID authentication. Install with: pip install azure-identity")
                
                # Get Entra ID token
                credential = DefaultAzureCredential()
                scope = config.get("redis_entra_scope", "https://redis.azure.com/.default")
                token = credential.get_token(scope)
                
                # Use token as password for Redis AUTH
                self._redis_client = redis.Redis(
                    host=config["redis_host"],
                    port=config["redis_port"],
                    password=token.token,  # Use Entra ID token as password
                    ssl=config.get("redis_ssl", True),
                    db=config.get("redis_db", 0),
                    socket_timeout=30,
                    socket_connect_timeout=30,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                
                # Store credential and scope for token refresh
                self._entra_credential = credential
                self._entra_scope = scope
                self._auth_method = "entra_id"
                
            else:  # access_key authentication
                self._redis_client = redis.Redis(
                    host=config["redis_host"],
                    port=config["redis_port"],
                    password=config.get("redis_password"),
                    ssl=config.get("redis_ssl", True),
                    db=config.get("redis_db", 0),
                    socket_timeout=30,
                    socket_connect_timeout=30,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                self._auth_method = "access_key"
            
            self._redis_key_prefix = config.get("redis_key_prefix", "nexamem:")
            self._redis_history_key = f"{self._redis_key_prefix}history"
            
            # Test connection
            self._redis_client.ping()
            if self._debug:
                auth_info = "Entra ID" if auth_method == "entra_id" else "access key"
                print(f"[DEBUG] Connected to Redis at {config['redis_host']}:{config['redis_port']} using {auth_info}")
                
        except Exception as e:
            raise ConfigError(f"Failed to connect to Redis: {e}")

    def _refresh_entra_token_if_needed(self):
        """Refresh Entra ID token if needed (called before Redis operations)."""
        if hasattr(self, '_auth_method') and self._auth_method == "entra_id":
            try:
                # Get a fresh token (azure-identity handles caching and refresh automatically)
                token = self._entra_credential.get_token(self._entra_scope)
                # Update the Redis client's password if token changed
                if hasattr(self._redis_client.connection_pool, 'connection_kwargs'):
                    self._redis_client.connection_pool.connection_kwargs['password'] = token.token
            except Exception as e:
                if self._debug:
                    print(f"[DEBUG] Failed to refresh Entra ID token: {e}")

    def _save_to_redis(self, msg: Message):
        """Save a single message to Redis using a list structure."""
        try:
            self._refresh_entra_token_if_needed()
            message_data = json.dumps(msg.model_dump())
            self._redis_client.rpush(self._redis_history_key, message_data)
            if self._debug:
                print(f"[DEBUG] Saved message to Redis: role='{msg.role}' content='{msg.content}'")
        except Exception as e:
            if self._debug:
                print(f"[DEBUG] Error saving to Redis: {e}")
            raise

    def _load_from_redis(self):
        """Load all messages from Redis."""
        try:
            self._refresh_entra_token_if_needed()
            self._history = []
            messages = self._redis_client.lrange(self._redis_history_key, 0, -1)
            for msg_json in messages:
                msg_data = json.loads(msg_json.decode('utf-8'))
                self._history.append(Message(**msg_data))
            if self._debug:
                print(f"[DEBUG] Loaded {len(self._history)} messages from Redis.")
        except Exception as e:
            if self._debug:
                print(f"[DEBUG] Error loading from Redis: {e}")
            self._history = []

    def _clear_redis(self):
        """Clear all messages from Redis."""
        try:
            self._refresh_entra_token_if_needed()
            self._redis_client.delete(self._redis_history_key)
            self._history = []
            if self._debug:
                print("[DEBUG] Cleared Redis chat history.")
        except Exception as e:
            if self._debug:
                print(f"[DEBUG] Error clearing Redis: {e}")
            raise

    def query_redis(self, pattern: str = None, limit: int = None) -> List[Dict[str, str]]:
        """
        Query Redis chat history with optional filtering.

        Args:
            pattern (str, optional): Pattern to search for in message content (case-insensitive).
            limit (int, optional): Maximum number of messages to return.
        Returns:
            List[Dict[str, str]]: List of matching messages.
        Raises:
            ConfigError: If not using Redis storage.
        """
        if self._storage != "redis":
            raise ConfigError("query_redis is only available when using Redis storage.")
        
        try:
            self._refresh_entra_token_if_needed()
            # Load current history from Redis
            self._load_from_redis()
            results = []
            
            for msg in self._history:
                msg_dict = msg.model_dump()
                if pattern is None or pattern.lower() in msg_dict['content'].lower():
                    results.append(msg_dict)
                    if limit and len(results) >= limit:
                        break
            
            if self._debug:
                print(f"[DEBUG] query_redis returned {len(results)} messages with pattern='{pattern}' and limit={limit}")
            return results
        except Exception as e:
            if self._debug:
                print(f"[DEBUG] Error querying Redis: {e}")
            return []

    def get_redis_info(self) -> Dict[str, str]:
        """
        Get Redis connection information and statistics.
        
        Returns:
            Dict[str, str]: Redis connection info and stats.
        Raises:
            ConfigError: If not using Redis storage.
        """
        if self._storage != "redis":
            raise ConfigError("get_redis_info is only available when using Redis storage.")
        
        try:
            self._refresh_entra_token_if_needed()
            info = self._redis_client.info()
            history_length = self._redis_client.llen(self._redis_history_key)
            
            return {
                "redis_version": info.get("redis_version", "unknown"),
                "connected_clients": str(info.get("connected_clients", 0)),
                "used_memory": info.get("used_memory_human", "unknown"),
                "history_length": str(history_length),
                "host": self._redis_client.connection_pool.connection_kwargs.get("host", "unknown"),
                "port": str(self._redis_client.connection_pool.connection_kwargs.get("port", 0)),
                "ssl_enabled": str(self._redis_client.connection_pool.connection_kwargs.get("ssl", False))
            }
        except Exception as e:
            if self._debug:
                print(f"[DEBUG] Error getting Redis info: {e}")
            return {"error": str(e)}
