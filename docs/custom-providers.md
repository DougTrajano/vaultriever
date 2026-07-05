# Custom Providers

Vaultriever's provider system is open: you can teach it to read from any vault by implementing a
small interface and registering it. Once registered, SRIs using your provider's name resolve
through it — including inside [`SecretSRIMixin`](pydantic-settings.md).

## The provider interface

A provider is any object that satisfies the
[`SecretProvider`](api/providers.md#vaultriever.providers.base.SecretProvider) protocol:

- a `name` attribute — the lowercase scheme used as the SRI's `provider` segment;
- a `get_secret_value(props)` method that takes a
  [`SecretProperties`](api/sri.md#vaultriever.sri.SecretProperties) and returns the secret.

```python
from vaultriever.sri import SecretProperties


class MyVaultProvider:
    name = 'myvault'

    def get_secret_value(self, props: SecretProperties) -> str:
        # props.region, props.secret_name, props.secret_key are available here.
        # Fetch and return the secret value as a string.
        ...
```

`SecretProvider` is a `runtime_checkable` `Protocol`, so you do **not** need to subclass anything —
any object with the right shape works.

## Registering a provider

Register an **instance** with the
[`SecretProviderRegistry`](api/providers.md#vaultriever.providers.base.SecretProviderRegistry):

```python
from vaultriever import SecretProviderRegistry

SecretProviderRegistry.register(MyVaultProvider())

# Now 'myvault:region:name:key' SRIs resolve through it.
```

Registration is global for the process and replaces any existing provider with the same `name`.
Register your providers **before** instantiating any `SecretSRIMixin` model, since the mixin only
treats a value as an SRI when its provider is already registered.

```python
from vaultriever import SecretProviderRegistry

SecretProviderRegistry.register(MyVaultProvider())
SecretProviderRegistry.unregister('myvault')      # remove it (no-op if absent)
SecretProviderRegistry.is_registered('myvault')   # False
SecretProviderRegistry.available_providers()      # ['aws', 'databricks']
```

## A complete example

```python
from vaultriever import SecretProviderRegistry, resolve_secret
from vaultriever.sri import SecretProperties


class EnvFileProvider:
    """Toy provider that reads from an in-memory mapping."""

    name = 'envfile'

    def __init__(self, store: dict[str, dict[str, str]]) -> None:
        self._store = store

    def get_secret_value(self, props: SecretProperties) -> str:
        return self._store[props.secret_name][props.secret_key]


SecretProviderRegistry.register(
    EnvFileProvider({'app': {'API_KEY': 'sk-local-123'}})
)

resolve_secret('envfile::app:API_KEY')  # 'sk-local-123'
```

## Guidelines

- **Return a plain string.** [`resolve_secret`](api/resolver.md) stringifies the result before
  wrapping it in `SecretStr`, so returning a `str` keeps behavior predictable.
- **Never leak secret values in errors.** Raise
  [`SecretRetrievalError`](api/exceptions.md#vaultriever.exceptions.SecretRetrievalError) (or a
  subclass) on failure, and include only non-sensitive context such as the `secret_name` or
  `region` — never the resolved value. This mirrors the built-in providers.
- **Import SDKs lazily.** Import heavy or optional dependencies inside `get_secret_value`, not at
  module top level, so registering the provider stays cheap and import-safe.
- **Interpret `region` however fits your vault.** It may be a region, a profile, a namespace, or
  empty — it is provider-defined. `props.region` is `None` when the SRI's region segment is empty.

## API reference

See the [providers API reference](api/providers.md) for the full protocol and registry signatures.
