from nexamem.schemas.memory_scope import MemoryScope
from pydantic import BaseModel


class StorageRecord(BaseModel):
    """
    Represents a storage record in the Nexamem system.
    
    Attributes:
        id (str): Unique identifier for the record.
        data (str): The content of the record.
        timestamp (int): The time when the record was created or last modified.
    """

    def __init__(self, id: str, content: str | bytes, timestamp: int, metadata: MemoryScope, channel: str):
        self.id = id
        self.content = content
        self.timestamp = timestamp
        self.metadata = metadata
        self.channel = channel