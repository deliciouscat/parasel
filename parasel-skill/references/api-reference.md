# API Reference

## Core Classes

### Context

Thread-safe dictionary wrapper for sharing data across pipeline.

```python
from parasel.core.context import Context

context = Context(initial_data: dict = None, thread_safe: bool = False)
```

**Methods:**
- `get(key: str, default: Any = None) -> Any` - Safe read
- `set(key: str, value: Any) -> None` - Write value
- `__getitem__(key: str) -> Any` - Dict-style read: `context["key"]`
- `__setitem__(key: str, value: Any) -> None` - Dict-style write: `context["key"] = value`
- `__contains__(key: str) -> bool` - Check existence: `"key" in context`
- `accumulate(key: str, value: Any) -> None` - Thread-safe list append
- `keys()` - All keys
- `values()` - All values
- `items()` - All key-value pairs
- `update(other: dict) -> None` - Bulk update
- `to_dict() -> dict` - Export as dict

---

### Node (Abstract Base Class)

Base class for all pipeline components.

```python
from parasel.core.node import Node

class Node(ABC):
    def __init__(
        self,
        name: str = None,
        timeout: float = None,
        retries: int = 0,
        metadata: dict = None
    )
    
    @abstractmethod
    def run(self, context: Context) -> None:
        """Synchronous execution"""
        pass
    
    async def run_async(self, context: Context) -> None:
        """Asynchronous execution"""
        pass
```

**Attributes:**
- `name: str` - Node identifier
- `timeout: float` - Execution timeout (seconds)
- `retries: int` - Retry count on failure
- `metadata: dict` - Additional metadata

---

### Serial

Sequential execution of child nodes.

```python
from parasel import Serial

Serial(
    children: List[Node],
    name: str = None,
    continue_on_error: bool = False,
    timeout: float = None,
    retries: int = 0
)
```

**Parameters:**
- `children` - List of nodes to execute sequentially
- `continue_on_error` - If True, continue despite errors

**Methods:**
- `run(context: Context)` - Execute children sequentially
- `expose(expose_keys: List[str]) -> Serial` - Filter API response keys

**Example:**
```python
pipeline = Serial([
    node1,
    node2,
    node3
], name="MyPipeline")
```

---

### Parallel

Concurrent execution of child nodes.

```python
from parasel import Parallel

Parallel(
    children: List[Node],
    name: str = None,
    max_workers: int = None,
    fail_fast: bool = True,
    timeout: float = None,
    retries: int = 0
)
```

**Parameters:**
- `children` - List of nodes to execute concurrently
- `max_workers` - Max thread pool size (default: len(children))
- `fail_fast` - Stop on first error (default: True)

**Methods:**
- `run(context: Context)` - Execute children in parallel
- `expose(expose_keys: List[str]) -> Parallel` - Filter API response keys

**Example:**
```python
pipeline = Parallel([
    task_a,
    task_b,
    task_c
], max_workers=3)
```

---

### ModuleAdapter

Wraps user functions into Node interface.

```python
from parasel import ModuleAdapter

ModuleAdapter(
    func: Callable,
    out_name: str = None,
    name: str = None,
    timeout: float = None,
    retries: int = 0,
    **kwargs
)
```

**Parameters:**
- `func` - Function to wrap (sync or async)
- `out_name` - Context key to write result to
- `name` - Node name (default: function name)
- `**kwargs` - Additional arguments passed to function

**Supported Function Signatures:**
```python
# Standard signature
def func(context: Context, out_name: str, **kwargs) -> None:
    pass

# Async
async def func(context: Context, out_name: str, **kwargs) -> None:
    pass

# With return value (written to out_name)
def func(context: Context, out_name: str, **kwargs) -> Any:
    return result
```

**Example:**
```python
def extract(context: Context, out_name: str, **kwargs):
    data = context.get("input")
    result = process(data)
    context[out_name] = result

node = ModuleAdapter(
    func=extract,
    out_name="extracted",
    name="Extractor",
    custom_arg="value"
)
```

---

### ByArgs

Generate multiple node instances with different argument values.

```python
from parasel import ByArgs

ByArgs(
    base_node: ModuleAdapter,
    args: Dict[str, List[Any]]
)
```

