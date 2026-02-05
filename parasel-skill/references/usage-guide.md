# Usage Guide

## Step-by-Step: Build Your First Pipeline

### Step 1: Project Structure

Create the following structure:

```
my-project/
├── modules/          # Domain-specific functions
│   ├── llm/
│   │   └── extract.py
│   └── search/
│       └── web.py
├── tasks/            # Pipeline definitions
│   └── search_task.py
├── api.py            # FastAPI deployment
├── main.py           # CLI execution
└── requirements.txt
```

### Step 2: Write Module Functions

#### modules/llm/extract.py
```python
from parasel.core.context import Context

def extract_keywords(context: Context, out_name: str, **kwargs):
    """Extract keywords from query"""
    query = context.get("query", "")
    
    # Your implementation (can call LLM API)
    keywords = your_llm_api.extract(query)
    
    # Write to context
    context[out_name] = keywords
```

#### modules/search/web.py
```python
from parasel.core.context import Context

async def web_search(context: Context, out_name: str, **kwargs):
    """Perform web search (async)"""
    keywords = context.get("keywords", [])
    
    # Async API call
    results = await search_api.query(keywords)
    
    context[out_name] = results
```

### Step 3: Compose Pipeline

#### tasks/search_task.py
```python
from parasel import Serial, Parallel, ModuleAdapter
from modules.llm.extract import extract_keywords
from modules.search.web import web_search

# Wrap functions into nodes
extract_node = ModuleAdapter(
    func=extract_keywords,
    out_name="keywords",
    name="ExtractKeywords"
)

search_node = ModuleAdapter(
    func=web_search,
    out_name="results",
    name="WebSearch"
)

# Compose pipeline
search_pipeline = Serial([
    extract_node,
    search_node
], name="SearchPipeline")

# Optional: Hide intermediate results in API response
search_pipeline = search_pipeline.expose(expose_keys=["results"])
```

### Step 4: Register Task

#### main.py (CLI execution)
```python
from parasel import Run
from parasel.registry import TaskRegistry
from tasks.search_task import search_pipeline

# Create registry
registry = TaskRegistry()

# Register task
registry.register(
    task_id="search",
    version="1.0.0",
    node=search_pipeline,
    description="Web search pipeline with keyword extraction",
    requires=["query"],
    produces=["keywords", "results"],
    tags=["search", "web"],
    mark_stable=True
)

# Execute
result = Run(
    user_input={"query": "AI trends 2024"},
    task="search",
    version="stable",
    registry=registry
)

# Check result
if result["success"]:
    print("Keywords:", result["data"]["keywords"])
    print("Results:", result["data"]["results"])
else:
    print("Error:", result["errors"])
```

### Step 5: Deploy as API

#### api.py
```python
from parasel.api.fastapi_app import create_app
from parasel.registry import TaskRegistry
from tasks.search_task import search_pipeline

# Registry and registration (same as main.py)
registry = TaskRegistry()
registry.register(
    task_id="search",
    version="1.0.0",
    node=search_pipeline,
    mark_stable=True
)

# Create FastAPI app
app = create_app(
    registry=registry,
    title="Search API",
    description="AI-powered search API",
    version="1.0.0"
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

#### Run Server
```bash
# Development
uvicorn api:app --reload

# Production
uvicorn api:app --host 0.0.0.0 --port 8000 --workers 4
```

#### Test API
```bash
# Using curl
curl -X POST http://localhost:8000/run/search \
  -H "Content-Type: application/json" \
  -d '{
    "data": {"query": "AI trends 2024"},
    "version": "stable"
  }'

# Using httpie
http POST localhost:8000/run/search \
  data:='{"query": "AI trends 2024"}' \
  version=stable
```

## Advanced Examples

### Example 1: Multi-Language Processing with ByArgs

```python
from parasel import Serial, Parallel, ByArgs, ModuleAdapter

# Function that accepts language parameter
async def translate_query(context: Context, language: str, out_name: str, **kwargs):
    query = context.get("query")
    translated = await translate_api(query, language)
    context[out_name] = translated

translate_node = ModuleAdapter(translate_query, out_name="translations")

pipeline = Serial([
    Parallel([
        ByArgs(translate_node, args={"language": ["en", "ko", "ja", "zh"]})
    ]),
    # context["translations"] = [en_text, ko_text, ja_text, zh_text]
    # ... rest of pipeline
])
```

### Example 2: Dynamic Search with ByKeys

```python
from parasel import Serial, Parallel, ByKeys, ModuleAdapter

# Expand query
expand_node = ModuleAdapter(expand_queries, out_name="expanded")
# context["expanded"] will be ["query1", "query2", "query3"]

# Search each expanded query
search_node = ModuleAdapter(web_search, out_name="all_results")

pipeline = Serial([
    expand_node,
    Parallel([
        ByKeys(search_node, keys=["expanded"], input_key_name="query")
    ]),
    # context["all_results"] = [results1, results2, results3]
])
```

### Example 3: Multi-Model Ensemble

```python
from parasel import Serial, Parallel, ModuleAdapter

# Define model-specific functions
gpt4_node = ModuleAdapter(gpt4_inference, out_name="gpt4")
claude_node = ModuleAdapter(claude_inference, out_name="claude")
gemini_node = ModuleAdapter(gemini_inference, out_name="gemini")

# Ensemble function
ensemble_node = ModuleAdapter(ensemble_results, out_name="final")

