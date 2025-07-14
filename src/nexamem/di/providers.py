"""Service provider interface for dependency injection."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar

T = TypeVar('T')


class ServiceProvider(ABC):
    """Abstract base class for service providers."""

    @abstractmethod
    def provide(self, service_type: Type[T], config: Optional[Dict[str, Any]] = None) -> T:
        """Provide an instance of the requested service type."""
        pass

    @abstractmethod
    def can_provide(self, service_type: Type) -> bool:
        """Check if this provider can provide the requested service type."""
        pass


class SingletonProvider(ServiceProvider):
    """Provider that maintains singleton instances."""

    def __init__(self):
        self._instances: Dict[Type, Any] = {}

    def provide(self, service_type: Type[T], config: Optional[Dict[str, Any]] = None) -> T:
        """Provide a singleton instance."""
        if service_type not in self._instances:
            if not self.can_provide(service_type):
                raise ValueError(f"Cannot provide service of type {service_type}")
            self._instances[service_type] = self._create_instance(service_type, config)
        return self._instances[service_type]

    def can_provide(self, service_type: Type) -> bool:
        """Check if this provider can create the service type."""
        return hasattr(self, '_create_instance')

    def _create_instance(self, service_type: Type[T], config: Optional[Dict[str, Any]]) -> T:
        """Create a new instance. Should be overridden by subclasses."""
        if config:
            return service_type(**config)
        return service_type()


class TransientProvider(ServiceProvider):
    """Provider that creates new instances each time."""

    def provide(self, service_type: Type[T], config: Optional[Dict[str, Any]] = None) -> T:
        """Provide a new instance."""
        if not self.can_provide(service_type):
            raise ValueError(f"Cannot provide service of type {service_type}")
        return self._create_instance(service_type, config)

    def can_provide(self, service_type: Type) -> bool:
        """Check if this provider can create the service type."""
        return hasattr(self, '_create_instance')

    def _create_instance(self, service_type: Type[T], config: Optional[Dict[str, Any]]) -> T:
        """Create a new instance. Should be overridden by subclasses."""
        if config:
            return service_type(**config)
        return service_type()


class FactoryProvider(ServiceProvider):
    """Provider that uses a factory function to create instances."""

    def __init__(self, factory_func: callable, singleton: bool = False):
        self._factory_func = factory_func
        self._singleton = singleton
        self._instance = None

    def provide(self, service_type: Type[T], config: Optional[Dict[str, Any]] = None) -> T:
        """Provide an instance using the factory function."""
        if self._singleton and self._instance is not None:
            return self._instance

        instance = self._factory_func(service_type, config)

        if self._singleton:
            self._instance = instance

        return instance

    def can_provide(self, service_type: Type) -> bool:
        """This provider can provide any service type via its factory function."""
        return callable(self._factory_func)
