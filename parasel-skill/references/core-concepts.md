# Core Concepts

## Architecture Overview

```
Input Data
    ↓
Context (shared store)
    ↓
Pipeline (Node tree)
    ├─ Serial (sequential)
    ├─ Parallel (concurrent)
    └─ ModuleAdapter (function wrapper)
    ↓
Output Data
```

## 1. Context

Thread-safe dictionary wrapper for sharing data across pipeline stages.

```python
from parasel.core.context import Context

# Create
context = Context({"query": "search term"}, thread_safe=True)

# Read
value = context.get("key", default=None)
value = context["key"]

# Write
context["result"] = "value"
context.set("result", "value")

# Parallel accumulation (atomic)
context.accumulate("results", new_item)
# Automatically creates list and appends
```

### Key Methods
- `get(key, default)` - Safe read
- `set(key, value)` / `[key] = value` - Write
- `accumulate(key, value)` - Thread-safe list append
- `keys()`, `values()`, `items()` - Dict interface

## 2. Node (Abstract Base)

All pipeline components inherit from Node.

```python
class Node(ABC):
    def __init__(self, name=None, timeout=None, retries=0):
        pass
    
    @abstractmethod
    def run(self, context: Context) -> None:
        """Execute the node"""
        pass
    
    async def run_async(self, context: Context) -> None:
        """Async execution"""
        pass
```

### Node Types

#### Serial
Sequential execution of child nodes.

```python
from parasel import Serial

pipeline = Serial([
    step1,
    step2,
    step3
], name="MyPipeline", continue_on_error=False)
```

**Options:**
- `continue_on_error=True` - Keep going if a step fails

#### Parallel
Concurrent execution of child nodes.

```python
from parasel import Parallel

pipeline = Parallel([
    task_a,
    task_b,
    task_c
], max_workers=3, fail_fast=True)
```

**Options:**
- `max_workers` - Thread pool size (default: number of children)
- `fail_fast=True` - Stop on first error (default)
- `fail_fast=False` - Run all, collect errors

## 3. ModuleAdapter

Wraps user functions into Node interface.

### Function Signature

```python
def my_function(context: Context, out_name: str, **kwargs):
    """
    Args:
        context: Shared data store
        out_name: Key to write result to
        **kwargs: Custom arguments
    """
    # Read input
    input_val = context.get("input_key")
    
    # Process
    result = process(input_val)
    
    # Write output
    context[out_name] = result
```

### Async Support

```python
async def my_async_function(context: Context, out_name: str, **kwargs):
    result = await api_call()
    context[out_name] = result
```

ModuleAdapter automatically detects and handles async functions.

### Creating Nodes

```python
from parasel import ModuleAdapter

node = ModuleAdapter(
    func=my_function,
    out_name="result",      # Output key
    name="MyNode",          # Optional: node name
    timeout=10.0,           # Optional: timeout in seconds
    retries=3,              # Optional: retry count
    custom_arg="value"      # Custom kwargs passed to func
)
```

## 4. Dynamic Parallel Execution

### ByArgs - Cartesian Product

Execute same function with different argument values in parallel.

```python
from parasel import ByArgs, Parallel, ModuleAdapter

def translate(context: Context, language: str, out_name: str, **kwargs):
    text = context.get("text")
    translated = translate_api(text, language)
    context[out_name] = translated

node = ModuleAdapter(translate, out_name="translations")

pipeline = Parallel([
    ByArgs(node, args={"language": ["en", "ko", "ja"]})
])
# Executes: translate(language="en"), translate(language="ko"), translate(language="ja")
# Results accumulated in context["translations"] as list: [en_result, ko_result, ja_result]
```

**Multiple Parameters:**
```python
ByArgs(node, args={
    "language": ["en", "ko"],
    "format": ["text", "html"]
})
# Creates 4 executions: (en,text), (en,html), (ko,text), (ko,html)
```

### ByKeys - Dynamic List Processing

Read list from Context and execute function on each item in parallel.

