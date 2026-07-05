# Security

Vaultriever handles secret material, so it is built to keep values out of logs and error messages
by default. This page describes those guarantees and the one behavior you should consciously decide
on: environment export.

## Secrets are masked by default

When [`SecretSRIMixin`](pydantic-settings.md) resolves an SRI, the value is wrapped in pydantic's
`SecretStr`. That keeps it out of `repr()`, logs, and tracebacks:

```python
settings = OpenAISettings()
print(settings)                # openai_api_key=SecretStr('**********')
str(settings.openai_api_key)   # '**********'
```

The plaintext value is only exposed when you explicitly ask for it:

```python
settings.openai_api_key.get_secret_value()  # 'sk-...'
```

Call `.get_secret_value()` as late as possible — ideally at the exact point you pass the secret to
a client — and never log its result.

!!! note "The standalone resolver returns plaintext"
    [`resolve_secret`](api/resolver.md) returns a plain `str`, not a `SecretStr`. If you use it
    directly (outside a settings model), wrap the result yourself: `SecretStr(resolve_secret(sri))`.

## Errors never contain secret values

All Vaultriever exceptions are designed so that **error messages never include the resolved secret
value**. Messages may reference non-sensitive SRI components — the `provider`, `region`, or
`secret_name` — to aid debugging, but not the secret itself. `SRIParseError` additionally avoids
echoing the full input, so a string that merely *looks* like a secret is not leaked through a
parse error.

If you [write a custom provider](custom-providers.md), uphold the same rule: raise
`SecretRetrievalError` with only non-sensitive context.

## Environment export writes plaintext

By default, `SecretSRIMixin` writes every validated field back to `os.environ` under its field
name, so downstream libraries that read environment variables see resolved values. **This places
plaintext secrets in the process environment**, where they are visible to:

- child processes spawned by your application;
- crash reporters and diagnostics that dump the environment;
- anything that can read `/proc/<pid>/environ` for the process.

Decide per model whether that trade-off is acceptable. To opt out, disable it with a `ClassVar`:

```python
from typing import ClassVar
from pydantic import SecretStr
from vaultriever import SecretSRIMixin


class MySettings(SecretSRIMixin):
    enable_env_export: ClassVar[bool] = False

    api_key: str | SecretStr = 'aws:us-east-1:my-secret:API_KEY'
```

With export disabled, resolved values live only on the model instance (as `SecretStr`), and nothing
is written to the environment.

## Caching

The AWS provider caches decoded secret payloads per `(secret_name, region)` for the lifetime of the
process to avoid redundant API calls. The cached data is the JSON object retrieved from Secrets
Manager. After rotating a secret, clear the cache so the next lookup fetches fresh material:

```python
from vaultriever.providers import AWSSecretProvider

AWSSecretProvider.clear_cache()
```

## Checklist

- [ ] Call `.get_secret_value()` only at the point of use; never log it.
- [ ] Decide whether [environment export](#environment-export-writes-plaintext) is acceptable for
  each model, and disable it where it isn't.
- [ ] Scope your vault credentials (IAM role / Databricks profile) to only the secrets the
  application needs.
- [ ] Clear the AWS cache after rotating secrets in a long-lived process.
- [ ] In custom providers, never put secret values in exceptions or logs.
