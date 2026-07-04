"""Provider interface and registry."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from vaultriever.exceptions import ProviderNotRegisteredError
from vaultriever.logging import get_logger
from vaultriever.sri import SecretProperties

logger = get_logger(__name__)


@runtime_checkable
class SecretProvider(Protocol):
    """Minimal interface every secret provider must implement."""

    name: str  # e.g. "aws", "databricks"

    def get_secret_value(self, props: SecretProperties) -> Any: ...


class SecretProviderRegistry:
    """Registry of available secret providers, keyed by provider name."""

    _providers: dict[str, SecretProvider] = {}

    @classmethod
    def register(cls, provider: SecretProvider) -> None:
        """Register a provider under its ``name``, replacing any existing one."""
        logger.debug('Registering secret provider %r', provider.name)
        cls._providers[provider.name] = provider

    @classmethod
    def get(cls, name: str) -> SecretProvider:
        """Return the provider registered under ``name``.

        Raises:
            ProviderNotRegisteredError: If no provider is registered.
        """
        try:
            return cls._providers[name]
        except KeyError:
            raise ProviderNotRegisteredError(
                f'No secret provider registered for {name!r}. '
                f'Available providers: {cls.available_providers()}'
            ) from None

    @classmethod
    def unregister(cls, name: str) -> None:
        """Remove a provider from the registry; no-op if not registered."""
        cls._providers.pop(name, None)

    @classmethod
    def is_registered(cls, name: str) -> bool:
        return name in cls._providers

    @classmethod
    def available_providers(cls) -> list[str]:
        return sorted(cls._providers)
