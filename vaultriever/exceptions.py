"""Package-specific exceptions.

Error messages must never contain secret values. Including the SRI's
secret_name/region is fine; the resolved value is not.
"""

from __future__ import annotations


class VaultrieverError(Exception):
    """Base class for all vaultriever errors."""


class SRIParseError(VaultrieverError, ValueError):
    """Raised when a string is not a valid Secret Resource Identifier."""


class ProviderNotRegisteredError(VaultrieverError, LookupError):
    """Raised when an SRI references a provider that is not registered."""


class SecretRetrievalError(VaultrieverError):
    """Raised when a provider fails to retrieve or decode a secret."""


class DatabricksConfigurationError(SecretRetrievalError):
    """Raised when the Databricks provider cannot build a usable context."""
