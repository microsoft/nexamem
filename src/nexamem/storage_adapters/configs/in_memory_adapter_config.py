from nexamem.storage_adapters.configs.i_storage_adapter_config import IStorageAdapterConfig


class InMemoryAdapterConfig(IStorageAdapterConfig):
    """
    Configuration class for the in-memory storage adapter.
    This class is used to define the configuration parameters for the in-memory storage adapter.
    """

    def __init__(self):
        self.name = "in_memory"
        self.description = "In-memory storage adapter for testing purposes."
        self.type = "in_memory"
        self.config = {}