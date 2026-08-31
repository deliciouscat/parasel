# Parasel + Pydantic AI

Parasel은 Pydantic AI를 대체하지 않는다. Pydantic AI의 `Agent`가 모델 호출, tool 실행, 구조화된 출력 검증을 맡고, Parasel은 여러 Agent와 일반 Python 단계를 직렬·병렬·fan-out으로 조립한다.

## 핵심 노드: `PydanticAgentModule`

```python
from pydantic import BaseModel
from pydantic_ai import Agent
from parasel import PydanticAgentModule, Serial


class Answer(BaseModel):
    summary: str
    confidence: float


agent = Agent(
    "openai:gpt-4o-mini",
    output_type=Answer,
    instructions="Return a concise factual answer.",
)

pipeline = Serial([
    PydanticAgentModule(
        agent,
        prompt=lambda context: f"Summarize: {context['document']}",
        out_name="answer",
    ),
])
```

`context["answer"]`에는 문자열이 아니라 검증된 `Answer` Pydantic 모델이 저장된다. 그러므로 다음 단계는 모델 출력을 다시 파싱하지 않고 타입을 바로 사용할 수 있다.

## 의존성, 모델 선택, 실행 메타데이터

Pydantic AI `deps`가 실행별로 달라지면 `deps_factory`를 사용한다. 정적 `deps`와 함께 쓸 수는 없다.

```python
node = PydanticAgentModule(
    agent,
    prompt=lambda context: context["question"],
    out_name="answer",
    deps_factory=lambda context: DatabaseSession(context["tenant_id"]),
    model="openai:gpt-4o-mini",  # Pydantic AI run()에 그대로 전달
    metadata_name="answer_run",
)
```

`metadata_name`을 지정하면 context에 `usage`와 `all_messages()` 결과가 기록된다. 민감한 대화 내용이 있을 수 있으므로 이 키를 HTTP 응답으로 노출할지는 명시적으로 결정해야 한다.

## 모델 앙상블

서로 다른 모델 또는 프롬프트를 `Parallel`로 실행한 뒤, 일반 module에서 결과를 선택·병합한다.

```python
drafts = Parallel([
    PydanticAgentModule(fast_agent, lambda c: c["question"], "fast_draft"),
    PydanticAgentModule(careful_agent, lambda c: c["question"], "careful_draft"),
])
```

병렬 Agent는 같은 Context를 읽는다. 반드시 서로 다른 `out_name`을 사용한다. 같은 키를 쓰면 결과는 실행 순서에 의존할 수 있다.

## 적용 범위

- `PydanticAgentModule`: Pydantic AI Agent 실행, typed output, deps, model override
- `ModuleAdapter`: 검색·DB·변환처럼 LLM이 아닌 단계
- `ByArgs` / `ByKeys`: 다수의 Agent 호출이나 문서별 처리
- `TaskRegistry` + `create_app`: 버전별 pipeline을 FastAPI로 노출

장기 실행 재개나 human-in-the-loop가 필요할 때만 LangGraph·Temporal 같은 런타임을 별도로 검토한다.
