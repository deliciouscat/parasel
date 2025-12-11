"""간단한 사용 예제"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from parasel import Serial, Parallel, ModuleAdapter, Executor, Context


def add_ten(context: Context, out_name: str, **kwargs):
    """입력값에 10을 더합니다"""
    x = context.get("x", 0)
    result = x + 10
    context[out_name] = result
    print(f"[AddTen] {x} + 10 = {result}")


def multiply_two(context: Context, out_name: str, **kwargs):
    """입력값에 2를 곱합니다"""
    x = context.get("x", 0)
    result = x * 2
    context[out_name] = result
    print(f"[MultiplyTwo] {x} * 2 = {result}")


def square(context: Context, out_name: str, **kwargs):
    """입력값을 제곱합니다"""
    x = context.get("x", 0)
    result = x ** 2
    context[out_name] = result
    print(f"[Square] {x}^2 = {result}")


def combine(context: Context, out_name: str, **kwargs):
    """병렬 결과들을 합산합니다"""
    a = context.get("result_a", 0)
    b = context.get("result_b", 0)
    result = a + b
    context[out_name] = result
    print(f"[Combine] {a} + {b} = {result}")


def main():
    """간단한 파이프라인 예제"""
    
    print("=" * 60)
    print("Parasel 간단한 파이프라인 예제")
    print("=" * 60)
    
    # 파이프라인 구성:
    # 1. x = 5
    # 2. Parallel:
    #    - a = (x + 10) = 15
    #    - b = (x * 2) = 10
    # 3. result = a + b = 25
    
    pipeline = Serial([
        Parallel([
            ModuleAdapter(add_ten, out_name="result_a", name="PathA"),
            ModuleAdapter(multiply_two, out_name="result_b", name="PathB"),
        ], name="ParallelOps"),
        ModuleAdapter(combine, out_name="final_result", name="Combine"),
    ], name="SimplePipeline")
    
    # 초기 데이터
    initial_data = {"x": 5}
    print(f"\n[초기 데이터] x = {initial_data['x']}")
    print()
    
    # 실행
    executor = Executor()
    result = executor.run(pipeline, initial_data=initial_data)
    
    print("\n[실행 결과]")
    print(f"Success: {result.success}")
    print(f"Duration: {result.duration:.3f}초")
    print(f"Final Result: {result.context['final_result']}")
    print(f"All Context Keys: {list(result.context.keys())}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

