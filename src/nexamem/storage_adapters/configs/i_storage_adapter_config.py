class IStorageAdapterConfig:
    """
    Interface for storage adapter configuration.
    """

    def get_storage_type(self) -> str:
        """
        Returns the type of storage (e.g., 'local', 's3', etc.).
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    def get_connection_details(self) -> dict:
        """
        Returns connection details required to connect to the storage.
        """
        raise NotImplementedError("This method should be overridden by subclasses.")