"""
Redis adapter for AIMemory with sync and async support.
Supports Azure Cache for Redis with access keys and Entra ID authentication.
"""
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import redis
    import redis.asyncio as redis_async
except ImportError:
    redis = None
    redis_async = None

try:
    import fakeredis
except ImportError:
    fakeredis = None

try:
    from azure.identity import DefaultAzureCredential, ClientSecretCredential
    from azure.keyvault.secrets import SecretClient
except ImportError:
    DefaultAzureCredential = None
    ClientSecretCredential = None
    SecretClient = None

from .memory_scope import MemoryScope


class RedisConnectionError(Exception):
    """Raised when Redis connection fails."""
    pass


class AzureRedisConnectionHelper:
    """Helper class for Azure Cache for Redis connections."""
    
    @staticmethod
    def get_azure_redis_config(
        hostname: str,
        access_key: Optional[str] = None,
        use_entra_id: bool = False,
        username: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        tenant_id: Optional[str] = None,
        keyvault_url: Optional[str] = None,
        secret_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create Redis configuration for Azure Cache for Redis.
        
        Args:
            hostname: Azure Redis hostname (e.g., 'myredis.redis.cache.windows.net')
            access_key: Redis access key (for key-based auth)
            use_entra_id: Use Entra ID authentication
            username: Username for Entra ID auth (typically same as client_id)
            client_id: Azure client ID for service principal auth
            client_secret: Azure client secret for service principal auth
            tenant_id: Azure tenant ID
            keyvault_url: Azure Key Vault URL to retrieve secrets
            secret_name: Name of secret in Key Vault containing Redis access key
            
        Returns:
            Dict with Redis connection parameters
        """
        config = {
            'host': hostname,
            'port': 6380,  # Azure Redis default SSL port
            'ssl': True,
            'ssl_cert_reqs': None,  # Azure Redis specific SSL config
            'decode_responses': True
        }
        
        if use_entra_id:
            if not DefaultAzureCredential:
                raise ImportError("azure-identity package required for Entra ID auth")
            
            # Get token for Redis access
            if client_id and client_secret and tenant_id:
                credential = ClientSecretCredential(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    client_secret=client_secret
                )
            else:
                credential = DefaultAzureCredential()
            
            # Get access token for Azure Redis
            token = credential.get_token("https://redis.azure.com/.default")
            config['username'] = username or client_id or 'default'
            config['password'] = token.token
            
        elif keyvault_url and secret_name:
            if not SecretClient:
                raise ImportError("azure-keyvault-secrets package required for Key Vault")
            
            # Get access key from Key Vault
            credential = DefaultAzureCredential()
            secret_client = SecretClient(vault_url=keyvault_url, credential=credential)
            secret = secret_client.get_secret(secret_name)
            config['password'] = secret.value
            
        elif access_key:
            config['password'] = access_key
        else:
            raise ValueError("Must provide either access_key, Key Vault config, or Entra ID config")
        
        return config
    
    @staticmethod
    def create_azure_connection_string(
        hostname: str,
        access_key: Optional[str] = None,
        ssl: bool = True,
        port: int = 6380
    ) -> str:
        """Create Redis connection string for Azure Cache for Redis."""
        if not access_key:
            raise ValueError("Access key required for connection string")
        
        protocol = "rediss" if ssl else "redis"
        return f"{protocol}://:{access_key}@{hostname}:{port}"


class RedisAdapter:
    """Synchronous Redis adapter for AIMemory with Azure support."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        ssl: bool = False,
        db: int = 0,
        use_fakeredis: bool = False,
        # Azure-specific parameters
        azure_hostname: Optional[str] = None,
        azure_access_key: Optional[str] = None,
        use_azure_entra_id: bool = False,
        azure_username: Optional[str] = None,
        azure_client_id: Optional[str] = None,
        azure_client_secret: Optional[str] = None,
        azure_tenant_id: Optional[str] = None,
        azure_keyvault_url: Optional[str] = None,
        azure_secret_name: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize Redis adapter with Azure Cache for Redis support.
        
        Args:
            host: Redis server hostname (for non-Azure)
            port: Redis server port
            password: Redis password (for non-Azure)
            ssl: Use SSL connection
            db: Redis database number
            use_fakeredis: Use fakeredis for testing
            azure_hostname: Azure Redis hostname (e.g., 'myredis.redis.cache.windows.net')
            azure_access_key: Azure Redis access key
            use_azure_entra_id: Use Entra ID authentication
            azure_username: Username for Entra ID auth
            azure_client_id: Azure client ID for service principal auth
            azure_client_secret: Azure client secret for service principal auth
            azure_tenant_id: Azure tenant ID
            azure_keyvault_url: Azure Key Vault URL
            azure_secret_name: Name of secret in Key Vault
            **kwargs: Additional Redis connection parameters
        """
        self.use_fakeredis = use_fakeredis
        self.is_azure = bool(azure_hostname)
        
        if redis is None and not use_fakeredis:
            raise ImportError("redis package is required. Install with: pip install redis")
        
        if use_fakeredis:
            if fakeredis is None:
                raise ImportError("fakeredis package is required. Install with: pip install fakeredis")
            self.client = fakeredis.FakeRedis(decode_responses=True)
            self.host = "fakeredis"
            self.port = 6379
            self.password = None
            self.ssl = False
            self.db = db
        elif self.is_azure:
            # Use Azure configuration
            azure_config = AzureRedisConnectionHelper.get_azure_redis_config(
                hostname=azure_hostname,
                access_key=azure_access_key,
                use_entra_id=use_azure_entra_id,
                username=azure_username,
                client_id=azure_client_id,
                client_secret=azure_client_secret,
                tenant_id=azure_tenant_id,
                keyvault_url=azure_keyvault_url,
                secret_name=azure_secret_name
            )
            
            # Store connection details
            self.host = azure_config['host']
            self.port = azure_config['port']
            self.password = azure_config['password']
            self.ssl = azure_config['ssl']
            self.db = db
            
            # Create Redis client with Azure config
            self.client = redis.Redis(
                host=azure_config['host'],
                port=azure_config['port'],
                password=azure_config['password'],
                ssl=azure_config['ssl'],
                ssl_cert_reqs=azure_config.get('ssl_cert_reqs'),
                username=azure_config.get('username'),
                db=db,
                decode_responses=True,
                **kwargs
            )
        else:
            # Standard Redis configuration
            self.host = host
            self.port = port
            self.password = password
            self.ssl = ssl
            self.db = db
            
            self.client = redis.Redis(
                host=host,
                port=port,
                password=password,
                ssl=ssl,
                db=db,
                decode_responses=True,
                **kwargs
            )
        
        # Test connection
        try:
            self.client.ping()
        except Exception as e:
            raise RedisConnectionError(f"Failed to connect to Redis: {e}") from e
    
    def write_message(
        self,
        scope: MemoryScope,
        channel: str,
        content: Union[str, bytes],
        ttl_sec: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Write a message to Redis.
        
        Args:
            scope: Memory scope
            channel: Channel name
            content: Message content
            ttl_sec: Time-to-live in seconds
            metadata: Optional metadata
            
        Returns:
            Message UUID
        """
        message_uuid = str(uuid.uuid4())
        timestamp = int(time.time())
        
        # Create message object
        message = {
            "uuid": message_uuid,
            "timestamp": timestamp,
            "content": content if isinstance(content, str) else content.decode('utf-8', errors='ignore'),
            "metadata": metadata or {}
        }
        
        # Store message
        message_key = f"{scope.get_key_prefix(channel)}:{message_uuid}"
        self.client.setex(message_key, ttl_sec, json.dumps(message))
        
        # Update sorted set index
        index_key = scope.get_index_key(channel)
        self.client.zadd(index_key, {message_uuid: timestamp})
        self.client.expire(index_key, ttl_sec)
        
        return message_uuid
    
    def read_messages(
        self,
        scope: MemoryScope,
        channel: str,
        *,
        since_sec: Optional[int] = None,
        max_msgs: Optional[int] = None,
        max_bytes: Optional[int] = None
    ) -> Tuple[List[str], Dict[str, Any]]:
        """
        Read messages from Redis.
        
        Args:
            scope: Memory scope
            channel: Channel name
            since_sec: Only messages newer than this (seconds ago)
            max_msgs: Maximum number of messages
            max_bytes: Maximum total bytes
            
        Returns:
            Tuple of (messages, metadata)
        """
        index_key = scope.get_index_key(channel)
        
        # Calculate time range
        max_score = int(time.time())
        min_score = 0
        if since_sec is not None:
            min_score = max_score - since_sec
        
        # Get message UUIDs from sorted set (newest first)
        message_uuids = self.client.zrevrangebyscore(
            index_key,
            max_score,
            min_score,
            start=0,
            num=max_msgs or -1
        )
        
        messages = []
        total_bytes = 0
        retrieved_count = 0
        
        for message_uuid in message_uuids:
            message_key = f"{scope.get_key_prefix(channel)}:{message_uuid}"
            message_data = self.client.get(message_key)
            
            if message_data is None:
                # Message expired, remove from index
                self.client.zrem(index_key, message_uuid)
                continue
            
            try:
                message = json.loads(message_data)
                content = message["content"]
                
                # Check byte limit
                content_bytes = len(content.encode('utf-8'))
                if max_bytes and (total_bytes + content_bytes) > max_bytes:
                    break
                
                messages.append(content)
                total_bytes += content_bytes
                retrieved_count += 1
                
            except (json.JSONDecodeError, KeyError):
                # Invalid message, remove from index
                self.client.zrem(index_key, message_uuid)
                continue
        
        metadata = {
            "total_messages": retrieved_count,
            "total_bytes": total_bytes,
            "truncated": len(message_uuids) > retrieved_count
        }
        
        return messages, metadata
    
    def bulk_erase(self, scope: MemoryScope) -> int:
        """
        Erase all messages for a scope across all channels.
        
        Args:
            scope: Memory scope
            
        Returns:
            Number of keys deleted
        """
        pattern = f"{scope.env}:{scope.agent_id}:{scope.user_id}:{scope.session_id}:*"
        keys = self.client.keys(pattern)
        
        if keys:
            return self.client.delete(*keys)
        return 0
    
    def count_bytes(self, scope: MemoryScope, channel: str) -> int:
        """
        Count total bytes for a scope and channel.
        
        Args:
            scope: Memory scope
            channel: Channel name
            
        Returns:
            Total bytes
        """
        index_key = scope.get_index_key(channel)
        message_uuids = self.client.zrange(index_key, 0, -1)
        
        total_bytes = 0
        for message_uuid in message_uuids:
            message_key = f"{scope.get_key_prefix(channel)}:{message_uuid}"
            message_data = self.client.get(message_key)
            
            if message_data is None:
                # Message expired, remove from index
                self.client.zrem(index_key, message_uuid)
                continue
            
            try:
                message = json.loads(message_data)
                content = message["content"]
                total_bytes += len(content.encode('utf-8'))
            except (json.JSONDecodeError, KeyError):
                # Invalid message, remove from index
                self.client.zrem(index_key, message_uuid)
                continue
        
        return total_bytes
    
    def checkpoint_set(self, scope: MemoryScope, key: str, payload: dict) -> None:
        """Set a checkpoint value."""
        checkpoint_key = f"{scope.env}:{scope.agent_id}:checkpoint:{key}"
        self.client.set(checkpoint_key, json.dumps(payload))
    
    def checkpoint_get(self, scope: MemoryScope, key: str) -> Optional[dict]:
        """Get a checkpoint value."""
        checkpoint_key = f"{scope.env}:{scope.agent_id}:checkpoint:{key}"
        data = self.client.get(checkpoint_key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return None
        return None
    
    def ping(self) -> bool:
        """Test Redis connection."""
        try:
            return self.client.ping()
        except Exception:
            return False
    
    def get_info(self) -> Dict[str, Any]:
        """Get Redis connection info."""
        return {
            "host": self.host,
            "port": self.port,
            "ssl": self.ssl,
            "db": self.db,
            "connected": self.ping(),
            "use_fakeredis": self.use_fakeredis,
            "is_azure": self.is_azure
        }


class AsyncRedisAdapter:
    """Asynchronous Redis adapter for AIMemory with Azure support."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        ssl: bool = False,
        db: int = 0,
        # Azure-specific parameters
        azure_hostname: Optional[str] = None,
        azure_access_key: Optional[str] = None,
        use_azure_entra_id: bool = False,
        azure_username: Optional[str] = None,
        azure_client_id: Optional[str] = None,
        azure_client_secret: Optional[str] = None,
        azure_tenant_id: Optional[str] = None,
        azure_keyvault_url: Optional[str] = None,
        azure_secret_name: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize async Redis adapter with Azure Cache for Redis support.
        
        Args:
            host: Redis server hostname (for non-Azure)
            port: Redis server port
            password: Redis password (for non-Azure)
            ssl: Use SSL connection
            db: Redis database number
            azure_hostname: Azure Redis hostname
            azure_access_key: Azure Redis access key
            use_azure_entra_id: Use Entra ID authentication
            azure_username: Username for Entra ID auth
            azure_client_id: Azure client ID for service principal auth
            azure_client_secret: Azure client secret for service principal auth
            azure_tenant_id: Azure tenant ID
            azure_keyvault_url: Azure Key Vault URL
            azure_secret_name: Name of secret in Key Vault
            **kwargs: Additional Redis connection parameters
        """
        if redis_async is None:
            raise ImportError("redis[asyncio] package is required. Install with: pip install redis[asyncio]")
        
        self.is_azure = bool(azure_hostname)
        
        if self.is_azure:
            # Use Azure configuration
            azure_config = AzureRedisConnectionHelper.get_azure_redis_config(
                hostname=azure_hostname,
                access_key=azure_access_key,
                use_entra_id=use_azure_entra_id,
                username=azure_username,
                client_id=azure_client_id,
                client_secret=azure_client_secret,
                tenant_id=azure_tenant_id,
                keyvault_url=azure_keyvault_url,
                secret_name=azure_secret_name
            )
            
            # Store connection details
            self.host = azure_config['host']
            self.port = azure_config['port']
            self.password = azure_config['password']
            self.ssl = azure_config['ssl']
            self.db = db
            
            # Create async Redis client with Azure config
            self.client = redis_async.Redis(
                host=azure_config['host'],
                port=azure_config['port'],
                password=azure_config['password'],
                ssl=azure_config['ssl'],
                ssl_cert_reqs=azure_config.get('ssl_cert_reqs'),
                username=azure_config.get('username'),
                db=db,
                decode_responses=True,
                **kwargs
            )
        else:
            # Standard Redis configuration
            self.host = host
            self.port = port
            self.password = password
            self.ssl = ssl
            self.db = db
            
            self.client = redis_async.Redis(
                host=host,
                port=port,
                password=password,
                ssl=ssl,
                db=db,
                decode_responses=True,
                **kwargs
            )
    
    async def write_message(
        self,
        scope: MemoryScope,
        channel: str,
        content: Union[str, bytes],
        ttl_sec: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Async version of write_message."""
        message_uuid = str(uuid.uuid4())
        timestamp = int(time.time())
        
        message = {
            "uuid": message_uuid,
            "timestamp": timestamp,
            "content": content if isinstance(content, str) else content.decode('utf-8', errors='ignore'),
            "metadata": metadata or {}
        }
        
        message_key = f"{scope.get_key_prefix(channel)}:{message_uuid}"
        await self.client.setex(message_key, ttl_sec, json.dumps(message))
        
        index_key = scope.get_index_key(channel)
        await self.client.zadd(index_key, {message_uuid: timestamp})
        await self.client.expire(index_key, ttl_sec)
        
        return message_uuid
    
    async def read_messages(
        self,
        scope: MemoryScope,
        channel: str,
        *,
        since_sec: Optional[int] = None,
        max_msgs: Optional[int] = None,
        max_bytes: Optional[int] = None
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Async version of read_messages."""
        index_key = scope.get_index_key(channel)
        
        max_score = int(time.time())
        min_score = 0
        if since_sec is not None:
            min_score = max_score - since_sec
        
        message_uuids = await self.client.zrevrangebyscore(
            index_key,
            max_score,
            min_score,
            start=0,
            num=max_msgs or -1
        )
        
        messages = []
        total_bytes = 0
        retrieved_count = 0
        
        for message_uuid in message_uuids:
            message_key = f"{scope.get_key_prefix(channel)}:{message_uuid}"
            message_data = await self.client.get(message_key)
            
            if message_data is None:
                await self.client.zrem(index_key, message_uuid)
                continue
            
            try:
                message = json.loads(message_data)
                content = message["content"]
                
                content_bytes = len(content.encode('utf-8'))
                if max_bytes and (total_bytes + content_bytes) > max_bytes:
                    break
                
                messages.append(content)
                total_bytes += content_bytes
                retrieved_count += 1
                
            except (json.JSONDecodeError, KeyError):
                await self.client.zrem(index_key, message_uuid)
                continue
        
        metadata = {
            "total_messages": retrieved_count,
            "total_bytes": total_bytes,
            "truncated": len(message_uuids) > retrieved_count
        }
        
        return messages, metadata
    
    async def bulk_erase(self, scope: MemoryScope) -> int:
        """Async version of bulk_erase."""
        pattern = f"{scope.env}:{scope.agent_id}:{scope.user_id}:{scope.session_id}:*"
        keys = await self.client.keys(pattern)
        
        if keys:
            return await self.client.delete(*keys)
        return 0
    
    async def count_bytes(self, scope: MemoryScope, channel: str) -> int:
        """Async version of count_bytes."""
        index_key = scope.get_index_key(channel)
        message_uuids = await self.client.zrange(index_key, 0, -1)
        
        total_bytes = 0
        for message_uuid in message_uuids:
            message_key = f"{scope.get_key_prefix(channel)}:{message_uuid}"
            message_data = await self.client.get(message_key)
            
            if message_data is None:
                await self.client.zrem(index_key, message_uuid)
                continue
            
            try:
                message = json.loads(message_data)
                content = message["content"]
                total_bytes += len(content.encode('utf-8'))
            except (json.JSONDecodeError, KeyError):
                await self.client.zrem(index_key, message_uuid)
                continue
        
        return total_bytes
    
    async def checkpoint_set(self, scope: MemoryScope, key: str, payload: dict) -> None:
        """Async version of checkpoint_set."""
        checkpoint_key = f"{scope.env}:{scope.agent_id}:checkpoint:{key}"
        await self.client.set(checkpoint_key, json.dumps(payload))
    
    async def checkpoint_get(self, scope: MemoryScope, key: str) -> Optional[dict]:
        """Async version of checkpoint_get."""
        checkpoint_key = f"{scope.env}:{scope.agent_id}:checkpoint:{key}"
        data = await self.client.get(checkpoint_key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return None
        return None
    
    async def ping(self) -> bool:
        """Test Redis connection."""
        try:
            return await self.client.ping()
        except Exception:
            return False
    
    async def close(self):
        """Close the Redis connection."""
        await self.client.close()
    
    def get_info(self) -> Dict[str, Any]:
        """Get Redis connection info."""
        return {
            "host": self.host,
            "port": self.port,
            "ssl": self.ssl,
            "db": self.db,
            "async": True,
            "is_azure": self.is_azure
        }
