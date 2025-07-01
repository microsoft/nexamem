from typing import Any, Optional
from nexamem.schemas.memory_scope import MemoryScope
from nexamem.schemas.storage_record import StorageRecord
from nexamem.storage_adapters.configs.i_storage_adapter_config import IStorageAdapterConfig
from nexamem.storage_adapters.i_storage_adapter import IStorageAdapter
import uuid
import time


class InMemoryAdapter(IStorageAdapter):
    def __init__(self, config: IStorageAdapterConfig):
        """Initialize the in-memory storage adapter."""
        self._data: list[StorageRecord] = list()

    def write(self, data: str | bytes, memory_scope: MemoryScope) -> str:
        """Create a new data entry in memory."""

        id = str(uuid.uuid4())
        timestamp = int(time.time())
        storage_record = StorageRecord(
            id=id,
            content=data,
            timestamp=timestamp,
            metadata=memory_scope
        )

        self._data.append(storage_record)
        return id
    
    def read_since(self, since_sec: int) -> list[StorageRecord]:
        """Read records created since a specific timestamp."""
        return [record for record in self._data if record.timestamp >= since_sec]
    
    def read_last_n_records(self, number_of_records: int) -> list[StorageRecord]:
        """Read the last N records from the in-memory storage."""
        records = self._data[-number_of_records:]
        return records
