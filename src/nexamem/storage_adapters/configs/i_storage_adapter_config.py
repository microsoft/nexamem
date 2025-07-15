from typing import Any


class IStorageAdapterConfig:
    """
    Interface for storage adapter configuration.
    """
    def __init__(self, **kwargs: Any):
        """
        Initialize the storage adapter configuration with given parameters.

        :param kwargs: Configuration parameters for the storage adapter.
        """
        # for key, value in kwargs.items():
        #     setattr(self, key, value)

        raise NotImplementedError("This method should be overridden by subclasses.")
