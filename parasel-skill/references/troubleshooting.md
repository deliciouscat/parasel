# Troubleshooting Guide

## Common Issues and Solutions

### Issue 1: Context Key Not Found

**Symptom**:
```
KeyError: 'some_key'
```

**Cause**: Node trying to read key that doesn't exist in Context.

**Solution**:
```python
# Bad
value = context["key"]

# Good - use get() with default
value = context.get("key", default_value)

# Good - check existence
if "key" in context:
    value = context["key"]
```

---

### Issue 2: Context Key Overwritten

**Symptom**: Expected data in Context is replaced by different data.

**Cause**: Multiple nodes writing to same `out_name`.

**Solution**: Use unique keys for each node.
```python
# Bad
node1 = ModuleAdapter(func1, out_name="result")
node2 = ModuleAdapter(func2, out_name="result")  # Overwrites!

# Good
node1 = ModuleAdapter(func1, out_name="step1_result")
node2 = ModuleAdapter(func2, out_name="step2_result")
```

---

### Issue 3: ByArgs/ByKeys Returns Nested Lists

**Symptom**:
```python
# Expected: [result1, result2, result3]
# Got: [[result1], [result2], [result3]]
```

**Cause**: ByArgs/ByKeys accumulates results in a list, and your function also returns a list.

**Solution**: Flatten the results.
```python
def flatten_list(context: Context, out_name: str, in_name: str, **kwargs):
    nested = context.get(in_name, [])
    
    if isinstance(nested, list) and nested and isinstance(nested[0], list):
        # Flatten nested list
        flat = [item for sublist in nested for item in sublist]
    else:
        # Already flat
        flat = nested
    
    context[out_name] = flat

flatten = ModuleAdapter(flatten_list, out_name="flat", in_name="nested")
```

---

### Issue 4: Async Function Not Working

**Symptom**: Async function seems to run but doesn't await properly, or raises errors.

**Cause**: ModuleAdapter handles async automatically, but pipeline execution might be synchronous.

**Solution**: Ensure proper async handling.
```python
# Option 1: Use FastAPI (handles async automatically)
app = create_app(registry=registry)

# Option 2: Use async executor
from parasel.core.executor import Executor
executor = Executor()
result = await executor.run_async(pipeline, initial_data=data)

# Option 3: Use Run with async runtime
import asyncio
result = asyncio.run(executor.run_async(pipeline, initial_data=data))
```

---

### Issue 5: Timeout Not Working

**Symptom**: Node doesn't timeout as configured.

**Cause**: Timeout applies to Node.run() execution, not internal blocking operations.

**Solution**: Implement internal timeout or use async with asyncio.wait_for().
```python
# For sync functions with blocking operations
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")

def my_function(context: Context, out_name: str, **kwargs):
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(10)  # 10 second timeout
    
    try:
        result = long_running_operation()
    finally:
        signal.alarm(0)  # Cancel alarm
    
    context[out_name] = result

# For async functions
import asyncio

async def my_async_function(context: Context, out_name: str, **kwargs):
    try:
        result = await asyncio.wait_for(
            long_running_async_operation(),
            timeout=10.0
        )
    except asyncio.TimeoutError:
        result = None  # or fallback
    
    context[out_name] = result
```

---

### Issue 6: Parallel Execution Race Condition

**Symptom**: Inconsistent results or corrupted data in Parallel execution.

**Cause**: Multiple threads writing to Context without thread-safety.

**Solution**: Enable thread-safe Context.
```python
# Bad
context = Context(initial_data)

# Good
context = Context(initial_data, thread_safe=True)

# Or use accumulate() for parallel writes
def my_function(context: Context, out_name: str, **kwargs):
    result = process()
    context.accumulate(out_name, result)  # Thread-safe
```

---

### Issue 7: Module Not Found Import Error

**Symptom**:
```
ImportError: cannot import name 'my_module'
```

**Cause**: Python can't find your module files.

**Solution**: Add project root to Python path.
```python
# At top of main script
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Now imports work
from modules.llm.extract import extract_keywords
```

---

### Issue 8: FastAPI Returns Empty Response

**Symptom**: API returns `{"success": true, "data": {}}` with no actual data.

**Cause**: Pipeline nodes write to Context keys, but they're not exposed or have wrong names.

**Solution**: Check node `out_name` and use `.expose()` if needed.
```python
# Check what keys are in context
print(f"Context keys: {list(result.context.keys())}")

# Expose specific keys in API response
pipeline = Serial([...]).expose(expose_keys=["final_result"])

# Or check TaskRegistry produces
registry.register(
    task_id="my_task",
    version="1.0.0",
    node=pipeline,
    produces=["final_result"]  # Should match actual Context keys
)
```

