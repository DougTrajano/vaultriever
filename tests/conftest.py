from collections.abc import Iterator

import pytest

from vaultriever.providers.aws import AWSSecretProvider
from vaultriever.providers.azure import AzureSecretProvider
from vaultriever.providers.gcp import GCPSecretProvider


@pytest.fixture(autouse=True)
def clear_aws_cache() -> Iterator[None]:
    """Keep the AWS lru_cache from leaking state between tests."""
    AWSSecretProvider.clear_cache()
    yield
    AWSSecretProvider.clear_cache()


@pytest.fixture(autouse=True)
def clear_azure_cache() -> Iterator[None]:
    """Keep the Azure lru_cache from leaking state between tests."""
    AzureSecretProvider.clear_cache()
    yield
    AzureSecretProvider.clear_cache()


@pytest.fixture(autouse=True)
def clear_gcp_cache() -> Iterator[None]:
    """Keep the GCP lru_cache from leaking state between tests."""
    GCPSecretProvider.clear_cache()
    yield
    GCPSecretProvider.clear_cache()
