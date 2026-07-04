"""Secret providers and their registry.

Default providers are registered at import time. Provider SDK dependencies
(boto3, databricks-sdk) are imported lazily on first use, so registration is
safe even when the corresponding extra is not installed.
"""

from __future__ import annotations

from vaultriever.providers.aws import AWSSecretProvider
from vaultriever.providers.base import SecretProvider, SecretProviderRegistry
from vaultriever.providers.databricks import DatabricksSecretProvider

SecretProviderRegistry.register(AWSSecretProvider())
SecretProviderRegistry.register(DatabricksSecretProvider())

__all__ = [
    'AWSSecretProvider',
    'DatabricksSecretProvider',
    'SecretProvider',
    'SecretProviderRegistry',
]
