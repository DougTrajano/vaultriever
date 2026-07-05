"""vaultriever: retrieve secrets in an ARN-like way from different vaults.

Secrets are addressed with a Secret Resource Identifier (SRI)::

    provider:qualifier:secret_name:secret_key
"""

from vaultriever.exceptions import (
    DatabricksConfigurationError,
    ProviderNotRegisteredError,
    SecretRetrievalError,
    SRIParseError,
    VaultrieverError,
)
from vaultriever.providers import SecretProvider, SecretProviderRegistry
from vaultriever.resolver import resolve_secret
from vaultriever.settings_mixin import SecretSRIMixin
from vaultriever.sri import SecretProperties, is_sri, parse_sri

__all__ = [
    'DatabricksConfigurationError',
    'ProviderNotRegisteredError',
    'SecretProperties',
    'SecretProvider',
    'SecretProviderRegistry',
    'SecretRetrievalError',
    'SecretSRIMixin',
    'SRIParseError',
    'VaultrieverError',
    'is_sri',
    'parse_sri',
    'resolve_secret',
]
