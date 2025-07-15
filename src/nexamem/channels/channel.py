from pydantic import BaseModel, Field

from nexamem.storage_adapters.i_storage_adapter import IStorageAdapter


class Channel(BaseModel):

    name:str = Field(description="The name of the channel.")
    ttl_sec: int = 0
    encrypt: bool = False
    storage: IStorageAdapter
