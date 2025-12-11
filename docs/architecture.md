# Parasel 미니 프레임워크 설계 제안

에이전트/모듈을 직렬·병렬 중첩 리스트로 정의해 실행하는 간이 프레임워크 설계 초안이다. Composite 패턴으로 파이프라인을 표현하고, Strategy/Registry 패턴으로 모듈 실행과 버전 관리를 분리한다.

## 1. 디렉터리/파일 구조 초안
```
parasel/
  __init__.py
  core/
    __init__.py
    node.py           # Composite: Node, Serial, Parallel
    context.py        # args/context 공유 객체
    executor.py       # 동기/비동기 실행 엔진, 타임아웃/리트라이
    module_adapter.py # Strategy: 모듈 실행 어댑터 (sync/async callable)
  registry/
    __init__.py
    task_registry.py  # Task/Version 등록, 검색, 메타데이터
    schemas.py        # 입력/출력 스키마, requires/produces
  api/
    __init__.py
    fastapi_app.py    # FastAPI 엔드포인트 (Run wrapper)
  modules/
    llm/
      keyword_extraction.py
      summarize.py
      merge.py
    search/
      duckduckgo.py
  tasks/
    search.py         # Serial/Parallel로 파이프라인 정의
  examples/
    search_example.py
  tests/
    test_core.py
    test_registry.py
    test_api.py
```

## 2. 코어 추상화 (Composite + Strategy)
- `Node`: `run(context)` 인터페이스. 공통 속성: `name`, `timeout`, `retries`, `metadata`.
- `Serial(Node)`: 순차 실행. 앞선 노드 실패 시 중단(옵션으로 continue_on_error).
- `Parallel(Node)`: 병렬 실행. 내부 풀/세마포어로 동시성 제한, 에러 수집 정책 설정(첫 실패 시 중단, 전부 완료 후 집계 등).
- `ModuleAdapter`: 모듈 실행 전략. 시그니처 `(context, out_name, **kwargs)` 또는 `(context, **kwargs)`를 래핑해 Node에 연결. 동기/비동기 구분.
- `Context`: `dict` 유사 객체로 `args` 저장. Lock-free 우선, 병렬 시 키 충돌 방지를 위해 out_name 고유 사용 권장. 옵셔널로 thread-safe 래퍼 제공.

### 기본 사용 예 (개념)
```py
keyword = ModuleAdapter(func=keyword_extraction, out_name="keyword")
summ_gem = ModuleAdapter(func=summarize_gemini, out_name="gempro-summary")
summ_hai = ModuleAdapter(func=summarize_haiku, out_name="haiku-summary")
merge   = ModuleAdapter(func=merge_summary, out_name="summary")
search  = ModuleAdapter(func=duckduckgo, out_name="search-result")

search_task = Serial([
    keyword,
    Parallel([summ_gem, summ_hai], timeout=10),
    merge,
    search,
])
```

## 3. 실행 엔진 설계
- 동기/비동기 공용 인터페이스 `Executor.run(node, context, policy)`.
- 정책 옵션:
  - `timeout` per-node, `retries` with backoff, `retry_on` 예외 타입 리스트.
  - `parallel_max_workers`: 병렬 노드의 동시 실행 제한.
  - `error_mode`: `fail_fast`(기본), `collect`(모든 에러 리스트 반환).
- 에러 전파: `ExecutionError`에 원인/노드명/컨텍스트 키 포함.
- 로깅/관측: 훅(`before_node`, `after_node`, `on_error`)으로 메트릭/로그 플러그인 부착.

## 4. 버전 관리와 태스크 레지스트리
- `TaskSpec`: `{id, version, node, schema_in, schema_out, requires, produces, tags, description}`.
- `TaskRegistry`:
  - `register(task_id, version, node, **meta)`
  - `get(task_id, version="latest"|"stable"|semver)`
  - `list(task_id)` → 등록된 버전 목록
  - 충돌 방지를 위해 `task_id` + `version` key 사용.
- `requires/produces`: context 키 의존성 문서화. 정적 검증(선행 키 체크)과 런타임 검증(실행 후 키 존재) 지원.
- 예시 등록:
```py
registry.register(
  task_id="search",
  version="0.1.0",
  node=search_task,
  requires=["query", "page"],
  produces=["summary", "search-result"],
  schema_in=SearchInModel,
  schema_out=SearchOutModel,
)
```

## 5. API 어댑터 (FastAPI 스켈레톤)
- 엔드포인트 예: `POST /run/{task_id}` 쿼리 `version`(옵션).
- 절차:
  1) 요청을 `schema_in`으로 검증.
  2) `TaskRegistry.get(task_id, version)`로 노드 획득.
  3) `Executor.run`으로 실행 후 `schema_out` 직렬화.
  4) 실행 메타(소요 시간, 노드별 상태) 포함한 응답 반환.
- 배포 시큐리티: API key/Bearer 토큰 미들웨어, 요청 사이즈 제한, 타임아웃 설정.

## 6. 예제 및 테스트 전략
- 예제: `examples/search_example.py`에서 README의 검색 파이프라인 재현, CLI 실행(`python -m examples.search_example`).
- 단위 테스트:
  - `test_core.py`: Serial/Parallel 실행, 타임아웃·리트라이, fail_fast/collect 검증.
  - `test_registry.py`: 버전 등록/조회, requires/produces 검증.
  - `test_api.py`: FastAPI TestClient로 happy-path/에러 응답 테스트.
- 추가: 부하 없는 가짜 모듈(fixture)로 실행 순서·병렬성 검증, Context 키 격리 테스트.

## 7. 적용 패턴 요약
- Composite: Node/Serial/Parallel 트리.
- Strategy: ModuleAdapter로 모듈 실행 방법 캡슐화.
- Registry/Factory: TaskRegistry로 버전별 실행체 반환.
- Template Method 훅: Executor의 before/after/on_error 콜백.
- Optionally Decorator: 모듈 레벨에서 retry/logging 래핑.

