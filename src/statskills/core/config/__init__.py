"""Config system: YAML loading with ``extends:`` inheritance.

Exposes the project-agnostic loader and error type. The domain config models
(Pydantic trees) and their validation arrive with the experiment layer; keeping
this package thin preserves the harness/experiment seam (ROADMAP §2).
"""

from __future__ import annotations

from statskills.core.config.errors import ConfigValidationError
from statskills.core.config.loading import load_yaml_with_inheritance

__all__ = [
    "ConfigValidationError",
    "load_yaml_with_inheritance",
]
