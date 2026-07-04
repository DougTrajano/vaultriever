import pytest

from vaultriever.exceptions import SRIParseError
from vaultriever.sri import SecretProperties, is_sri, parse_sri


class TestIsSRI:
    @pytest.mark.parametrize(
        'value',
        [
            'aws:us-east-1:my-secret:OPENAI_API_KEY',
            'databricks::my-secret-scope:OPENAI_API_KEY',
            'azure:my-vault:my-secret:latest',
            'my_vault-2:region:name:key',
        ],
    )
    def test_valid(self, value: str) -> None:
        assert is_sri(value)

    @pytest.mark.parametrize(
        'value',
        [
            '',
            'plain-string',
            'a:b:c',  # 3 parts
            'a:b:c:d:e',  # 5 parts
            'AWS:us-east-1:my-secret:KEY',  # uppercase provider
            ':us-east-1:my-secret:KEY',  # empty provider
            'aws:us-east-1::KEY',  # empty secret_name
            'aws:us-east-1:my-secret:',  # empty secret_key
            'postgresql://user:pass@host:5432/db',  # URL-ish, invalid provider chars
        ],
    )
    def test_invalid(self, value: str) -> None:
        assert not is_sri(value)

    def test_non_string(self) -> None:
        assert not is_sri(123)  # type: ignore[arg-type]


class TestParseSRI:
    def test_aws(self) -> None:
        props = parse_sri('aws:us-east-1:my-secret:OPENAI_API_KEY')
        assert props == SecretProperties(
            provider='aws',
            region='us-east-1',
            secret_name='my-secret',
            secret_key='OPENAI_API_KEY',
        )

    def test_empty_region_becomes_none(self) -> None:
        props = parse_sri('databricks::my-secret-scope:OPENAI_API_KEY')
        assert props.provider == 'databricks'
        assert props.region is None
        assert props.secret_name == 'my-secret-scope'
        assert props.secret_key == 'OPENAI_API_KEY'

    @pytest.mark.parametrize(
        'value',
        ['not-an-sri', 'a:b:c', 'a:b:c:d:e', 'AWS:r:n:k', 'aws:r::k', 'aws:r:n:'],
    )
    def test_malformed_raises(self, value: str) -> None:
        expected = "Expected 'provider:region:secret_name:secret_key'"
        with pytest.raises(SRIParseError, match=expected):
            parse_sri(value)

    def test_malformed_is_value_error(self) -> None:
        with pytest.raises(ValueError):
            parse_sri('nope')
