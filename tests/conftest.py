from collections.abc import Iterator

import pytest

from vaultriever.providers.aws import AWSSecretProvider


@pytest.fixture(autouse=True)
def clear_aws_cache() -> Iterator[None]:
    """Keep the AWS lru_cache from leaking state between tests."""
    AWSSecretProvider.clear_cache()
    yield
    AWSSecretProvider.clear_cache()
