# Parasel

AI 파이프라인을 직렬/병렬의 중첩 리스트로 통제하기 위한 프레임워크.  

## 기능적 요구사항
- 동일한 기능에 대해 다양한 파이프라인 versioning이 가능할 것
- FastAPI를 통한 배포가 단순하게 이루어질 것

## 주요 특징
- **Composite 패턴**: Serial/Parallel 노드로 파이프라인을 트리 구조로 조립
- **버전 관리**: TaskRegistry로 태스크별 여러 버전 관리 (latest, stable, semver)
- **타입 안전**: Pydantic 스키마로 입력/출력 검증
- **에러 핸들링**: 재시도, 타임아웃, fail-fast/collect 정책
- **FastAPI 통합**: 태스크를 HTTP 엔드포인트로 자동 노출

## 빠른 시작

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경 설정 (OpenRouter API 사용 시)
cp .env.example .env
# .env 파일에 OPENROUTER_API_KEY 설정

# 3. 예제 실행
python examples/simple_example.py          # 기본 파이프라인
python examples/search_example.py          # 더미 데이터 검색
python examples/openrouter_example.py      # 실제 LLM 사용 (API 키 필요)

# 4. FastAPI 서버 실행
python examples/api_example.py
```

자세한 사용법은 [USAGE.md](USAGE.md)를 참고하세요.

# 사용 방법

## Parallel / Serial

```py
from parasel import Run, Serial, Parallel, ModuleAdapter
# 표준 사용법: `modules/` 디렉토리에 각 컴포넌트를 정의한다.
# 각 모듈은 라이브러리 자체가 아니라 직접 구현하여 사용함.
from modules.llm.keyword_extraction import keyword_extraction
from modules.llm.summarize import summarize_gemini, summarize_haiku
from modules.search.duckduckgo import duckduckgo_search
```

### 표준 입력 예시
```py
user_input = {
    # 필수 입력값.
    "requester_type": "user",   # 요청 주체가 user일수도 있고, page일 수도 있고...
    "id": "USER_SERIALS",
    "task": "search",
    # task 별 상이한 입력값.
    "query": "이 페이지에서 \'절차적 생성\'이 의미하는 바는?",
    "page": "... extracted HTML contents ..."
}
```

### 모듈 구현 예시

모듈 함수는 `Context` 객체를 받아 입력을 읽고 출력을 씁니다.

```py
# modules/llm/keyword_extraction.py
from parasel.core.context import Context

def keyword_extraction(context: Context, out_name: str = "keywords", **kwargs):
    query = context.get("query", "")
    keywords = extract_keywords(query)  # 실제 구현
    context[out_name] = keywords

# modules/llm/summarize.py
def summarize(context: Context, model: str, out_name: str, **kwargs):
    page = context.get("page", "")
    summary = llm_api.summarize(page, model=model)  # 실제 구현
    context[out_name] = summary

# modules/llm/merge.py
def merge_summaries(context: Context, out_name: str = "summary", **kwargs):
    gem_summary = context.get("gemini-summary", "")
    hai_summary = context.get("haiku-summary", "")
    merged = combine_summaries(gem_summary, hai_summary)  # 실제 구현
    context[out_name] = merged

# modules/search/duckduckgo.py
def duckduckgo_search(context: Context, out_name: str = "search-result", **kwargs):
    query = context.get("query", "")
    results = ddg_api.search(query)  # 실제 구현
    context[out_name] = results
```

### task 구현 예시

`ModuleAdapter`로 함수를 Node로 래핑하고, `Serial`/`Parallel`로 파이프라인을 조립합니다.

```py
# tasks/search.py
from parasel import Serial, Parallel, ModuleAdapter
from modules.llm.keyword_extraction import keyword_extraction
from modules.llm.summarize import summarize_gemini, summarize_haiku
from modules.llm.merge import merge_summaries
from modules.search.duckduckgo import duckduckgo_search

# 각 모듈을 ModuleAdapter로 래핑
keyword = ModuleAdapter(keyword_extraction, out_name="keywords")
summ_gem = ModuleAdapter(summarize_gemini, out_name="gemini-summary")
summ_hai = ModuleAdapter(summarize_haiku, out_name="haiku-summary")
merge = ModuleAdapter(merge_summaries, out_name="summary")
search = ModuleAdapter(duckduckgo_search, out_name="search-result")

# Serial과 Parallel로 파이프라인 조립
search_pipeline = Serial([
    keyword,
    Parallel([summ_gem, summ_hai], timeout=10),
    merge,
    search,
])
```

### task 등록 및 실행

```py
from parasel import Run
from parasel.registry import TaskRegistry

# 레지스트리에 태스크 등록
registry = TaskRegistry()
registry.register(
    task_id="search",
    version="0.1.0",
    node=search_pipeline,
    requires=["query", "page"],
    produces=["keywords", "summary", "search-result"],
)

# 실행
result = Run(
    user_input=user_input,
    task="search",  # 또는 user_input["task"]에서 자동 추출
    version="latest",  # "latest", "stable", 또는 "0.1.0" 등
    registry=registry,
)

print(f"Success: {result['success']}")
print(f"Output: {result['data']}")
```

## FastAPI 배포

```py
from parasel import create_app
from parasel.registry import TaskRegistry

# 레지스트리에 태스크 등록
registry = TaskRegistry()
registry.register("search", "0.1.0", search_pipeline)

# FastAPI 앱 생성
app = create_app(registry=registry)

# uvicorn으로 실행
# uvicorn your_module:app --reload
```

API 엔드포인트:
- `GET /tasks` - 등록된 태스크 목록
- `GET /tasks/{task_id}` - 태스크 정보
- `POST /run/{task_id}` - 태스크 실행

## 프로젝트 구조

```
your-project/
├── modules/          # 사용자 정의 모듈 (프레임워크 사용자가 작성)
│   ├── llm/
│   └── search/
├── tasks/            # 파이프라인 정의 (프레임워크 사용자가 작성)
│   └── search.py
└── main.py           # FastAPI 앱 또는 실행 스크립트
```

## 기반 라이브러리

- **FastAPI** - REST API 프레임워크
- **Pydantic** - 데이터 검증
- **Packaging** - 버전 관리

향후 다음과의 통합 예정:
- Pydantic AI
- OpenRouter
- Convex

## 개발 및 테스트

```bash
# 단위 테스트 실행
pytest -m "not integration"

# 통합 테스트 포함 (API 키 필요)
pytest

# OpenRouter 통합 테스트
pytest tests/test_openrouter.py -m integration -v

# 코드 포매팅
black parasel/

# 린팅
ruff parasel/
```

## 라이선스

MIT

## 문서

- [설계 문서](docs/architecture.md) - 아키텍처 및 디자인 패턴
- [사용 가이드](USAGE.md) - 상세 사용법 및 예제