pipeline = Serial([
    # Call all models in parallel
    Parallel([
        gpt4_node,
        claude_node,
        gemini_node
    ]),
    # Combine results
    ensemble_node
])
```

### Example 4: Nested Pipelines

```python
# Sub-pipeline for preprocessing
preprocess = Serial([
    clean_node,
    tokenize_node
])

# Sub-pipeline for analysis
analyze = Parallel([
    sentiment_node,
    topic_node
])

# Main pipeline
main_pipeline = Serial([
    preprocess,
    analyze,
    aggregate_node
])
```

## Working with Context

### Reading Data
```python
def my_func(context: Context, out_name: str, **kwargs):
    # Safe read with default
    query = context.get("query", "")
    
    # Direct access (raises KeyError if missing)
    query = context["query"]
    
    # Check existence
    if "query" in context:
        query = context["query"]
```

### Writing Data
```python
def my_func(context: Context, out_name: str, **kwargs):
    result = process()
    
    # Write to specified key
    context[out_name] = result
    
    # Write to custom key
    context["custom_key"] = other_data
```

### Accumulating Results (Parallel)
```python
def my_func(context: Context, out_name: str, **kwargs):
    item = process()
    
    # Thread-safe accumulation (for use with ByArgs/ByKeys)
    # If key doesn't exist: creates [item]
    # If key exists: appends to list
    context.accumulate(out_name, item)
```

## Error Handling Strategies

### Strategy 1: Fail Fast (Default)
```python
# Stop on first error
pipeline = Serial([step1, step2, step3])

# Parallel stops on first error
pipeline = Parallel([task1, task2, task3], fail_fast=True)
```

### Strategy 2: Collect Errors
```python
# Continue despite errors in Serial
pipeline = Serial([step1, step2, step3], continue_on_error=True)

# Parallel runs all tasks, collects errors
pipeline = Parallel([task1, task2, task3], fail_fast=False)
```

### Strategy 3: Retry
```python
# Retry individual node
unreliable_node = ModuleAdapter(
    func=api_call,
    out_name="result",
    retries=3,
    timeout=10.0
)
```

### Strategy 4: Graceful Degradation
```python
def resilient_func(context: Context, out_name: str, **kwargs):
    try:
        result = expensive_operation()
    except Exception as e:
        # Fallback to simpler approach
        result = fallback_operation()
    
    context[out_name] = result
```

## Testing Pipelines

### Unit Test Individual Modules
```python
def test_extract_keywords():
    context = Context({"query": "test query"})
    extract_keywords(context, out_name="keywords")
    
    assert "keywords" in context
    assert len(context["keywords"]) > 0
```

### Integration Test Pipeline
```python
def test_search_pipeline():
    from tasks.search_task import search_pipeline
    from parasel.core.executor import Executor
    
    executor = Executor()
    result = executor.run(
        search_pipeline,
        initial_data={"query": "test"}
    )
    
    assert result.success
    assert "results" in result.context
```

### Test with Registry
```python
def test_registered_task():
    from parasel import Run
    
    result = Run(
        user_input={"query": "test"},
        task="search",
        version="1.0.0",
        registry=registry
    )
    
    assert result["success"]
    assert "results" in result["data"]
```

## Version Management

### Semantic Versioning
```python
# Initial release
registry.register("search", "1.0.0", pipeline_v1, mark_stable=True)

# Bug fix (backward compatible)
registry.register("search", "1.0.1", pipeline_v1_fixed)

# New feature (backward compatible)
registry.register("search", "1.1.0", pipeline_v1_with_cache)

# Breaking change
registry.register("search", "2.0.0", pipeline_v2, mark_stable=True)
```

### Using Versions
```python
# Latest version (2.0.0)
Run(input, task="search", version="latest", registry=registry)

# Stable version (2.0.0, marked as stable)
Run(input, task="search", version="stable", registry=registry)

# Specific version (1.0.1)
Run(input, task="search", version="1.0.1", registry=registry)
```

## Deployment Checklist

- [ ] Module functions are well-tested
- [ ] Pipeline composition is correct
- [ ] Task registered with appropriate version
- [ ] `requires` and `produces` documented
- [ ] Error handling strategy defined
- [ ] Timeouts and retries configured
- [ ] API response filtered with `.expose()`
- [ ] Environment variables configured (.env)
- [ ] Dependencies listed in requirements.txt
- [ ] Logging configured
- [ ] Health check endpoint tested

## Performance Tips

1. **Use Parallel for Independent Tasks**
   ```python
   # Good: Independent operations
   Parallel([translate, summarize, extract])
   
   # Bad: Dependent operations
   Parallel([fetch_data, process_data])  # process needs fetch result
   ```

2. **Prefer Async for I/O**
   ```python
   # Good: Async for API calls
   async def api_call(context, out_name, **kwargs):
       result = await client.post(...)
   
   # Less efficient: Sync blocks thread
   def api_call(context, out_name, **kwargs):
       result = requests.post(...)
   ```

3. **Batch with ByArgs/ByKeys**
   ```python
   # Good: Single parallel batch
   Parallel([ByArgs(translate, args={"lang": ["en", "ko", "ja"]})])
   
   # Bad: Sequential calls
   Serial([translate_en, translate_ko, translate_ja])
   ```

4. **Minimize Context Size**
   ```python
   # Good: Only essential data
   context["result"] = {"score": 0.9, "label": "positive"}
   
   # Bad: Large unnecessary data
   context["raw_response"] = huge_api_response
   ```
