---
name: parasel
version: 1.0.0
description: Build versioned AI pipelines with Serial/Parallel composition patterns and deploy as FastAPI services
author: Parasel Framework
license: MIT
tags:
  - pipeline
  - ai-workflow
  - fastapi
  - parallel-execution
  - async
compatibility: Requires Python 3.8+, FastAPI, Pydantic. Optional: OpenRouter API for LLM calls.
---

# Parasel: AI Pipeline Framework

## What This Skill Does

Parasel helps you build complex AI pipelines using composable Serial and Parallel patterns. It provides:

- **Structured Pipeline Composition**: Combine functions into tree structures using Serial (sequential) and Parallel (concurrent) nodes
- **Dynamic Parallel Execution**: Use ByArgs/ByKeys to run the same function with different arguments or data in parallel
- **Version Management**: Manage multiple pipeline versions with semantic versioning (latest/stable/specific)
- **FastAPI Integration**: Automatically expose pipelines as REST API endpoints
- **Async Support**: Seamlessly handle both sync and async functions

## When to Use This Skill

Use Parasel when you need to:

- Build multi-step AI workflows (LLM calls, searches, processing)
- Execute operations in parallel (multi-language processing, multi-model inference)
- Version and deploy AI pipelines as APIs
- Manage complex dependencies between pipeline stages
- Handle both synchronous and asynchronous operations

## Quick Start

### 1. Create Module Functions

```python
# modules/extract.py
from parasel.core.context import Context

def extract_keywords(context: Context, out_name: str, **kwargs):
    query = context.get("query")
    keywords = llm_extract(query)  # Your implementation
    context[out_name] = keywords
```

### 2. Compose Pipeline

```python
# tasks/my_pipeline.py
from parasel import Serial, Parallel, ModuleAdapter

extract = ModuleAdapter(extract_keywords, out_name="keywords")
search = ModuleAdapter(web_search, out_name="results")

pipeline = Serial([
    extract,
    search
])
```

### 3. Deploy

```python
# api.py
from parasel.api.fastapi_app import create_app
from parasel.registry import TaskRegistry

registry = TaskRegistry()
registry.register("search", "1.0.0", pipeline, mark_stable=True)

app = create_app(registry=registry)
# Run: uvicorn api:app
```

## Core Concepts

See [references/core-concepts.md](references/core-concepts.md) for detailed documentation on:

- Context (shared data store)
- Node architecture (Serial, Parallel, ModuleAdapter)
- Module function signatures
- Dynamic parallel execution (ByArgs, ByKeys)
- Task registry and versioning

## Common Patterns

### Multi-Language Processing
```python
Parallel([
    ByArgs(translate, args={"language": ["en", "ko", "ja"]})
])
```

### Multi-Model Ensemble
```python
Parallel([
    ModuleAdapter(gpt4_call, out_name="gpt4"),
    ModuleAdapter(claude_call, out_name="claude")
])
```

### Query Expansion → Search → Aggregate
```python
Serial([
    expand_queries,
    Parallel([ByKeys(search, keys=["queries"])]),
    aggregate_results
])
```

## Documentation

- [Core Concepts](references/core-concepts.md) - Architecture and key components
- [Usage Guide](references/usage-guide.md) - Step-by-step implementation guide
- [API Reference](references/api-reference.md) - Complete API documentation
- [Patterns](references/patterns.md) - Common pipeline patterns
- [Troubleshooting](references/troubleshooting.md) - Common issues and solutions

## Examples

See `examples/` directory for complete working examples:

- `simple_pipeline.py` - Basic Serial/Parallel usage
- `multi_language.py` - ByArgs for multi-language processing
- `web_recommend.py` - Complete real-world pipeline
- `fastapi_deploy.py` - API deployment example

## Project Structure

When building with Parasel, use this structure:

```
your-project/
├── modules/          # Reusable functions
│   ├── llm/
│   └── search/
├── tasks/            # Pipeline definitions
│   └── my_task.py
├── api.py            # FastAPI deployment
└── requirements.txt
```

## Installation

```bash
cd /path/to/parasel
pip install -r requirements.txt
```

## Key Features Summary

| Feature | Description |
|---------|-------------|
| **Serial** | Execute nodes sequentially |
| **Parallel** | Execute nodes concurrently |
| **ByArgs** | Same function, different args, parallel |
| **ByKeys** | Dynamic parallel on list items |
| **TaskRegistry** | Version management (semver) |
| **FastAPI** | Auto-generate REST API |
| **Async** | Native async/await support |

## Learning Path

1. Start with [Core Concepts](references/core-concepts.md) to understand architecture
2. Follow [Usage Guide](references/usage-guide.md) to build your first pipeline
3. Study [Patterns](references/patterns.md) for common use cases
4. Check [examples/](examples/) for working examples
5. Reference [API docs](references/api-reference.md) as needed

## Support

- Examples: `/Users/deliciouscat/projects/parasel/examples/`
- Real project: `/Users/deliciouscat/projects/WizPerch-ai-pipeline/`
- Framework code: `/Users/deliciouscat/projects/parasel/parasel/`