**Parameters:**
- `base_node` - ModuleAdapter to replicate
- `args` - Dict of param_name -> list_of_values

**Usage:**
```python
node = ModuleAdapter(translate, out_name="translations")

# Execute with language="en", "ko", "ja"
Parallel([
    ByArgs(node, args={"language": ["en", "ko", "ja"]})
])
```

**Cartesian Product:**
```python
# Creates 6 executions: (en,text), (en,html), (ko,text), (ko,html), (ja,text), (ja,html)
ByArgs(node, args={
    "language": ["en", "ko", "ja"],
    "format": ["text", "html"]
})
```

---

### ByKeys

Execute node for each item in Context list.

```python
from parasel import ByKeys

ByKeys(
    base_node: ModuleAdapter,
    keys: List[str],
    input_key_name: str = "input",
    name: str = None
)
```

**Parameters:**
- `base_node` - ModuleAdapter to replicate
- `keys` - Context keys to read (must be lists)
- `input_key_name` - Function parameter to pass each item to

**Usage:**
```python
# context["queries"] = ["q1", "q2", "q3"]
search_node = ModuleAdapter(search, out_name="results")

Parallel([
    ByKeys(search_node, keys=["queries"], input_key_name="query")
])
# Executes: search(query="q1"), search(query="q2"), search(query="q3")
```

---

### TaskRegistry

Manage versioned tasks.

```python
from parasel.registry import TaskRegistry

registry = TaskRegistry()
```

**Methods:**

#### register()
```python
registry.register(
    task_id: str,
    version: str,
    node: Node,
    description: str = None,
    requires: List[str] = None,
    produces: List[str] = None,
    schema_in: Type[BaseModel] = None,
    schema_out: Type[BaseModel] = None,
    tags: List[str] = None,
    metadata: dict = None,
    overwrite: bool = False,
    mark_stable: bool = False
) -> TaskSpec
```

**Parameters:**
- `task_id` - Unique task identifier
- `version` - Semantic version (e.g., "1.0.0")
- `node` - Pipeline to execute
- `requires` - List of required input keys
- `produces` - List of output keys
- `mark_stable` - Mark this version as stable

#### get()
```python
registry.get(
    task_id: str,
    version: str = "latest"
) -> TaskSpec
```

**Parameters:**
- `task_id` - Task identifier
- `version` - "latest", "stable", or specific version

#### list_tasks()
```python
registry.list_tasks() -> List[str]
```

Returns list of all task IDs.

#### list_versions()
```python
registry.list_versions(task_id: str) -> List[str]
```

Returns sorted list of versions for a task.

#### mark_stable()
```python
registry.mark_stable(task_id: str, version: str) -> None
```

Mark a version as stable.

#### unregister()
```python
registry.unregister(
    task_id: str,
    version: str = None
) -> None
```

Remove task (all versions if version=None).

---

### Run Function

Simplified pipeline execution.

```python
from parasel import Run

Run(
    user_input: dict,
    task: str,
    version: str = "latest",
    registry: TaskRegistry = None
) -> dict
```

**Parameters:**
- `user_input` - Input data dictionary
- `task` - Task ID to execute
- `version` - "latest", "stable", or specific version
- `registry` - TaskRegistry instance

**Returns:**
```python
{
    "success": bool,
    "data": dict,  # Context data
    "task_id": str,
    "version": str,
    "duration": float,
    "errors": List[Exception]  # If any
}
```

**Example:**
```python
result = Run(
    user_input={"query": "search term"},
    task="search",
    version="stable",
    registry=registry
)

if result["success"]:
    print(result["data"]["results"])
```

---

### Executor

Advanced execution engine with policies.

```python
from parasel.core.executor import Executor, ExecutionPolicy

policy = ExecutionPolicy(
    timeout: float = None,
    retry_on: List[Type[Exception]] = [Exception],
    retry_backoff: float = 1.0,
    parallel_max_workers: int = None,
    error_mode: ErrorMode = ErrorMode.FAIL_FAST,
    before_node: Callable = None,
    after_node: Callable = None,
    on_error: Callable = None
)

executor = Executor(policy=policy)
```

