from nexamem.schemas.memory_scope import MemoryScope
from nexamem.schemas.storage_record import StorageRecord
from nexamem.storage_adapters.configs.i_storage_adapter_config import IStorageAdapterConfig
from nexamem.storage_adapters.i_storage_adapter import IStorageAdapter

class AIMemory:
    def __init__(self, storage: IStorageAdapter):
        self._storage = storage


    def write(self, scope: MemoryScope, channel: str,
              content: str | bytes, *,
              pii: bool = False,
              ttl_override: int | None = None,
              auto_pii: bool = False) -> str:
        
        if pii:
            # encrypt PII content
            content = f"PII: {content}"
                    
        # add memory scope metadata to content
        created_id = self._storage.write(content, memory_scope=scope, channel=channel)
        return created_id

    def read(self, scope: MemoryScope, channel: str, *,
             since_sec: int | None = None,
             max_msgs: int | None = None) -> list[StorageRecord]:
        
        records: list[StorageRecord] = []
        if since_sec is not None:
            records = self._storage.read_since(since_sec, memory_scope=scope, channel=channel)
        
        if max_msgs is not None:
            # Read the last N records
            return self._storage.read_last_n_records(max_msgs, memory_scope=scope, channel=channel)
        
        return records

    # def checkpoint(self, scope: MemoryScope, key: str, payload: dict) -> None

    # def checkpoint_atomic(self, scope: MemoryScope, key: str,
    #                       update_fn: Callable[[dict | None], dict]) -> dict

    # def bulk_erase(self, scope: MemoryScope) -> int
    # def count_bytes(self, scope: MemoryScope, channel: str) -> int
    # def register_channel(self, name: str, *, ttl_sec: int, encrypt: bool, quota_bytes: int | None = None) -> None
