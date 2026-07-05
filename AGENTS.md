# vaultriever Agent Instructions

## What this repository is

vaultriever resolves secret resource identifiers (SRIs) like `provider:region:secret_name:secret_key` into secret values, with the main user-facing API re-exported from [vaultriever/__init__.py](vaultriever/__init__.py). The core modules are [vaultriever/sri.py](vaultriever/sri.py), [vaultriever/resolver.py](vaultriever/resolver.py), [vaultriever/settings_mixin.py](vaultriever/settings_mixin.py), and [vaultriever/providers](vaultriever/providers).

## How to work here

- Keep changes focused and add or update tests alongside behavior changes.
- Prefer the smallest change that preserves the existing API and provider behavior.
- Do not duplicate documentation that already exists; link to the relevant page instead.
- Treat secret material carefully: avoid logging resolved values and preserve the repo’s masking behavior.

## Project conventions

- `SecretSRIMixin` resolves SRI-like string defaults and validated values; it also exports validated values to `os.environ` unless disabled on the model.
- The registry is global for the process, so register custom providers before instantiating settings models.
- Providers should import optional SDKs lazily and raise `SecretRetrievalError` with non-sensitive context only.
- AWS secrets are cached per `(secret_name, region)`; clear the cache in tests or after rotation when needed.
- Databricks behavior depends on runtime context and CLI profiles; tests should patch the internal helper rather than reaching into SDK internals directly.

## Useful docs

- [README.md](README.md) for the high-level API and examples.
- [docs/quick-start.md](docs/quick-start.md) for getting started.
- [docs/pydantic-settings.md](docs/pydantic-settings.md) for settings integration details.
- [docs/custom-providers.md](docs/custom-providers.md) for provider extension guidance.
- [docs/security.md](docs/security.md) for masking, environment export, and error-handling expectations.

## Commands

Use the documented workflow from the README:

- `uv sync --all-extras --dev`
- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy`

When touching a narrow area, prefer the smallest relevant test target first, then widen only if needed.