---

### Issue 9: Out of Memory

**Symptom**: Process killed or `MemoryError`.

**Cause**: Context accumulating too much data, especially with ByArgs/ByKeys.

**Solution**: Clear unnecessary data, or stream results.
```python
def cleanup_intermediate(context: Context, out_name: str, **kwargs):
    # Keep only what's needed
    final = context.get("final_result")
    
    # Clear large intermediate results
    for key in list(context.keys()):
        if key != "final_result" and key != out_name:
            del context._data[key]
    
    context[out_name] = final

# Add cleanup step
pipeline = Serial([
    step1,
    step2,
    ModuleAdapter(cleanup_intermediate, out_name="cleaned")
])
```

---

### Issue 10: Version Not Found

**Symptom**:
```
TaskNotFoundError: Task 'my_task' version 'stable' not found
```

**Cause**: No version marked as stable, or wrong version specified.

**Solution**: Check registered versions and mark stable.
```python
# List available versions
versions = registry.list_versions("my_task")
print(f"Available: {versions}")

# Mark a version as stable
registry.mark_stable("my_task", "1.0.0")

# Or use 'latest' instead
Run(input, task="my_task", version="latest", registry=registry)
```

---

## Debugging Tips

### 1. Add Logging

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def my_function(context: Context, out_name: str, **kwargs):
    logger.info(f"[{out_name}] Starting with input: {context.get('input')}")
    
    result = process()
    
    logger.info(f"[{out_name}] Completed with result: {result}")
    context[out_name] = result
```

### 2. Use Execution Hooks

```python
from parasel.core.executor import Executor, ExecutionPolicy

def before_node(node, context):
    print(f"Starting {node.name}")
    print(f"Context keys: {list(context.keys())}")

def after_node(node, context, error):
    if error:
        print(f"Error in {node.name}: {error}")
    else:
        print(f"Completed {node.name}")

policy = ExecutionPolicy(
    before_node=before_node,
    after_node=after_node
)

executor = Executor(policy=policy)
```

### 3. Inspect Context at Each Step

```python
def debug_context(context: Context, out_name: str, **kwargs):
    print(f"\n=== Context Snapshot ===")
    for key, value in context.items():
        print(f"{key}: {type(value)} = {value}")
    print("=" * 30 + "\n")
    
    context[out_name] = "debug_complete"

# Insert debug nodes
pipeline = Serial([
    step1,
    ModuleAdapter(debug_context, out_name="debug1"),
    step2,
    ModuleAdapter(debug_context, out_name="debug2"),
])
```

### 4. Test Nodes Individually

```python
# Test single node
def test_extract_keywords():
    context = Context({"query": "test query"})
    extract_keywords(context, out_name="keywords")
    
    assert "keywords" in context
    print(f"Result: {context['keywords']}")

# Test sub-pipeline
def test_preprocess_stage():
    preprocess = Serial([clean, tokenize, normalize])
    executor = Executor()
    
    result = executor.run(preprocess, initial_data={"text": "test"})
    assert result.success
    print(f"Preprocess output: {result.context.to_dict()}")
```

### 5. Use try-except in Functions

```python
def robust_function(context: Context, out_name: str, **kwargs):
    try:
        result = risky_operation(context)
    except Exception as e:
        # Log error
        logger.error(f"Error in robust_function: {e}", exc_info=True)
        
        # Provide fallback or re-raise
        result = {"error": str(e), "success": False}
        # or: raise
    
    context[out_name] = result
```

---

## Performance Issues

### Slow Pipeline Execution

**Diagnosis**:
```python
from parasel.core.executor import Executor

executor = Executor()
result = executor.run(pipeline, initial_data=data)

print(f"Total duration: {result.duration}s")
# Check node_timings if available
```

**Solutions**:
1. Parallelize independent operations
2. Use async for I/O operations
3. Add caching for repeated operations
4. Reduce data size in Context
5. Profile individual functions

### High Memory Usage

**Solutions**:
1. Clear large intermediate results
2. Stream results instead of accumulating
3. Use generators where possible
4. Limit ByArgs/ByKeys batch size

### API Response Time

**Solutions**:
1. Add caching layer (Redis)
2. Optimize hot path functions
3. Use connection pooling
4. Add timeout limits
5. Consider async execution

---

## Getting Help

### Check Examples
- `/Users/deliciouscat/projects/parasel/examples/`
- `/Users/deliciouscat/projects/WizPerch-ai-pipeline/`

### Read Source Code
- `/Users/deliciouscat/projects/parasel/parasel/core/`
- Look for similar patterns in tests: `/Users/deliciouscat/projects/parasel/tests/`

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check FastAPI Logs
```bash
uvicorn api:app --log-level debug
```
