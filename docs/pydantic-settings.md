# Pydantic Settings Integration

[`SecretSRIMixin`](api/settings.md#vaultriever.settings_mixin.SecretSRIMixin) is the idiomatic way
to use Vaultriever. Mix it into a `pydantic-settings` model and any field whose value is a valid,
registered SRI is resolved automatically — no custom field types, no per-field wiring.

## Basic usage

```python
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings
from vaultriever import SecretSRIMixin


class OpenAISettings(SecretSRIMixin, BaseSettings):
    openai_api_key: str | SecretStr = Field(
        default='aws:us-east-1:my-secret:OPENAI_API_KEY',
        description='OpenAI API key; SRI or literal.',
    )


settings = OpenAISettings()
settings.openai_api_key                     # SecretStr('**********') — masked
settings.openai_api_key.get_secret_value()  # the resolved secret
```

Because the mixin already extends `BaseSettings`, both declarations are equivalent:

```python
class MySettings(SecretSRIMixin):
    api_key: str | SecretStr = 'aws:us-east-1:my-secret:API_KEY'

class MySettings(SecretSRIMixin, BaseSettings):
    api_key: str | SecretStr = 'aws:us-east-1:my-secret:API_KEY'
```

Adding `BaseSettings` explicitly keeps type checkers happy about `model_config`; pick whichever
your team prefers.

## How resolution works

The mixin installs a wildcard `mode='before'` validator that runs on **every** field. For each
value it:

1. Unwraps `SecretStr` / accepts `str`; any other type passes through untouched.
2. Checks the string is [structurally an SRI](sri.md#validation-rules) **and** that its provider is
   registered.
3. If both hold, resolves the secret and returns it wrapped in `SecretStr`.
4. Otherwise returns the original value unchanged.

```python
class Settings(SecretSRIMixin):
    api_key: str | SecretStr = 'aws:us-east-1:my-secret:API_KEY'  # resolved -> SecretStr
    db_url: str = 'postgresql://user:pass@host:5432/db'           # literal -> unchanged
    retries: int = 3                                              # non-string -> unchanged
```

!!! info "Why the provider must be registered"
    Requiring a registered provider (not just a valid shape) means colon-heavy strings that happen
    to look like an SRI for an unknown scheme are treated as plain literals rather than raising.
    Register [custom providers](custom-providers.md) before instantiating the model.

### Defaults are resolved too

The mixin sets `model_config = SettingsConfigDict(validate_default=True)`, so SRI strings used as
**field defaults** are resolved — not just values supplied from the environment.

## Masking

Resolved secrets are wrapped in `SecretStr`, so they stay masked in `repr()`, logs, and tracebacks.
Call `.get_secret_value()` only at the point of use:

```python
settings = OpenAISettings()
print(settings)                             # openai_api_key=SecretStr('**********')
client = OpenAI(api_key=settings.openai_api_key.get_secret_value())
```

## Environment export

By default, every validated field is also written back to `os.environ` under the **field name**, so
downstream libraries that read environment variables pick up resolved values automatically:

```python
class Settings(SecretSRIMixin):
    openai_api_key: str | SecretStr = 'aws:us-east-1:my-secret:OPENAI_API_KEY'


Settings()
import os
os.environ['openai_api_key']  # the resolved secret, in plaintext
```

Dict/list values are JSON-encoded; everything else is stringified.

!!! danger "This writes plaintext secrets to the environment"
    Environment export puts **resolved secrets in plaintext** into the process environment, where
    child processes and crash reporters can read them. Opt out per model with a `ClassVar`:

    ```python
    from typing import ClassVar
    from pydantic import SecretStr
    from vaultriever import SecretSRIMixin


    class MySettings(SecretSRIMixin):
        enable_env_export: ClassVar[bool] = False

        api_key: str | SecretStr = 'aws:us-east-1:my-secret:API_KEY'
    ```

    The `ClassVar` annotation is required — it tells pydantic this is configuration, not a field.

See [Security](security.md) for the full picture.

## API reference

See the [settings API reference](api/settings.md) for the complete `SecretSRIMixin` signature.
