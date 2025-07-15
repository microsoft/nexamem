from nexamem.schemas.memory_scope import MemoryScope
from pydantic import BaseModel, Field
from typing import Optional, Union


class MemoryEntry(BaseModel):
    """
    Represents a storage record in the Nexamem system.

    Attributes:
        id (str): Unique identifier for the record.
        content (Union[str, bytes]): The content of the record.
        timestamp (int): The time when the record was created or last modified.
        metadata (MemoryScope): Metadata describing the memory scope.
        channel_name (str): Name of the channel associated with this entry.
        source (Optional[str]): Source of the record, if applicable.
        type (Optional[str]): Type of the record, if applicable.
        pii (bool): Indicates if the record contains PII.
        ttl_override (Optional[int]): Override for time-to-live, if applicable.
        auto_pii (bool): Indicates if PII detection is automatic.
    """

    id: str = Field(..., description="Unique identifier for the record.")
    content: Union[str, bytes] = Field(..., description="The content of the record.")
    timestamp: int = Field(..., description="The time when the record was created or last modified.")
    metadata: MemoryScope = Field(..., description="Metadata describing the memory scope.")
    channel_name: str = Field(..., description="Name of the channel associated with this entry.")
    source: Optional[str] = Field(None, description="Source of the record, if applicable.")
    type: Optional[str] = Field(None, description="Type of the record, if applicable.")
    pii: bool = Field(False, description="Indicates if the record contains PII.")
    ttl_override: Optional[int] = Field(None, description="Override for time-to-live, if applicable.")
    auto_pii: bool = Field(False, description="Indicates if PII detection is automatic.")