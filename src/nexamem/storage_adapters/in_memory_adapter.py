import time
import uuid

from nexamem.schemas.memory_entry import MemoryEntry
from nexamem.storage_adapters.configs.i_storage_adapter_config import IStorageAdapterConfig
from nexamem.storage_adapters.i_storage_adapter import IStorageAdapter


class InMemoryAdapter(IStorageAdapter):
    def __init__(self, config: IStorageAdapterConfig):
        """Initialize the in-memory storage adapter."""
        self._data: list[MemoryEntry] = []

    async def write(self, entries: list[MemoryEntry]) -> None:
        """Create a new data entry in memory."""

        str(uuid.uuid4())
        int(time.time())

        self._data.extend(entries)

    def read_since(self, since_sec: int, channel:str) -> list[MemoryEntry]:
        """Read records created since a specific timestamp."""
        return [record for record in self._data if record.timestamp >= since_sec]

    def read_last_n_records(self, number_of_records: int, channel: str) -> list[MemoryEntry]:
        """Read the last N records from the in-memory storage."""
        records = self._data[-number_of_records:]
        return records
