"""
Redis storage adapter configuration.
"""
from typing import Any, Dict, Optional

from nexamem.storage_adapters.configs.i_storage_adapter_config import IStorageAdapterConfig


class RedisAdapterConfig(IStorageAdapterConfig):
    """
    Configuration for Redis storage adapter.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0,
        ssl: bool = False,
        ssl_cert_reqs: Optional[str] = None,
        ssl_ca_certs: Optional[str] = None,
        ssl_certfile: Optional[str] = None,
        ssl_keyfile: Optional[str] = None,
        connection_pool_kwargs: Optional[Dict[str, Any]] = None,
        decode_responses: bool = True,
        health_check_interval: int = 30,
        socket_connect_timeout: int = 5,
        socket_timeout: int = 5,
        retry_on_timeout: bool = True,
        max_connections: int = 50,
        **kwargs: Any
    ):
        """
        Initialize Redis adapter configuration.

        Args:
            host: Redis server hostname
            port: Redis server port
            password: Redis server password
            db: Redis database number
            ssl: Enable SSL/TLS connection
            ssl_cert_reqs: SSL certificate requirements
            ssl_ca_certs: Path to CA certificates file
            ssl_certfile: Path to client certificate file
            ssl_keyfile: Path to client private key file
            connection_pool_kwargs: Additional connection pool arguments
            decode_responses: Whether to decode responses to strings
            health_check_interval: Health check interval in seconds
            socket_connect_timeout: Connection timeout in seconds
            socket_timeout: Socket timeout in seconds
            retry_on_timeout: Whether to retry on timeout
            max_connections: Maximum number of connections in pool
            **kwargs: Additional configuration parameters
        """
        self.host = host
        self.port = port
        self.password = password
        self.db = db
        self.ssl = ssl
        self.ssl_cert_reqs = ssl_cert_reqs
        self.ssl_ca_certs = ssl_ca_certs
        self.ssl_certfile = ssl_certfile
        self.ssl_keyfile = ssl_keyfile
        self.connection_pool_kwargs = connection_pool_kwargs or {}
        self.decode_responses = decode_responses
        self.health_check_interval = health_check_interval
        self.socket_connect_timeout = socket_connect_timeout
        self.socket_timeout = socket_timeout
        self.retry_on_timeout = retry_on_timeout
        self.max_connections = max_connections

        # Store additional kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_redis_kwargs(self) -> Dict[str, Any]:
        """
        Convert configuration to redis-py connection arguments.

        Returns:
            Dictionary of redis-py connection arguments
        """
        kwargs = {
            "host": self.host,
            "port": self.port,
            "db": self.db,
            "decode_responses": self.decode_responses,
            "health_check_interval": self.health_check_interval,
            "socket_connect_timeout": self.socket_connect_timeout,
            "socket_timeout": self.socket_timeout,
            "retry_on_timeout": self.retry_on_timeout,
            "max_connections": self.max_connections,
        }

        if self.password:
            kwargs["password"] = self.password

        if self.ssl:
            kwargs["ssl"] = True
            if self.ssl_cert_reqs:
                kwargs["ssl_cert_reqs"] = self.ssl_cert_reqs
            if self.ssl_ca_certs:
                kwargs["ssl_ca_certs"] = self.ssl_ca_certs
            if self.ssl_certfile:
                kwargs["ssl_certfile"] = self.ssl_certfile
            if self.ssl_keyfile:
                kwargs["ssl_keyfile"] = self.ssl_keyfile

        # Add any additional connection pool kwargs
        kwargs.update(self.connection_pool_kwargs)

        return kwargs