```python
from parasel import ByKeys, Parallel, ModuleAdapter

def search(context: Context, query: str, out_name: str, **kwargs):
    results = search_api(query)
    context[out_name] = results

search_node = ModuleAdapter(search, out_name="search_results")

# Assume context["queries"] = ["query1", "query2", "query3"]
pipeline = Parallel([
    ByKeys(search_node, keys=["queries"], input_key_name="query")
])
# Executes: search(query="query1"), search(query="query2"), search(query="query3")
# Results in context["search_results"] as list
```

**Options:**
- `keys` - List of Context keys to read (must be lists)
- `input_key_name` - Function parameter name to pass each item to (default: "input")

## 5. TaskRegistry

Manage multiple versions of pipelines.

```python
from parasel.registry import TaskRegistry

registry = TaskRegistry()

# Register v1.0.0
registry.register(
    task_id="search",
    version="1.0.0",
    node=search_pipeline_v1,
    description="Search pipeline v1",
    requires=["query"],           # Input keys
    produces=["results"],          # Output keys
    tags=["search", "web"],
    metadata={"author": "team"},
    mark_stable=True              # Mark as stable version
)

# Register v2.0.0
registry.register(
    task_id="search",
    version="2.0.0",
    node=search_pipeline_v2,
    description="Search pipeline v2 with caching"
)

# Retrieve
task = registry.get("search", version="latest")   # v2.0.0
task = registry.get("search", version="stable")   # v1.0.0
task = registry.get("search", version="1.0.0")    # Specific

# List
versions = registry.list_versions("search")  # ["1.0.0", "2.0.0"]
all_tasks = registry.list_tasks()            # ["search", ...]
```

### Semantic Versioning

Follow semver (MAJOR.MINOR.PATCH):
- **MAJOR**: Breaking changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes

## 6. Execution

### Direct Execution

```python
from parasel import Run

result = Run(
    user_input={"query": "search term"},
    task="search",
    version="stable",
    registry=registry
)

if result["success"]:
    data = result["data"]  # Context dict
    print(data["results"])
else:
    print(result["errors"])
```

### FastAPI Deployment

```python
from parasel.api.fastapi_app import create_app

app = create_app(
    registry=registry,
    title="My AI API",
    description="Pipeline API",
    version="1.0.0"
)

# Run: uvicorn api:app --reload
```

**Endpoints:**
- `GET /tasks` - List all tasks
- `GET /tasks/{task_id}` - Task info (all versions)
- `POST /run/{task_id}` - Execute task

**Request:**
```json
{
  "data": {"query": "search term"},
  "version": "stable"
}
```

**Response:**
```json
{
  "success": true,
  "data": {"results": [...]},
  "task_id": "search",
  "version": "1.0.0",
  "duration": 1.234
}
```

## 7. Error Handling

### Node-Level

```python
# Retry on failure
ModuleAdapter(func, out_name="result", retries=3)

# Timeout
ModuleAdapter(func, out_name="result", timeout=10.0)
```

### Pipeline-Level

```python
# Serial: continue on error
Serial([step1, step2, step3], continue_on_error=True)

# Parallel: collect all errors
Parallel([task1, task2, task3], fail_fast=False)
```

## 8. Best Practices

### Module Design
- **Single Responsibility**: Each module does one thing
- **Pure Functions**: Minimize side effects
- **Clear Signatures**: Always use `context`, `out_name`, `**kwargs`
- **Async for I/O**: Use async functions for network/disk operations

### Pipeline Design
- **Descriptive Names**: Name nodes clearly
- **Minimize Context Keys**: Only store necessary data
- **Expose Sparingly**: Use `.expose()` to hide intermediate results
- **Handle Errors**: Set appropriate retry/timeout/error policies

### Performance
- **Parallelize Independent Tasks**: Use Parallel for operations without dependencies
- **Batch Operations**: Use ByArgs/ByKeys for repeated operations
- **Async I/O**: Prefer async functions for I/O-bound tasks
- **Thread Safety**: Enable `thread_safe=True` for Context in Parallel nodes
