# ByArgs와 ByKeys 가이드

`ByArgs`와 `ByKeys`는 Parasel에서 동일한 함수를 여러 번 병렬로 실행할 때 사용하는 헬퍼 클래스입니다.

## 개요

### ByArgs
**함수 호출 시점에 다른 인자를 주입하여 여러 번 실행**

- 동일한 함수를 서로 다른 파라미터로 여러 번 실행
- Cartesian product를 사용하여 모든 파라미터 조합 생성
- 결과는 지정된 `out_name`에 리스트로 누적

### ByKeys
**Context에 저장된 리스트의 각 아이템에 대해 함수를 실행**

- 실행 시점에 Context를 읽어 동적으로 노드 생성
- 중첩 리스트를 자동으로 flatten
- 각 아이템마다 함수를 병렬 실행

## 사용 예제

### ByArgs 기본 사용법

```python
from parasel import ModuleAdapter, Parallel, ByArgs, Context

def query_expansion(context: Context, language: str, out_name: str = None, **kwargs):
    """언어별 쿼리 확장"""
    if language == "en":
        return ["query1_en", "query2_en"]
    else:
        return ["query1_ko", "query2_ko"]

expansion = ModuleAdapter(query_expansion, out_name="queries")

# ByArgs로 언어별 실행
pipeline = Parallel([
    ByArgs(expansion, args={"language": ["en", "ko"]})
])

ctx = Context()
pipeline.run(ctx)

# 결과: ctx["queries"] = [
#   ["query1_en", "query2_en"],
#   ["query1_ko", "query2_ko"]
# ]
```

### ByArgs 다중 파라미터 (Cartesian Product)

```python
def search(context: Context, engine: str, max_results: int, out_name: str = None, **kwargs):
    return f"{engine}:{max_results}"

search_node = ModuleAdapter(search, out_name="results")

# 2개 엔진 × 2개 결과 수 = 4개 조합
pipeline = Parallel([
    ByArgs(search_node, args={
        "engine": ["google", "bing"],
        "max_results": [5, 10]
    })
])

ctx = Context()
pipeline.run(ctx)

# 결과: ctx["results"] = ["google:5", "google:10", "bing:5", "bing:10"]
```

### ByKeys 기본 사용법

```python
def search(context: Context, input: str, out_name: str = None, **kwargs):
    """검색 실행"""
    return f"result_for_{input}"

search_node = ModuleAdapter(search, out_name="search_results")

# Context에 쿼리 리스트 준비
ctx = Context({"queries": ["query1", "query2", "query3"]})

# ByKeys로 각 쿼리에 대해 검색
pipeline = Parallel([
    ByKeys(search_node, keys=["queries"], input_key_name="input")
])

pipeline.run(ctx)

# 결과: ctx["search_results"] = [
#   "result_for_query1",
#   "result_for_query2",
#   "result_for_query3"
# ]
```

### ByKeys 중첩 리스트 자동 Flatten

```python
# Context에 중첩 리스트가 있는 경우
ctx = Context({
    "expanded_queries": [
        ["query1_en", "query2_en"],  # 영어 쿼리
        ["query1_ko", "query2_ko"]   # 한국어 쿼리
    ]
})

# ByKeys는 자동으로 flatten
pipeline = Parallel([
    ByKeys(search_node, keys=["expanded_queries"], input_key_name="input")
])

pipeline.run(ctx)

# 4개 쿼리 모두에 대해 검색 실행
# ctx["search_results"] = [
#   "result_for_query1_en",
#   "result_for_query2_en",
#   "result_for_query1_ko",
#   "result_for_query2_ko"
# ]
```

## 전체 파이프라인 예제

```python
from parasel import Serial, Parallel, ModuleAdapter, ByArgs, ByKeys, Executor

def query_expansion(context: Context, language: str, out_name: str = None, **kwargs):
    """언어별 쿼리 확장"""
    if language == "en":
        return ["python tutorial", "learn python"]
    else:
        return ["파이썬 튜토리얼", "파이썬 배우기"]

def search(context: Context, input: str, out_name: str = None, **kwargs):
    """검색 실행"""
    return {"query": input, "results": [f"result1", f"result2"]}

def merge_results(context: Context, out_name: str = None, **kwargs):
    """결과 병합"""
    all_results = context.get("search_results", [])
    merged = []
    for result in all_results:
        merged.extend(result["results"])
    context[out_name] = merged

# 파이프라인 구성
expansion = ModuleAdapter(query_expansion, out_name="expanded_queries")
search_node = ModuleAdapter(search, out_name="search_results")
merge = ModuleAdapter(merge_results, out_name="final_results")

pipeline = Serial([
    # Step 1: 언어별 쿼리 확장 (병렬)
    Parallel([
        ByArgs(expansion, args={"language": ["en", "ko"]})
    ]),
    
    # Step 2: 각 확장된 쿼리로 검색 (병렬)
    Parallel([
        ByKeys(search_node, keys=["expanded_queries"], input_key_name="input")
    ]),
    
    # Step 3: 결과 병합
    merge,
])

# 실행
executor = Executor()
result = executor.run(pipeline, initial_data={"base_query": "python"})

print(f"최종 결과: {result.context['final_results']}")
# 2개 언어 × 각 2개 쿼리 × 각 2개 결과 = 8개 아이템
```

## 주요 특징

### ByArgs
1. **Cartesian Product**: 모든 파라미터 조합을 생성
2. **결과 누적**: 각 실행 결과를 리스트에 추가
3. **기존 kwargs 병합**: ModuleAdapter의 기존 kwargs와 병합

### ByKeys
1. **동적 노드 생성**: 실행 시점에 Context를 읽어 노드 생성
2. **자동 Flatten**: 중첩 리스트를 자동으로 펼침
3. **병렬 실행**: 내부적으로 Parallel 노드 사용

## 제약사항

1. **ModuleAdapter 전용**: 두 클래스 모두 `ModuleAdapter`와만 사용 가능
2. **ByKeys 리스트 요구**: `ByKeys`는 Context의 값이 리스트 또는 튜플이어야 함
3. **Thread-safe Context**: 병렬 실행 시 `thread_safe=True` 권장

## 고급 사용법

### 여러 ByArgs를 동시에 실행

```python
pipeline = Parallel([
    ByArgs(node1, args={"param": [1, 2]}),
    ByArgs(node2, args={"param": [10, 20]}),
])
```

### 여러 키를 병합하여 처리

```python
ctx = Context({
    "list1": ["a", "b"],
    "list2": ["c", "d"]
})

pipeline = Parallel([
    ByKeys(node, keys=["list1", "list2"], input_key_name="input")
])

# 4개 아이템 모두 처리: a, b, c, d
```

### 커스텀 input_key_name

```python
def my_func(context: Context, query: str, out_name: str = None, **kwargs):
    # 'query' 파라미터로 받음
    return process(query)

node = ModuleAdapter(my_func, out_name="results")

pipeline = Parallel([
    ByKeys(node, keys=["queries"], input_key_name="query")  # 'query'로 전달
])
```

## 참고

- 전체 예제: `examples/by_args_keys_example.py`
- 테스트 코드: `tests/test_by_args_keys.py`

