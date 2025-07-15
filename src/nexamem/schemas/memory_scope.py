from pydantic import BaseModel, Field


class MemoryScope(BaseModel):
    agent_id: str = Field(..., description="ID of the agent.")
    user_id: str = Field(..., description="ID of the user.")
    session_id: str = Field(..., description="ID of the session.")
    env: str = Field(..., description="Environment identifier.")
