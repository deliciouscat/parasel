# ByArgs와 ByKeys 기능 추가 요약

## 개요

Parasel 라이브러리에 `ByArgs`와 `ByKeys` 기능을 추가하여 동일한 함수를 다른 인자나 데이터로 병렬 실행할 수 있게 되었습니다.

## 추가된 기능

### 1. ByArgs 클래스
- **목적**: 동일한 함수를 서로 다른 파라미터로 여러 번 병렬 실행
- **위치**: `parasel/core/node.py`
- **특징**:
  - Cartesian product를 사용하여 모든 파라미터 조합 생성
  - 결과를 리스트로 자동 누적
  - Iterable 프로토콜 구현으로 `Parallel`과 자연스럽게 통합

### 2. ByKeys 클래스
- **목적**: Context에 저장된 리스트의 각 아이템에 대해 함수를 병렬 실행
- **위치**: `parasel/core/node.py`
- **특징**:
  - 실행 시점에 Context를 읽어 동적으로 노드 생성
  - 중첩 리스트를 자동으로 flatten
  - Node 서브클래스로 구현하여 지연 평가 지원

## 구현 세부사항

### 클래스 vs 함수 선택
**클래스로 구현한 이유:**
1. **확장성**: 나중에 더 복잡한 로직 추가 용이
2. **명확성**: 코드 의도가 분명하게 드러남
3. **타입 안전성**: IDE 자동완성과 타입 체크 용이
4. **지연 평가**: 필요한 시점까지 노드 생성 미룸
5. **상태 관리**: 설정을 객체로 캡슐화

### 핵심 설계 결정

#### 1. Parallel의 자동 Flatten
```python
# Parallel이 Iterable을 자동으로 펼침
Parallel([
    ByArgs(node, args={"language": ["en", "ko"]})  # 2개 노드로 확장됨
])
```

#### 2. 결과 누적 메커니즘
```python
# ModuleAdapter에 _accumulate_result 플래그 추가
node._accumulate_result = True  # 결과를 리스트에 추가
```

#### 3. ByKeys의 지연 평가
```python
# Node 서브클래스로 구현하여 실행 시점에 Context 읽기
class ByKeys(Node):
    def run(self, context: Context):
        # 실행 시점에 context에서 데이터 읽음
        all_items = []
        for key in self.keys:
            value = context[key]
            # 중첩 리스트 flatten
            for item in value:
                if isinstance(item, (list, tuple)):
                    all_items.extend(item)
                else:
                    all_items.append(item)
```

## 수정된 파일

### 핵심 파일
1. **`parasel/core/node.py`**
   - `ByArgs` 클래스 추가
   - `ByKeys` 클래스 추가
   - `Parallel.__init__` 수정 (Iterable 지원)

2. **`parasel/core/module_adapter.py`**
   - `_accumulate_result` 플래그 추가
   - 결과 누적 로직 구현

3. **`parasel/__init__.py`**
   - `ByArgs`, `ByKeys` export 추가

### 테스트 파일
4. **`tests/test_by_args_keys.py`** (신규)
   - 11개 테스트 케이스
   - ByArgs 기본/고급 사용법
   - ByKeys 기본/고급 사용법
   - 통합 시나리오

### 문서 파일
5. **`examples/by_args_keys_example.py`** (신규)
   - 실제 사용 예제
   - 다국어 웹 검색 파이프라인 시뮬레이션

6. **`docs/by_args_keys_guide.md`** (신규)
   - 상세 사용 가이드
   - 예제 코드
   - 제약사항 및 고급 사용법

7. **`README.md`**
   - 주요 특징에 ByArgs/ByKeys 추가
   - 예제 실행 명령 추가
   - 문서 링크 추가

## 테스트 결과

```
tests/test_by_args_keys.py - 11개 테스트 모두 통과
tests/test_core.py - 16개 테스트 모두 통과
전체 테스트 스위트 - 67개 테스트 모두 통과
```

## 사용 예제

### 기본 사용법
```python
from parasel import Serial, Parallel, ModuleAdapter, ByArgs, ByKeys

# ByArgs: 언어별 쿼리 확장
expansion = ModuleAdapter(query_expansion, out_name="queries")
Parallel([
    ByArgs(expansion, args={"language": ["en", "ko"]})
])

# ByKeys: 각 쿼리로 검색
search = ModuleAdapter(duckduckgo_search, out_name="results")
Parallel([
    ByKeys(search, keys=["queries"], input_key_name="input")
])
```

### 전체 파이프라인
```python
web_recommend = Serial([
    # Step 1: 언어별 쿼리 확장 (병렬)
    Parallel([
        ByArgs(query_expansion, args={"language": ["en", "ko"]})
    ]),
    
    # Step 2: 각 확장된 쿼리로 검색 (병렬)
    Parallel([
        ByKeys(duckduckgo_search, keys=["expanded_queries"])
    ]),
    
    # Step 3: 결과 정렬
    sorting,
])
```

## 주요 이점

1. **코드 간결성**: 반복적인 노드 생성 코드 제거
2. **병렬 실행**: 자동으로 병렬 처리
3. **타입 안전**: 명확한 인터페이스
4. **확장성**: 쉽게 새로운 기능 추가 가능
5. **자연스러운 통합**: 기존 Parasel API와 완벽히 호환

## 향후 개선 사항

1. **ByIndex**: 인덱스 기반 분할 실행
2. **ByBatch**: 배치 단위 처리
3. **ByCondition**: 조건부 실행
4. **성능 최적화**: 대량 데이터 처리 시 메모리 효율성 개선

## 결론

`ByArgs`와 `ByKeys`는 클래스로 구현하여 확장성, 명확성, 타입 안전성을 확보했습니다. 
Iterable 프로토콜과 Node 추상화를 활용하여 기존 Parasel 아키텍처와 자연스럽게 통합되었으며,
모든 테스트가 통과하여 안정성이 검증되었습니다.

