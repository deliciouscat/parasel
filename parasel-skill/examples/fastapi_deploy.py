"""
FastAPI Deployment Example

Shows how to deploy pipelines as REST API.
"""

import sys
from pathlib import Path

parasel_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parasel_path))

from parasel import Serial, ModuleAdapter
from parasel.core.context import Context
from parasel.registry import TaskRegistry
from parasel.api.fastapi_app import create_app


def process_text(context: Context, out_name: str, **kwargs):
    """Simple text processing"""
    text = context.get("text", "")
    
    # Process (example: uppercase and add exclamation)
    result = {
        "original": text,
        "processed": text.upper() + "!",
        "length": len(text)
    }
    
    context[out_name] = result


def main():
    print("=" * 60)
    print("FastAPI Deployment Example")
    print("=" * 60)
    
    # Create pipeline
    pipeline = Serial([
        ModuleAdapter(process_text, out_name="result")
    ]).expose(expose_keys=["result"])
    
    # Register task
    registry = TaskRegistry()
    registry.register(
        task_id="process",
        version="1.0.0",
        node=pipeline,
        description="Simple text processing",
        requires=["text"],
        produces=["result"],
        mark_stable=True
    )
    
    # Create FastAPI app
    app = create_app(
        registry=registry,
        title="Text Processing API",
        description="Example API for text processing",
        version="1.0.0"
    )
    
    print("\n" + "=" * 60)
    print("API Server Ready!")
    print("=" * 60)
    print("\nEndpoints:")
    print("  - GET  /              : API info")
    print("  - GET  /health        : Health check")
    print("  - GET  /tasks         : List tasks")
    print("  - POST /run/process   : Execute processing")
    print("\nExample Request:")
    print('  curl -X POST http://localhost:8000/run/process \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"data": {"text": "hello world"}, "version": "stable"}\'')
    print("\nStarting server on http://localhost:8000")
    print("Visit http://localhost:8000/docs for interactive API docs")
    print("=" * 60)
    
    # Run server
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
