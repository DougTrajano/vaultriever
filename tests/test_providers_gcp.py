import sys
import types
from collections.abc import Callable
from typing import Any, cast

import pytest

from vaultriever.exceptions import SecretRetrievalError
from vaultriever.providers.gcp import GCPSecretProvider, _get_gcp_secret_value
from vaultriever.sri import parse_sri

PROJECT = 'my-project'


class FakePayload:
    def __init__(self, data: bytes) -> None:
        self.data = data


class FakeResponse:
    def __init__(self, data: bytes) -> None:
        self.payload = FakePayload(data)


def _install_fake_gcp_sdk(
    monkeypatch: pytest.MonkeyPatch, access_secret_version: Callable[[str], FakeResponse]
) -> None:
    fake_google = types.ModuleType('google')
    fake_google.__path__ = []
    fake_cloud = types.ModuleType('google.cloud')
    fake_cloud.__path__ = []
    fake_secretmanager = types.ModuleType('google.cloud.secretmanager')

    class FakeSecretManagerServiceClient:
        def access_secret_version(self, request: dict[str, str]) -> FakeResponse:
            return access_secret_version(request['name'])

    cast(Any, fake_secretmanager).SecretManagerServiceClient = FakeSecretManagerServiceClient

    monkeypatch.setitem(sys.modules, 'google', fake_google)
    monkeypatch.setitem(sys.modules, 'google.cloud', fake_cloud)
    monkeypatch.setitem(sys.modules, 'google.cloud.secretmanager', fake_secretmanager)


@pytest.fixture
def provider() -> GCPSecretProvider:
    return GCPSecretProvider()


class TestGCPSecretProvider:
    def test_latest_version_builds_expected_resource_name(
        self, provider: GCPSecretProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[str] = []

        def access_secret_version(name: str) -> FakeResponse:
            calls.append(name)
            return FakeResponse(b'super-secret-value')

        _install_fake_gcp_sdk(monkeypatch, access_secret_version)
        props = parse_sri(f'gcp:{PROJECT}:my-secret:latest')

        assert provider.get_secret_value(props) == 'super-secret-value'
        assert calls == ['projects/my-project/secrets/my-secret/versions/latest']

    def test_explicit_version_is_used_in_resource_name(
        self, provider: GCPSecretProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[str] = []

        def access_secret_version(name: str) -> FakeResponse:
            calls.append(name)
            return FakeResponse(b'versioned-value')

        _install_fake_gcp_sdk(monkeypatch, access_secret_version)
        props = parse_sri(f'gcp:{PROJECT}:my-secret:3')

        assert provider.get_secret_value(props) == 'versioned-value'
        assert calls == ['projects/my-project/secrets/my-secret/versions/3']

    def test_missing_project_id_raises(self, provider: GCPSecretProvider) -> None:
        props = parse_sri('gcp::my-secret:latest')
        with pytest.raises(SecretRetrievalError, match='non-empty project id'):
            provider.get_secret_value(props)

    def test_sdk_error_is_wrapped_and_does_not_leak_value(
        self, provider: GCPSecretProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def access_secret_version(name: str) -> FakeResponse:
            raise RuntimeError('secret-value-should-not-leak')

        _install_fake_gcp_sdk(monkeypatch, access_secret_version)
        props = parse_sri(f'gcp:{PROJECT}:my-secret:latest')

        with pytest.raises(SecretRetrievalError) as excinfo:
            provider.get_secret_value(props)
        assert 'secret-value-should-not-leak' not in str(excinfo.value)
        assert 'my-secret' in str(excinfo.value)
        assert PROJECT in str(excinfo.value)

    def test_caching(self, provider: GCPSecretProvider, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[str] = []

        def access_secret_version(name: str) -> FakeResponse:
            calls.append(name)
            return FakeResponse(b'value')

        _install_fake_gcp_sdk(monkeypatch, access_secret_version)
        props = parse_sri(f'gcp:{PROJECT}:my-secret:latest')

        provider.get_secret_value(props)
        info = _get_gcp_secret_value.cache_info()
        assert info.misses == 1

        provider.get_secret_value(props)
        info = _get_gcp_secret_value.cache_info()
        assert info.hits == 1
        assert info.misses == 1
        assert len(calls) == 1

    def test_clear_cache(
        self, provider: GCPSecretProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def access_secret_version(name: str) -> FakeResponse:
            return FakeResponse(b'value')

        _install_fake_gcp_sdk(monkeypatch, access_secret_version)
        props = parse_sri(f'gcp:{PROJECT}:my-secret:latest')

        provider.get_secret_value(props)
        GCPSecretProvider.clear_cache()
        provider.get_secret_value(props)
        assert _get_gcp_secret_value.cache_info().misses == 1

    def test_missing_sdk_raises_helpful_error(
        self, provider: GCPSecretProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delitem(sys.modules, 'google.cloud.secretmanager', raising=False)
        import builtins

        real_import = builtins.__import__

        def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == 'google.cloud':
                raise ImportError("No module named 'google.cloud.secretmanager'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, '__import__', fake_import)
        props = parse_sri(f'gcp:{PROJECT}:my-secret:latest')

        with pytest.raises(SecretRetrievalError, match='vaultriever\\[gcp\\]'):
            provider.get_secret_value(props)
