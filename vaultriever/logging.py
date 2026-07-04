"""Logger helper.

All modules obtain their logger through :func:`get_logger` so the package
shares a single ``vaultriever`` namespace and users can configure it once.
"""

from __future__ import annotations

import logging


def get_logger(name: str) -> logging.Logger:
    """Return a logger under the ``vaultriever`` namespace."""
    if name == 'vaultriever' or name.startswith('vaultriever.'):
        return logging.getLogger(name)
    return logging.getLogger(f'vaultriever.{name}')
