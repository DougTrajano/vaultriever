import json
from collections.abc import Iterator

import boto3
import pytest
from moto import mock_aws

from vaultriever.exceptions import SecretRetrievalError
from vaultriever.providers.aws import AWSSecretProvider, _get_aws_secret_string
from vaultriever.sri import parse_sri

REGION = 'us-east-1'


@pytest.fixture
def provider() -> AWSSecretProvider:
    return AWSSecretProvider()


@pytest.fixture
def secretsmanager(monkeypatch: pytest.MonkeyPatch) -> Iterator[object]:
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    with mock_aws():
        client = boto3.client('secretsmanager', region_name=REGION)
        client.create_secret(
            Name='my-secret',
            SecretString=json.dumps({'OPENAI_API_KEY': 'sk-test-123', 'OTHER': 'value'}),
        )
        client.create_secret(Name='not-json', SecretString='just a plain string')
        client.create_secret(Name='not-object', SecretString=json.dumps(['a', 'b']))
        yield client


class TestAWSSecretProvider:
    def test_get_secret_value(self, provider: AWSSecretProvider, secretsmanager: object) -> None:
        props = parse_sri(f'aws:{REGION}:my-secret:OPENAI_API_KEY')
        assert provider.get_secret_value(props) == 'sk-test-123'

    def test_missing_key_raises(self, provider: AWSSecretProvider, secretsmanager: object) -> None:
        props = parse_sri(f'aws:{REGION}:my-secret:NO_SUCH_KEY')
        with pytest.raises(SecretRetrievalError, match="'NO_SUCH_KEY' not found"):
            provider.get_secret_value(props)

    def test_missing_secret_raises(
        self, provider: AWSSecretProvider, secretsmanager: object
    ) -> None:
        props = parse_sri(f'aws:{REGION}:no-such-secret:KEY')
        with pytest.raises(SecretRetrievalError, match='no-such-secret'):
            provider.get_secret_value(props)

    def test_plaintext_secret_with_omitted_key_returns_raw_string(
        self, provider: AWSSecretProvider, secretsmanager: object
    ) -> None:
        props = parse_sri(f'aws:{REGION}:not-json:')
        assert provider.get_secret_value(props) == 'just a plain string'

    def test_non_object_json_secret_with_omitted_key_returns_raw_string(
        self, provider: AWSSecretProvider, secretsmanager: object
    ) -> None:
        props = parse_sri(f'aws:{REGION}:not-object:')
        assert provider.get_secret_value(props) == json.dumps(['a', 'b'])

    def test_plaintext_secret_with_key_raises(
        self, provider: AWSSecretProvider, secretsmanager: object
    ) -> None:
        props = parse_sri(f'aws:{REGION}:not-json:KEY')
        with pytest.raises(SecretRetrievalError, match='not JSON-based'):
            provider.get_secret_value(props)

    def test_json_object_secret_with_omitted_key_raises(
        self, provider: AWSSecretProvider, secretsmanager: object
    ) -> None:
        props = parse_sri(f'aws:{REGION}:my-secret:')
        with pytest.raises(SecretRetrievalError, match='secret_key is required'):
            provider.get_secret_value(props)

    def test_missing_region_raises(self, provider: AWSSecretProvider) -> None:
        props = parse_sri('aws::my-secret:KEY')
        with pytest.raises(SecretRetrievalError, match='non-empty region'):
            provider.get_secret_value(props)

    def test_error_message_does_not_leak_value(
        self, provider: AWSSecretProvider, secretsmanager: object
    ) -> None:
        props = parse_sri(f'aws:{REGION}:my-secret:NO_SUCH_KEY')
        with pytest.raises(SecretRetrievalError) as excinfo:
            provider.get_secret_value(props)
        assert 'sk-test-123' not in str(excinfo.value)

    def test_caching(self, provider: AWSSecretProvider, secretsmanager: object) -> None:
        props = parse_sri(f'aws:{REGION}:my-secret:OPENAI_API_KEY')
        provider.get_secret_value(props)
        info = _get_aws_secret_string.cache_info()
        assert info.misses == 1

        provider.get_secret_value(props)
        info = _get_aws_secret_string.cache_info()
        assert info.hits == 1
        assert info.misses == 1

    def test_clear_cache(self, provider: AWSSecretProvider, secretsmanager: object) -> None:
        props = parse_sri(f'aws:{REGION}:my-secret:OPENAI_API_KEY')
        provider.get_secret_value(props)
        AWSSecretProvider.clear_cache()
        provider.get_secret_value(props)
        assert _get_aws_secret_string.cache_info().misses == 1
