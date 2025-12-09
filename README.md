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

# 표준 사용 예.
user_input = {
    # 필수 입력값.
    "requester_type": "user",   # 요청 주체가 user일수도 있고, page일 수도 있고...
    "id": "USER_SERIALS",
    "task": "search",
    # task 별 상이한 입력값.
    "query": "이 페이지에서 \'절차적 생성\'이 의미하는 바는?",
    "page": "... extracted HTML contents ..."
}

Run(user_input, task=user_input.task, version="newest")
# task 입력 없을 시 1) user_input.task 참조 2) 그마저도 없으면 Error Messege
```

### 모듈 구현 예시
```py
# modules/llm/KeywordExtraction.py
def KeywordExtraction(~, args):
    ...
    args['keywords'] = keyword_list

# modules/llm/Summary.py
def Summary(~, args):
    ...
    args['']
```

### task 구현 예시
```py
# tasks/search.py
from modules.llm import KeywordExtraction, Summary

search = Serial([
    KeywordExtraction(~),
    Parallel([
        Summarize("gemini-pro"),
        Summarize("Claude-haiku"),
    ])
])
```


# 기반 라이브러리
다음의 프레임워크와의 호환성을 우선시 한다.
- FastAPI
- Pydantic AI
- OpenRouter
- Convex