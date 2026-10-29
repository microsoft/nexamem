"""Dependency injection and storage selection contracts."""

from pathlib import Path
from unittest.mock import patch

import pytest

from nexamem.config.storage import AzureRedisConfig, MemoryConfig, StorageConfig, StorageType
from nexamem.di.container import DIContainer
from nexamem.di.providers import FactoryProvider, SingletonProvider, TransientProvider
from nexamem.storage.base import BaseAsyncStorage, BaseStorage
from nexamem.storage.factory import StorageFactory, create_storage_from_config


class Service:
    def __init__(self, value: str = "default") -> None:
        self.value = value


@pytest.mark.parametrize(
    "provider_type,same", [(SingletonProvider, True), (TransientProvider, False)]
)
def test_provider_lifecycle(provider_type: type, same: bool) -> None:
    provider = provider_type()
    assert provider.can_provide(Service)
    first = provider.provide(Service)
    second = provider.provide(Service)
    assert (first is second) is same
    assert first.value == "default"
    assert provider_type().provide(Service, {"value": "configured"}).value == "configured"
    with patch.object(provider, "can_provide", return_value=False):
        with pytest.raises(ValueError):
            provider.provide(dict)


@pytest.mark.parametrize("singleton", [False, True])
def test_factory_provider(singleton: bool) -> None:
    provider = FactoryProvider(
        lambda service_type, config: service_type(**(config or {})), singleton
    )
    assert provider.can_provide(Service)
    first = provider.provide(Service, {"value": "custom"})
    assert first.value == "custom"
    assert (provider.provide(Service) is first) is singleton


def test_container_configuration_and_scopes() -> None:
    container = DIContainer()
    assert container.get_config() == {}
    assert container.try_resolve(Service) is None
    assert not container.is_registered(Service)
    with pytest.raises(ValueError):
        container.resolve(Service)
    container.set_config({"value": "global"})
    container.register(Service, TransientProvider())
    assert container.is_registered(Service)
    assert container.registry.list_registered_types() == [Service]
    assert container.get_config("value") == "global"
    assert container.resolve(Service).value == "global"
    assert container.resolve(Service, {"value": "local"}).value == "local"
    scope = container.build_scope()
    assert scope.resolve(Service).value == "global"
    scope.set_config({"value": "scope"})
    assert container.get_config("value") == "global"
    scope.registry.unregister(Service)
    scope.registry.unregister(Service)
    assert scope.try_resolve(Service) is None
    assert container.is_registered(Service)
    container.registry.clear()
    assert container.registry.list_registered_types() == []


def test_storage_factory_backends(tmp_path: Path) -> None:
    configurations = [
        StorageConfig.memory(),
        StorageConfig.file(str(tmp_path / "files")),
        StorageConfig.sqlite(str(tmp_path / "data.db")),
        StorageConfig.azure_redis(
            AzureRedisConfig(hostname="unit.redis.cache.windows.net", access_key="unit-test-only")
        ),
    ]
    for config in configurations:
        assert isinstance(StorageFactory.create_sync_storage(config), BaseStorage)
        assert isinstance(StorageFactory.create_async_storage(config), BaseAsyncStorage)
        assert isinstance(create_storage_from_config(config, False), BaseStorage)
        assert isinstance(create_storage_from_config(config), BaseAsyncStorage)


@pytest.mark.parametrize(
    "storage_type", [StorageType.AZURE_REDIS, StorageType.FILE, StorageType.SQLITE]
)
def test_storage_factory_rejects_mismatched_configuration(storage_type: StorageType) -> None:
    config = StorageConfig(type=storage_type, config=MemoryConfig())
    with pytest.raises(ValueError):
        StorageFactory.create_sync_storage(config)
    with pytest.raises(ValueError):
        StorageFactory.create_async_storage(config)
