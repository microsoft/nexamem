"""
MemoryScope defines the key structure for AIMemory operations.
"""
from pydantic import BaseModel, Field
import uuid


class MemoryScope(BaseModel):
    """
    Defines the scope for memory operations with hierarchical key structure.
    Key format: {env}:{agent_id}:{user_id}:{session_id}:{channel}:{uuid}
    """
    
    agent_id: str = Field(..., description="Agent identifier (e.g., 'invest_agent')")
    user_id: str = Field(..., description="Hashed customer/user identifier")
    session_id: str = Field(..., description="Chat session UUID")
    env: str = Field(default="prod", description="Environment (dev/stg/prod)")
    
    def __init__(self, **data):
        # Auto-generate session_id if not provided
        if 'session_id' not in data or not data['session_id']:
            data['session_id'] = str(uuid.uuid4())
        super().__init__(**data)
    
    def get_key_prefix(self, channel: str) -> str:
        """
        Generate the Redis key prefix for this scope and channel.
        Format: {env}:{agent_id}:{user_id}:{session_id}:{channel}
        """
        return f"{self.env}:{self.agent_id}:{self.user_id}:{self.session_id}:{channel}"
    
    def get_index_key(self, channel: str) -> str:
        """
        Generate the sorted-set index key for this scope and channel.
        Format: {env}:{agent_id}:{user_id}:{session_id}:{channel}:index
        """
        return f"{self.get_key_prefix(channel)}:index"
    
    def model_dump_dict(self) -> dict:
        """Return dictionary representation of the scope."""
        return self.model_dump()
