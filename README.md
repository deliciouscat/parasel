# Parasel
AI 파이프라인을 직렬/병렬의 중첩 리스트로 통제하기 위한 프레임워크.  
기능적 요구사항:
- 동일한 기능에 대해 다양한 파이프라인 versioning이 가능할 것.
- FastAPI를 통한 배포가 단순하게 이루어질 것.

# 사용 방법

## Parallel / Serial
```py
from parasel import Run, Parallel, Serial
# 표준 사용법: `module` 디렉토리에 각 컴포넌트를 정의한다.
# 각 모듈은 라이브러리 자체가 아니라 직접 구현하여 사용함.
from modules.llm import Summarize, KeywordExtraction
from modules.retrieve import BM25, Embedding

# 표준 입력 예시.
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
```py
# modules/llm/KeywordExtraction.py
def KeywordExtraction(~, out_name, args):
    ...
    args[out_name] = keyword_list

# modules/llm/Summary.py
def Summary(~, out_name, args):
    ...
    args[out_name]

# modules/llm/Merge.py
def Merge(~, out_name, args):
    ...
    merged_summary = some_function(
        args["gemini-summary"], args["haiku-summary"]
        )
    ... 각 결과의 장점 취합 ...
    args[out_name] = merged_summary

# modules/llm/QueryExpansion.py
def QueryExpansion(~, args):
    ...
    args['query'] = search_query

# modules/search/DuckDuckGo.py
def DuckDuckGo(~, args):
    ...
    args['search_result'] = url_list
```

### task 구현 예시
```py
# tasks/search.py
from parasel import Task
from modules.llm import KeywordExtraction, Summary, ...

search = Serial([
    KeywordExtraction(~, out_name="keyword"),
    Parallel([
        Summarize("gemini-pro", out_name="gempro-summary"),
        Summarize("Claude-haiku", out_name="haiku-summary"),
    ]),
    Merge(~, out_name="summary"),
    DuckDuckGo(~, out_name="search-result")
])
```

### task 사용 명령

```py
Run(user_input, task=user_input.task, version="newest")
# 
# task 입력 없을 시 1) user_input.task 참조 2) 그마저도 없으면 Error Messege
```

# 기반 라이브러리
다음의 프레임워크와의 호환성을 우선시 한다.
- FastAPI
- Pydantic AI
- OpenRouter
- Convex