**Methods:**

#### run()
```python
executor.run(
    node: Node,
    context: Context = None,
    initial_data: dict = None
) -> ExecutionResult
```

Synchronous execution.

#### run_async()
```python
await executor.run_async(
    node: Node,
    context: Context = None,
    initial_data: dict = None
) -> ExecutionResult
```

Asynchronous execution.

**ExecutionResult:**
```python
class ExecutionResult:
    context: Context
    success: bool
    duration: float
    errors: List[ExecutionError]
    node_timings: Dict[str, float]
```

---

## FastAPI Integration

### create_app()

```python
from parasel.api.fastapi_app import create_app

create_app(
    registry: TaskRegistry,
    title: str = "Parasel API",
    description: str = "",
    version: str = "1.0.0"
) -> FastAPI
```

**Parameters:**
- `registry` - TaskRegistry with registered tasks
- `title` - API title
- `description` - API description
- `version` - API version

**Returns:** FastAPI application instance

**Example:**
```python
app = create_app(
    registry=registry,
    title="My AI Pipeline API",
    description="Production AI workflows",
    version="1.0.0"
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## FastAPI Endpoints

### GET /

API information and health status.

**Response:**
```json
{
  "name": "Parasel API",
  "version": "1.0.0",
  "status": "healthy"
}
```

---

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

---

### GET /tasks

List all registered tasks.

**Response:**
```json
{
  "tasks": [
    {
      "task_id": "search",
      "versions": ["1.0.0", "1.1.0", "2.0.0"],
      "stable_version": "2.0.0",
      "latest_version": "2.0.0"
    }
  ]
}
```

---

### GET /tasks/{task_id}

Get task details (all versions).

**Parameters:**
- `task_id` (path) - Task identifier

**Response:**
```json
{
  "task_id": "search",
  "versions": {
    "1.0.0": {
      "version": "1.0.0",
      "description": "Search pipeline v1",
      "requires": ["query"],
      "produces": ["results"],
      "tags": ["search", "web"]
    },
    "2.0.0": {
      "version": "2.0.0",
      "description": "Search pipeline v2",
      "requires": ["query"],
      "produces": ["results", "metadata"],
      "tags": ["search", "web", "cached"]
    }
  },
  "stable_version": "2.0.0",
  "latest_version": "2.0.0"
}
```

---

### POST /run/{task_id}

Execute a task.

**Parameters:**
- `task_id` (path) - Task identifier

**Request Body:**
```json
{
  "data": {
    "query": "search term",
    "max_results": 10
  },
  "version": "stable"
}
```

**Fields:**
- `data` (required) - Input data dictionary
- `version` (optional) - "latest", "stable", or specific version (default: "latest")

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "results": [...]
  },
  "task_id": "search",
  "version": "2.0.0",
  "duration": 1.234
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "Error message",
  "task_id": "search",
  "version": "2.0.0",
  "duration": 0.5
}
```

---

## Exceptions

### ExecutionError

Raised when node execution fails.

```python
from parasel.core.node import ExecutionError

class ExecutionError(Exception):
    def __init__(
        self,
        message: str,
        node_name: str,
        cause: Exception = None
    )
    
    node_name: str      # Name of failed node
    cause: Exception    # Original exception
```

---

### TaskNotFoundError

Raised when task or version not found in registry.

```python
from parasel.registry import TaskNotFoundError

class TaskNotFoundError(Exception):
    pass
```

---

### VersionConflictError

Raised when registering duplicate version without overwrite.

```python
from parasel.registry import VersionConflictError

class VersionConflictError(Exception):
    pass
```

---

## Type Hints

```python
from typing import Callable, Dict, List, Any, Optional
from parasel.core.context import Context
from parasel.core.node import Node
from pydantic import BaseModel

# Function signature
ModuleFunction = Callable[[Context, str, ...], None]

# Registry types
TaskID = str
Version = str
InputData = Dict[str, Any]
OutputData = Dict[str, Any]
```

---

## Constants

```python
from parasel.core.executor import ErrorMode

ErrorMode.FAIL_FAST   # Stop on first error
ErrorMode.COLLECT     # Collect all errors
```
