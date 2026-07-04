"""Secret providers and their registry.

Default providers are registered at import time. Provider SDK dependencies
(boto3, databricks-sdk) are imported lazily on first use, so registration is
safe even when the corresponding extra is not installed.
"""

from __future__ import annotations

from vaultriever.providers.aws import AWSSecretProvider
from vaultriever.providers.azure import AzureSecretProvider
from vaultriever.providers.base import SecretProvider, SecretProviderRegistry
from vaultriever.providers.databricks import DatabricksSecretProvider
from vaultriever.providers.gcp import GCPSecretProvider

SecretProviderRegistry.register(AWSSecretProvider())
SecretProviderRegistry.register(DatabricksSecretProvider())
SecretProviderRegistry.register(AzureSecretProvider())
SecretProviderRegistry.register(GCPSecretProvider())

__all__ = [
    'AWSSecretProvider',
    'AzureSecretProvider',
    'DatabricksSecretProvider',
    'GCPSecretProvider',
    'SecretProvider',
    'SecretProviderRegistry',
]
