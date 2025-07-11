"""Dependency injection container for NexaMem."""

from typing import Any, Dict, List, Optional, Type, TypeVar

from .providers import ServiceProvider

T = TypeVar('T')


class ServiceRegistry:
    """Registry for managing service providers."""

    def __init__(self):
        self._providers: Dict[Type, ServiceProvider] = {}

    def register(self, service_type: Type, provider: ServiceProvider) -> None:
        """Register a service provider for a given type."""
        self._providers[service_type] = provider

    def get_provider(self, service_type: Type) -> Optional[ServiceProvider]:
        """Get the provider for a service type."""
        return self._providers.get(service_type)

    def unregister(self, service_type: Type) -> None:
        """Unregister a service type."""
        if service_type in self._providers:
            del self._providers[service_type]

    def clear(self) -> None:
        """Clear all registered providers."""
        self._providers.clear()

    def list_registered_types(self) -> List[Type]:
        """Get a list of all registered service types."""
        return list(self._providers.keys())


class DIContainer:
    """Dependency injection container."""

    def __init__(self):
        self._registry = ServiceRegistry()
        self._config: Dict[str, Any] = {}

    @property
    def registry(self) -> ServiceRegistry:
        """Get the service registry."""
        return self._registry

    def set_config(self, config: Dict[str, Any]) -> None:
        """Set the global configuration."""
        self._config = config

    def get_config(self, key: Optional[str] = None) -> Any:
        """Get configuration value(s)."""
        if key is None:
            return self._config
        return self._config.get(key)

    def register(self, service_type: Type, provider: ServiceProvider) -> None:
        """Register a service with its provider."""
        self._registry.register(service_type, provider)

    def resolve(self, service_type: Type[T], config: Optional[Dict[str, Any]] = None) -> T:
        """Resolve a service instance."""
        provider = self._registry.get_provider(service_type)
        if provider is None:
            raise ValueError(f"No provider registered for service type {service_type}")

        # Merge global config with provided config
        merged_config = self._config.copy()
        if config:
            merged_config.update(config)

        return provider.provide(service_type, merged_config if merged_config else None)

    def try_resolve(self, service_type: Type[T], config: Optional[Dict[str, Any]] = None) -> Optional[T]:
        """Try to resolve a service instance, returning None if not possible."""
        try:
            return self.resolve(service_type, config)
        except (ValueError, TypeError, AttributeError):
            return None

    def is_registered(self, service_type: Type) -> bool:
        """Check if a service type is registered."""
        provider = self._registry.get_provider(service_type)
        return provider is not None and provider.can_provide(service_type)

    def build_scope(self) -> 'DIContainer':
        """Create a new scoped container that inherits from this one."""
        scoped_container = DIContainer()
        scoped_container._config = self._config.copy()
        # Copy providers (but not instances for singleton providers)
        for service_type, provider in self._registry._providers.items():
            scoped_container.register(service_type, provider)
        return scoped_container
