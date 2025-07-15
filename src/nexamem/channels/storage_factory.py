from typing import Type, Dict

from lagom import Container
from nexamem.storage_adapters.i_storage_adapter import IStorageAdapter
from nexamem.storage_adapters.configs.i_storage_adapter_config import IStorageAdapterConfig

class StorageAdapterFactory():
    """
    Factory for creating storage adapters based on type.
    Allows dynamic registration of new adapter types.
    """
    _registry: Dict[str, Type[IStorageAdapter]] = {}

    def __init__(self, container:Container):
        pass

    @classmethod
    def register_adapter(cls, adapter_type: str, adapter_cls: Type[IStorageAdapter]) -> None:
        """
        Register a new storage adapter class with a type name.

        :param adapter_type: The string identifier for the adapter type.
        :param adapter_cls: The adapter class implementing IStorageAdapter.
        """
        cls._registry[adapter_type] = adapter_cls

    @classmethod
    def create_adapter(cls, adapter_type: str, config: IStorageAdapterConfig) -> IStorageAdapter:
        """
        Create an instance of a registered storage adapter.

        :param adapter_type: The string identifier for the adapter type.
        :param config: The configuration object for the adapter.
        :return: An instance of IStorageAdapter.
        :raises ValueError: If the adapter type is not registered.
        """
        if adapter_type not in cls._registry:
            raise ValueError(f"Adapter type '{adapter_type}' is not registered.")
        return cls._registry[adapter_type](config)
