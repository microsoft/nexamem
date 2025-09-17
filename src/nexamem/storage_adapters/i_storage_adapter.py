from abc import abstractmethod
from typing import Protocol

from nexamem.schemas.memory_entry import MemoryEntry
from nexamem.schemas.memory_filter import MemoryFilter
from nexamem.storage_adapters.configs.i_storage_adapter_config import IStorageAdapterConfig


class IStorageAdapter(Protocol):
    """
    Interface for adapters that handle different storage.
    """

    @abstractmethod
    def __init__(self, config: IStorageAdapterConfig):
        """
        Initialize the storage adapter with the given configuration.

        :param config: Configuration object for the storage adapter.
        """
        raise NotImplementedError("This method should be overridden by subclasses.")


    @abstractmethod
    async def write(self, entries: list[MemoryEntry]) -> None:
        """
        Create a new data entry at the specified path.

        :param path: The path where the data will be created.
        :param data: The data to be created.
        :return: The ID of the created data entry.
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    @abstractmethod
    async def read(self, filter: MemoryFilter) -> list[MemoryEntry]:
        """
        Retrieve data from the specified ID.

        :param id: The ID of the data.
        :return: A dictionary containing the read data.
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    # @abstractmethod
    # def read_last_n_records(self, number_of_records: int, memory_scope: MemoryScope, channel: str) -> list[MemoryEntry]:
    #     raise NotImplementedError(
    #         "This method should be overridden by subclasses.")
