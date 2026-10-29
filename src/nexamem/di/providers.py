"""Service provider interface for dependency injection."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, TypeVar, cast

T = TypeVar("T")


class ServiceProvider(ABC):
    """Abstract base class for service providers."""

    @abstractmethod
    def provide(self, service_type: Callable[..., T], config: dict[str, Any] | None = None) -> T:
        """Provide an instance of the requested service type."""
        pass

    @abstractmethod
    def can_provide(self, service_type: Callable[..., object]) -> bool:
        """Check if this provider can provide the requested service type."""
        pass


class SingletonProvider(ServiceProvider):
    """Provider that maintains singleton instances."""

    def __init__(self) -> None:
        self._instances: dict[Callable[..., object], object] = {}

    def provide(self, service_type: Callable[..., T], config: dict[str, Any] | None = None) -> T:
        """Provide a singleton instance."""
        if service_type not in self._instances:
            if not self.can_provide(service_type):
                raise ValueError(f"Cannot provide service of type {service_type}")
            self._instances[service_type] = self._create_instance(service_type, config)
        return cast("T", self._instances[service_type])

    def can_provide(self, service_type: Callable[..., object]) -> bool:
        """Check if this provider can create the service type."""
        return hasattr(self, "_create_instance")

    def _create_instance(self, service_type: Callable[..., T], config: dict[str, Any] | None) -> T:
        """Create a new instance. Should be overridden by subclasses."""
        if config:
            return service_type(**config)
        return service_type()


class TransientProvider(ServiceProvider):
    """Provider that creates new instances each time."""

    def provide(self, service_type: Callable[..., T], config: dict[str, Any] | None = None) -> T:
        """Provide a new instance."""
        if not self.can_provide(service_type):
            raise ValueError(f"Cannot provide service of type {service_type}")
        return self._create_instance(service_type, config)

    def can_provide(self, service_type: Callable[..., object]) -> bool:
        """Check if this provider can create the service type."""
        return hasattr(self, "_create_instance")

    def _create_instance(self, service_type: Callable[..., T], config: dict[str, Any] | None) -> T:
        """Create a new instance. Should be overridden by subclasses."""
        if config:
            return service_type(**config)
        return service_type()


class FactoryProvider(ServiceProvider):
    """Provider that uses a factory function to create instances."""

    def __init__(
        self,
        factory_func: Callable[[Callable[..., object], dict[str, Any] | None], object],
        singleton: bool = False,
    ) -> None:
        self._factory_func = factory_func
        self._singleton = singleton
        self._instance: object | None = None

    def provide(self, service_type: Callable[..., T], config: dict[str, Any] | None = None) -> T:
        """Provide an instance using the factory function."""
        if self._singleton and self._instance is not None:
            return cast("T", self._instance)

        instance = self._factory_func(service_type, config)

        if self._singleton:
            self._instance = instance

        return cast("T", instance)

    def can_provide(self, service_type: Callable[..., object]) -> bool:
        """This provider can provide any service type via its factory function."""
        return callable(self._factory_func)
