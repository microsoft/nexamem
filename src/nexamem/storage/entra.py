"""Owned, renewable Redis credentials using redis-entraid's streaming provider."""

import asyncio
import threading
from collections.abc import Callable
from concurrent.futures import Future
from typing import Any

from azure.identity import ClientSecretCredential, DefaultAzureCredential
from redis.auth.token_manager import RetryPolicy, TokenManager, TokenManagerConfig
from redis_entraid.cred_provider import EntraIdCredentialsProvider
from redis_entraid.identity_provider import DefaultAzureCredentialProvider

from ..config.storage import AzureRedisConfig


class _OwnedTokenManager(TokenManager):
    _closed = False
    _owned_loop: asyncio.AbstractEventLoop | None = None
    _thread: threading.Thread | None = None

    def start(self, listener: Any, skip_initial: bool = False) -> Callable[[], None]:
        self._listener = listener
        loop = asyncio.new_event_loop()
        self._owned_loop = loop

        def run() -> None:
            asyncio.set_event_loop(loop)
            try:
                loop.run_forever()
            finally:
                loop.close()

        self._thread = threading.Thread(target=run, name="nexamem-redis-renewal", daemon=True)
        self._thread.start()
        initial: Future[None] = Future()

        def renew() -> None:
            try:
                self._renew_token(skip_initial)
                initial.set_result(None)
            except BaseException as error:
                initial.set_exception(error)

        loop.call_soon_threadsafe(renew)
        initial.result()
        return self.stop

    async def acquire_token_async(self, force_refresh: bool = False) -> Any:
        return await asyncio.to_thread(self.acquire_token, force_refresh)

    async def _renew_token_async(self, *args: Any, **kwargs: Any) -> None:
        if not self._closed:
            await super()._renew_token_async(*args, **kwargs)

    def stop(self) -> None:
        self._closed = True
        loop = self._owned_loop
        if loop is not None and not loop.is_closed():
            loop.call_soon_threadsafe(super().stop)
            loop.call_soon_threadsafe(loop.stop)
            if self._thread is not None and self._thread is not threading.current_thread():
                self._thread.join()
        else:
            super().stop()


class RedisEntraCredentials(EntraIdCredentialsProvider):
    """Use token object IDs as usernames and stop renewal when the client closes."""

    _token_mgr: _OwnedTokenManager

    def __init__(self, config: AzureRedisConfig) -> None:
        self.credential: ClientSecretCredential | DefaultAzureCredential
        if config.client_id and config.client_secret and config.tenant_id:
            self.credential = ClientSecretCredential(
                config.tenant_id, config.client_id, config.client_secret
            )
        else:
            self.credential = DefaultAzureCredential(managed_identity_client_id=config.client_id)
        manager_config = TokenManagerConfig(0.7, 0, 10000, RetryPolicy(3, 100))
        super().__init__(
            DefaultAzureCredentialProvider(self.credential, ("https://redis.azure.com/.default",)),
            manager_config,
        )
        self._token_mgr = _OwnedTokenManager(self._idp, manager_config)

    def close(self) -> None:
        """Stop the provider's refresh timers and release the owned Azure credential."""
        self._token_mgr.stop()
        self.credential.close()
