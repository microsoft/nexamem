from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class MemoryFilter(BaseModel):
    session: str = Field(..., description="Session identifier.")
    source: str = Field(..., description="Source of the memory entry.")
    type: str = Field(..., description="Type of the memory entry.")
    starting_timestamp: Optional[datetime] = Field(None, description="Start timestamp as datetime.")
    ending_timestamp: Optional[datetime] = Field(None, description="End timestamp as datetime.")
    channel_names: List[str] = Field(..., description="List of channel names to filter.")
    max_msgs: Optional[int] = Field(None, description="Maximum number of messages to retrieve.")

