from collections.abc import Iterator
from typing import Any

import pytest

from vaultriever.exceptions import ProviderNotRegisteredError, SecretRetrievalError, SRIParseError
from vaultriever.providers import SecretProviderRegistry
from vaultriever.resolver import resolve_secret
from vaultriever.sri import SecretProperties


class FakeProvider:
    name = 'fakevault'

    def __init__(self, secrets: dict[str, Any]) -> None:
        self.secrets = secrets
        self.calls: list[SecretProperties] = []

    def get_secret_value(self, props: SecretProperties) -> Any:
        self.calls.append(props)
        try:
            return self.secrets[props.secret_key]
        except KeyError:
            raise SecretRetrievalError(f'Key {props.secret_key!r} not found') from None


@pytest.fixture
def fake_provider() -> Iterator[FakeProvider]:
    provider = FakeProvider({'MY_KEY': 'my-value', 'AN_INT': 42})
    SecretProviderRegistry.register(provider)
    yield provider
    SecretProviderRegistry.unregister(provider.name)


class TestResolveSecret:
    def test_dispatch(self, fake_provider: FakeProvider) -> None:
        assert resolve_secret('fakevault:us-east-1:my-secret:MY_KEY') == 'my-value'
        assert fake_provider.calls == [
            SecretProperties('fakevault', 'us-east-1', 'my-secret', 'MY_KEY')
        ]

    def test_returns_string(self, fake_provider: FakeProvider) -> None:
        assert resolve_secret('fakevault::my-secret:AN_INT') == '42'

    def test_unknown_provider(self) -> None:
        with pytest.raises(ProviderNotRegisteredError, match="'nope'"):
            resolve_secret('nope:region:name:key')

    def test_malformed_sri(self) -> None:
        with pytest.raises(SRIParseError):
            resolve_secret('not-an-sri')

    def test_provider_error_propagates(self, fake_provider: FakeProvider) -> None:
        with pytest.raises(SecretRetrievalError, match='MISSING'):
            resolve_secret('fakevault::my-secret:MISSING')


class TestRegistry:
    def test_available_providers_includes_defaults(self) -> None:
        available = SecretProviderRegistry.available_providers()
        assert {'aws', 'azure', 'databricks', 'gcp'} <= set(available)

    def test_register_and_unregister(self) -> None:
        provider = FakeProvider({})
        SecretProviderRegistry.register(provider)
        assert SecretProviderRegistry.is_registered('fakevault')
        assert SecretProviderRegistry.get('fakevault') is provider

        SecretProviderRegistry.unregister('fakevault')
        assert not SecretProviderRegistry.is_registered('fakevault')
