"""Registry components for task management and versioning"""

from parasel.registry.task_registry import TaskRegistry, TaskSpec
from parasel.registry.schemas import requires_keys, produces_keys, validate_schema

__all__ = [
    "TaskRegistry",
    "TaskSpec",
    "requires_keys",
    "produces_keys",
    "validate_schema",
]

