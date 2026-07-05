import sys
import types
from typing import Any, cast

import pytest

from vaultriever.exceptions import SecretRetrievalError
from vaultriever.providers import databricks as databricks_module
from vaultriever.providers.databricks import (
    DatabricksContext,
    DatabricksSecretProvider,
    resolve_databricks_context,
)
from vaultriever.sri import parse_sri


class TestResolveDatabricksContext:
    def test_none_qualifier_is_default(self) -> None:
        assert resolve_databricks_context(None) == DatabricksContext(profile=None)

    def test_empty_qualifier_is_default(self) -> None:
        assert resolve_databricks_context('') == DatabricksContext(profile=None)

    def test_qualifier_maps_to_profile(self) -> None:
        assert resolve_databricks_context('staging') == DatabricksContext(profile='staging')


class TestDatabricksSecretProvider:
    def test_default_context(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[tuple[DatabricksContext, str, str]] = []

        def fake_get_secret(context: DatabricksContext, scope: str, key: str) -> str:
            calls.append((context, scope, key))
            return 'resolved-value'

        monkeypatch.setattr(databricks_module, '_get_secret', fake_get_secret)
        provider = DatabricksSecretProvider()
        props = parse_sri('databricks::my-scope:MY_KEY')

        assert provider.get_secret_value(props) == 'resolved-value'
        assert calls == [(DatabricksContext(profile=None), 'my-scope', 'MY_KEY')]

    def test_profile_context(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[tuple[DatabricksContext, str, str]] = []

        def fake_get_secret(context: DatabricksContext, scope: str, key: str) -> str:
            calls.append((context, scope, key))
            return 'resolved-value'

        monkeypatch.setattr(databricks_module, '_get_secret', fake_get_secret)
        provider = DatabricksSecretProvider()
        props = parse_sri('databricks:staging:my-scope:MY_KEY')

        provider.get_secret_value(props)
        assert calls == [(DatabricksContext(profile='staging'), 'my-scope', 'MY_KEY')]

    def test_missing_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        provider = DatabricksSecretProvider()
        props = parse_sri('databricks::my-scope:')

        with pytest.raises(SecretRetrievalError, match='non-empty key'):
            provider.get_secret_value(props)

    def test_sdk_error_is_wrapped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_get_secret(context: DatabricksContext, scope: str, key: str) -> str:
            raise RuntimeError('secret-value-should-not-leak')

        monkeypatch.setattr(databricks_module, '_get_secret', fake_get_secret)
        provider = DatabricksSecretProvider()
        props = parse_sri('databricks::my-scope:MY_KEY')

        with pytest.raises(SecretRetrievalError) as excinfo:
            provider.get_secret_value(props)
        assert 'secret-value-should-not-leak' not in str(excinfo.value)
        assert 'my-scope' in str(excinfo.value)

    def test_default_context_falls_back_to_sdk_when_runtime_is_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_databricks = types.ModuleType('databricks')
        fake_databricks.__path__ = []

        fake_sdk = types.ModuleType('databricks.sdk')
        fake_sdk.__path__ = []

        calls: list[str | None] = []

        class FakeWorkspaceClient:
            def __init__(self, profile: str | None = None) -> None:
                calls.append(profile)
                self.dbutils = types.SimpleNamespace(
                    secrets=types.SimpleNamespace(get=lambda scope, key: 'resolved-value')
                )

        cast(Any, fake_sdk).WorkspaceClient = FakeWorkspaceClient
        cast(Any, fake_databricks).sdk = fake_sdk

        monkeypatch.setitem(sys.modules, 'databricks', fake_databricks)
        monkeypatch.setitem(sys.modules, 'databricks.sdk', fake_sdk)
        monkeypatch.delitem(sys.modules, 'databricks.sdk.runtime', raising=False)

        provider = DatabricksSecretProvider()
        props = parse_sri('databricks::my-scope:MY_KEY')

        assert provider.get_secret_value(props) == 'resolved-value'
        assert calls == [None]
