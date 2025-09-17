
import yaml
from lagom import Container

from nexamem.channels.channel import Channel
from nexamem.channels.storage_factory import StorageAdapterFactory
from nexamem.storage_adapters.configs.i_storage_adapter_config import IStorageAdapterConfig


class ChannelFactory:
    """
    Factory for creating Channel instances with registered storage adapters.
    """
    def __init__(self, container: Container,config_object):
        """
        Initialize ChannelFactory with a Lagom DI container.

        :param container: Lagom dependency injection container.
        """
        self._container = container

    #keeps list of channels here

    #outsucrse to pydantic settings
    def load_from_yaml(self, yaml_path: str) -> list[Channel]:
        """
        Load channel configurations from a YAML file and create Channel instances.

        :param yaml_path: Path to the YAML configuration file.
        :return: List of Channel instances.
        """
        channels: list[Channel] = []
        with open(yaml_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        for entry in config.get("channels", []):
            name = entry.get("name")
            adapter_type = entry.get("adapter_type")
            #TODO: replace this with an object configuration with env vars
            adapter_config_dict = entry.get("adapter_config", {})
            ttl_sec = entry.get("ttl_sec", 0)
            encrypt = entry.get("encrypt", False)
            # You may need to instantiate the correct config class based on adapter_type
            adapter_config = IStorageAdapterConfig(**adapter_config_dict)
            channel = self.create_channel(name, adapter_type, adapter_config, ttl_sec, encrypt)
            channels.append(channel)
        return channels

    #TODO: do I need to create the channel with a storage adapter that I retreive from the DI container?
    @staticmethod
    def create_channel(name: str, adapter_type: str, adapter_config: IStorageAdapterConfig, ttl_sec: int = 0, encrypt: bool = False) -> Channel:
        """
        Create a Channel with the specified storage adapter.

        :param name: The name of the channel.
        :param adapter_type: The type of storage adapter to use.
        :param adapter_config: The configuration for the storage adapter.
        :param ttl_sec: Time-to-live in seconds for the channel (default: 0).
        :param encrypt: Whether to enable encryption (default: False).
        :return: A Channel instance with the specified storage adapter.
        """
        storage = StorageAdapterFactory.create_adapter(adapter_type, adapter_config)
        return Channel(name=name, ttl_sec=ttl_sec, encrypt=encrypt, storage=storage)
