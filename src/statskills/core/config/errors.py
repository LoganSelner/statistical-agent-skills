"""Config error type.

Leaf module with no internal imports, so :mod:`loading` (cycle detection) and,
later, a validation module can both raise it without creating an import cycle.
"""

from __future__ import annotations


class ConfigValidationError(Exception):
    """Raised when config loading or validation fails."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        bullet_list = "\n".join(f"  - {e}" for e in errors)
        super().__init__(
            f"Config validation failed with {len(errors)} error(s):\n{bullet_list}"
        )
