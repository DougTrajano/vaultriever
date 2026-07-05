import sys
import types
from typing import Any, cast

import pytest

from vaultriever.exceptions import SecretRetrievalError
from vaultriever.providers.azure import AzureSecretProvider, _get_azure_secret_value
from vaultriever.sri import parse_sri

VAULT = 'my-vault'


class FakeSecret:
    def __init__(self, value: str) -> None:
        self.value = value


def _install_fake_azure_sdk(
    monkeypatch: pytest.MonkeyPatch,
    get_secret: Any,
    credential_calls: list[None] | None = None,
) -> None:
    fake_azure = types.ModuleType('azure')
    fake_azure.__path__ = []

    fake_identity = types.ModuleType('azure.identity')

    class FakeDefaultAzureCredential:
        def __init__(self) -> None:
            if credential_calls is not None:
                credential_calls.append(None)

    cast(Any, fake_identity).DefaultAzureCredential = FakeDefaultAzureCredential

    fake_keyvault = types.ModuleType('azure.keyvault')
    fake_keyvault.__path__ = []
    fake_secrets = types.ModuleType('azure.keyvault.secrets')

    class FakeSecretClient:
        def __init__(self, vault_url: str, credential: Any) -> None:
            self.vault_url = vault_url
            self.credential = credential

        def get_secret(self, name: str, version: str | None = None) -> Any:
            return get_secret(name, version)

    cast(Any, fake_secrets).SecretClient = FakeSecretClient

    monkeypatch.setitem(sys.modules, 'azure', fake_azure)
    monkeypatch.setitem(sys.modules, 'azure.identity', fake_identity)
    monkeypatch.setitem(sys.modules, 'azure.keyvault', fake_keyvault)
    monkeypatch.setitem(sys.modules, 'azure.keyvault.secrets', fake_secrets)


@pytest.fixture
def provider() -> AzureSecretProvider:
    return AzureSecretProvider()


class TestAzureSecretProvider:
    def test_latest_version_calls_get_secret_without_version(
        self, provider: AzureSecretProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[tuple[str, str | None]] = []

        def get_secret(name: str, version: str | None) -> FakeSecret:
            calls.append((name, version))
            return FakeSecret('super-secret-value')

        _install_fake_azure_sdk(monkeypatch, get_secret)
        props = parse_sri(f'azure:{VAULT}:my-secret:latest')

        assert provider.get_secret_value(props) == 'super-secret-value'
        assert calls == [('my-secret', None)]

    def test_explicit_version_is_passed_through(
        self, provider: AzureSecretProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[tuple[str, str | None]] = []

        def get_secret(name: str, version: str | None) -> FakeSecret:
            calls.append((name, version))
            return FakeSecret('versioned-value')

        _install_fake_azure_sdk(monkeypatch, get_secret)
        props = parse_sri(f'azure:{VAULT}:my-secret:abc123')

        assert provider.get_secret_value(props) == 'versioned-value'
        assert calls == [('my-secret', 'abc123')]

    def test_vault_url_is_built_from_vault_name(
        self, provider: AzureSecretProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen_vault_urls: list[str] = []
        fake_azure = types.ModuleType('azure')
        fake_azure.__path__ = []
        fake_identity = types.ModuleType('azure.identity')

        class FakeDefaultAzureCredential:
            pass

        cast(Any, fake_identity).DefaultAzureCredential = FakeDefaultAzureCredential

        fake_keyvault = types.ModuleType('azure.keyvault')
        fake_keyvault.__path__ = []
        fake_secrets = types.ModuleType('azure.keyvault.secrets')

        class FakeSecretClient:
            def __init__(self, vault_url: str, credential: Any) -> None:
                seen_vault_urls.append(vault_url)

            def get_secret(self, name: str, version: str | None = None) -> FakeSecret:
                return FakeSecret('value')

        cast(Any, fake_secrets).SecretClient = FakeSecretClient
        monkeypatch.setitem(sys.modules, 'azure', fake_azure)
        monkeypatch.setitem(sys.modules, 'azure.identity', fake_identity)
        monkeypatch.setitem(sys.modules, 'azure.keyvault', fake_keyvault)
        monkeypatch.setitem(sys.modules, 'azure.keyvault.secrets', fake_secrets)

        props = parse_sri(f'azure:{VAULT}:my-secret:latest')
        provider.get_secret_value(props)

        assert seen_vault_urls == ['https://my-vault.vault.azure.net/']

    def test_missing_vault_name_raises(self, provider: AzureSecretProvider) -> None:
        props = parse_sri('azure::my-secret:latest')
        with pytest.raises(SecretRetrievalError, match='non-empty vault name'):
            provider.get_secret_value(props)

    def test_missing_version_raises(self, provider: AzureSecretProvider) -> None:
        props = parse_sri(f'azure:{VAULT}:my-secret:')
        with pytest.raises(SecretRetrievalError, match='non-empty version'):
            provider.get_secret_value(props)

    def test_sdk_error_is_wrapped_and_does_not_leak_value(
        self, provider: AzureSecretProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def get_secret(name: str, version: str | None) -> FakeSecret:
            raise RuntimeError('secret-value-should-not-leak')

        _install_fake_azure_sdk(monkeypatch, get_secret)
        props = parse_sri(f'azure:{VAULT}:my-secret:latest')

        with pytest.raises(SecretRetrievalError) as excinfo:
            provider.get_secret_value(props)
        assert 'secret-value-should-not-leak' not in str(excinfo.value)
        assert 'my-secret' in str(excinfo.value)
        assert VAULT in str(excinfo.value)

    def test_caching(self, provider: AzureSecretProvider, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[tuple[str, str | None]] = []

        def get_secret(name: str, version: str | None) -> FakeSecret:
            calls.append((name, version))
            return FakeSecret('value')

        _install_fake_azure_sdk(monkeypatch, get_secret)
        props = parse_sri(f'azure:{VAULT}:my-secret:latest')

        provider.get_secret_value(props)
        info = _get_azure_secret_value.cache_info()
        assert info.misses == 1

        provider.get_secret_value(props)
        info = _get_azure_secret_value.cache_info()
        assert info.hits == 1
        assert info.misses == 1
        assert len(calls) == 1

    def test_clear_cache(
        self, provider: AzureSecretProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def get_secret(name: str, version: str | None) -> FakeSecret:
            return FakeSecret('value')

        _install_fake_azure_sdk(monkeypatch, get_secret)
        props = parse_sri(f'azure:{VAULT}:my-secret:latest')

        provider.get_secret_value(props)
        AzureSecretProvider.clear_cache()
        provider.get_secret_value(props)
        assert _get_azure_secret_value.cache_info().misses == 1

    def test_missing_sdk_raises_helpful_error(
        self, provider: AzureSecretProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delitem(sys.modules, 'azure.identity', raising=False)
        monkeypatch.delitem(sys.modules, 'azure.keyvault.secrets', raising=False)
        import builtins

        real_import = builtins.__import__

        def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name in {'azure.identity', 'azure.keyvault.secrets'}:
                raise ImportError(f'No module named {name!r}')
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, '__import__', fake_import)
        props = parse_sri(f'azure:{VAULT}:my-secret:latest')

        with pytest.raises(SecretRetrievalError, match='vaultriever\\[azure\\]'):
            provider.get_secret_value(props)
