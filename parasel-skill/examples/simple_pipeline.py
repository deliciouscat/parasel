"""
Simple Pipeline Example

Demonstrates basic Serial and Parallel execution.
"""

import sys
from pathlib import Path

# Add parasel to path
parasel_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parasel_path))

from parasel import Serial, Parallel, ModuleAdapter
from parasel.core.context import Context


def add_ten(context: Context, out_name: str, **kwargs):
    """Add 10 to input"""
    x = context.get("x", 0)
    result = x + 10
    print(f"[AddTen] {x} + 10 = {result}")
    context[out_name] = result


def multiply_two(context: Context, out_name: str, **kwargs):
    """Multiply input by 2"""
    x = context.get("x", 0)
    result = x * 2
    print(f"[MultiplyTwo] {x} * 2 = {result}")
    context[out_name] = result


def combine(context: Context, out_name: str, **kwargs):
    """Combine parallel results"""
    a = context.get("result_a", 0)
    b = context.get("result_b", 0)
    result = a + b
    print(f"[Combine] {a} + {b} = {result}")
    context[out_name] = result


def main():
    print("=" * 60)
    print("Simple Pipeline Example")
    print("=" * 60)
    
    # Build pipeline:
    # 1. x = 5
    # 2. Parallel:
    #    - a = x + 10 = 15
    #    - b = x * 2 = 10
    # 3. result = a + b = 25
    
    pipeline = Serial([
        Parallel([
            ModuleAdapter(add_ten, out_name="result_a"),
            ModuleAdapter(multiply_two, out_name="result_b"),
        ]),
        ModuleAdapter(combine, out_name="final_result"),
    ])
    
    # Execute
    context = Context({"x": 5}, thread_safe=True)
    print(f"\nInput: x = {context['x']}")
    print("\nExecuting pipeline...\n")
    
    pipeline.run(context)
    
    print(f"\n{'=' * 60}")
    print(f"Final Result: {context['final_result']}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
