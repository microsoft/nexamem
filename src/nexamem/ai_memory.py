from collections import defaultdict
from typing import TYPE_CHECKING

from lagom import Container

from nexamem.channels.channel_factory import ChannelFactory
from nexamem.schemas.memory_entry import MemoryEntry
from nexamem.schemas.memory_filter import MemoryFilter

if TYPE_CHECKING:
    from nexamem.channels.channel import Channel
    from nexamem.storage_adapters.i_storage_adapter import IStorageAdapter


class AIMemory:
    def __init__(self, channel_factory: ChannelFactory):
        # initialize this with a Ichannelfactory and do DI stuff with the factory stuff

        #TODO: figure out how to get the yaml file location
        # channel_factory = ChannelFactory()
        self._channels: list[Channel] = channel_factory.load_from_yaml("path/to/your/config.yaml")

        # read yaml config file from predetermined location

    @staticmethod
    def create(container:Container|None = None, config_object = None, path_to_config: str|None = None) -> 'AIMemory':
        """
        Static method to create an instance of AIMemory.
        This can be used to initialize the AIMemory with a specific configuration.
        """

        if not container:
            container = Container()

        container = AIMemory.register_deps(container)


        if not path_to_config:
            raise ValueError("Path to configuration file must be provided.")


        return container[AIMemory]

    @staticmethod
    def register_deps(container: Container) -> Container:

        # wire up DI dependencies if needed
        # check if stuff is already registered in the container
        # if not, register the necessary components

        return container


    async def write(self, entries: list[MemoryEntry]) -> None:

        # loop the entries and write each one, handle pii, ttl etc as needed
        # group by channel and write in batches (pipelining)

        grouped_entries: defaultdict[str,list[MemoryEntry]] = defaultdict(list)
        for entry in entries:
            grouped_entries[entry.channel_name].append(entry)

        for channel_name, entries in grouped_entries.items():
            channel = next(
                (c for c in self._channels if c.name == channel_name), None)
            if not channel:
                raise ValueError(f"Channel '{channel_name}' not found. Please register the channel first.")

            #TODO: implement logic to handle PII, TTL, etc.

            storage: IStorageAdapter = channel.storage

            await storage.write(entries)


    async def read(self, filter: MemoryFilter) -> list[MemoryEntry]:

        records: list[MemoryEntry] = []
        for channel_name in filter.channel_names:
            channel = next((c for c in self._channels if c.name == channel_name), None)
            if not channel:
                raise ValueError(f"Channel '{channel_name}' not found. Please register the channel first.")
            storage: IStorageAdapter = channel.storage
            entries = await storage.read(filter)
            records.extend(entries)

        return records

    # def register_channel(self, name: str, *, ttl_sec: int, encrypt: bool, quota_bytes: int | None = None, storage: IStorageAdapter) -> None
