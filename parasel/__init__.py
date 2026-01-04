"""Parasel: AI 파이프라인을 직렬/병렬의 중첩 리스트로 통제하기 위한 프레임워크"""

from parasel.core.node import Node, Serial, Parallel, ByArgs, ByKeys
from parasel.core.context import Context
from parasel.core.module_adapter import ModuleAdapter
from parasel.core.executor import Executor, ExecutionPolicy
from parasel.registry.task_registry import TaskRegistry, TaskSpec
from parasel.api.fastapi_app import create_app, Run, RunAsync

__version__ = "0.1.0"

__all__ = [
    "Node",
    "Serial",
    "Parallel",
    "ByArgs",
    "ByKeys",
    "Context",
    "ModuleAdapter",
    "Executor",
    "ExecutionPolicy",
    "TaskRegistry",
    "TaskSpec",
    "create_app",
    "Run",
    "RunAsync",
]

