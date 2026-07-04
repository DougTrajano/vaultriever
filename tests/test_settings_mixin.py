import os
from collections.abc import Iterator
from typing import Any, ClassVar

import pytest
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings

from vaultriever import SecretProviderRegistry, SecretSRIMixin
from vaultriever.sri import SecretProperties


class FakeProvider:
    name = 'fakevault'

    def get_secret_value(self, props: SecretProperties) -> Any:
        return f'resolved:{props.secret_name}/{props.secret_key}'


@pytest.fixture(autouse=True)
def fake_provider() -> Iterator[FakeProvider]:
    provider = FakeProvider()
    SecretProviderRegistry.register(provider)
    yield provider
    SecretProviderRegistry.unregister(provider.name)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ('api_key', 'plain_value', 'number', 'db_url'):
        monkeypatch.delenv(name, raising=False)


class TestSRIResolution:
    def test_str_sri_resolves_to_secret_str(self) -> None:
        class Settings(SecretSRIMixin, BaseSettings):
            api_key: str | SecretStr = 'fakevault:us-east-1:my-secret:API_KEY'

        settings = Settings()
        assert isinstance(settings.api_key, SecretStr)
        assert settings.api_key.get_secret_value() == 'resolved:my-secret/API_KEY'

    def test_secret_str_sri_resolves(self) -> None:
        class Settings(SecretSRIMixin, BaseSettings):
            api_key: SecretStr

        settings = Settings(api_key=SecretStr('fakevault::my-secret:API_KEY'))
        assert settings.api_key.get_secret_value() == 'resolved:my-secret/API_KEY'

    def test_resolved_secret_is_masked_in_repr(self) -> None:
        class Settings(SecretSRIMixin, BaseSettings):
            api_key: str | SecretStr = 'fakevault::my-secret:API_KEY'

        assert 'resolved:my-secret/API_KEY' not in repr(Settings())

    def test_non_sri_str_unchanged(self) -> None:
        class Settings(SecretSRIMixin, BaseSettings):
            plain_value: str = 'just-a-plain-string'

        assert Settings().plain_value == 'just-a-plain-string'

    def test_colon_heavy_url_unchanged(self) -> None:
        class Settings(SecretSRIMixin, BaseSettings):
            db_url: str = 'postgresql://user:pass@host:5432/db'

        assert Settings().db_url == 'postgresql://user:pass@host:5432/db'

    def test_unregistered_provider_sri_unchanged(self) -> None:
        class Settings(SecretSRIMixin, BaseSettings):
            plain_value: str = 'unknownvault:region:name:key'

        assert Settings().plain_value == 'unknownvault:region:name:key'

    def test_non_string_values_unchanged(self) -> None:
        class Settings(SecretSRIMixin, BaseSettings):
            number: int = 7

        assert Settings().number == 7

    def test_explicit_value_overrides_default(self) -> None:
        class Settings(SecretSRIMixin, BaseSettings):
            api_key: str | SecretStr = Field(default='fakevault::my-secret:API_KEY')

        settings = Settings(api_key='literal-key')
        assert settings.api_key == 'literal-key'


class TestEnvExport:
    def test_resolved_secret_exported(self) -> None:
        class Settings(SecretSRIMixin, BaseSettings):
            api_key: str | SecretStr = 'fakevault::my-secret:API_KEY'

        Settings()
        assert os.environ['api_key'] == 'resolved:my-secret/API_KEY'

    def test_plain_value_exported(self) -> None:
        class Settings(SecretSRIMixin, BaseSettings):
            plain_value: str = 'hello'

        Settings()
        assert os.environ['plain_value'] == 'hello'

    def test_export_disabled(self) -> None:
        class Settings(SecretSRIMixin, BaseSettings):
            enable_env_export: ClassVar[bool] = False

            api_key: str | SecretStr = 'fakevault::my-secret:API_KEY'

        settings = Settings()
        assert isinstance(settings.api_key, SecretStr)
        assert 'api_key' not in os.environ
