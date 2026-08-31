"""Offline regression tests for the Pydantic AI first-class adapter."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from parasel import (
    Context,
    Executor,
    Parallel,
    PydanticAgentModule,
    Serial,
    TaskRegistry,
    create_app,
)
from parasel.core.node import ExecutionError


class Answer(BaseModel):
    answer: str


def test_agent_module_stores_pydantic_ai_validated_output():
    agent = Agent(TestModel(), output_type=Answer)
    node = PydanticAgentModule(
        agent,
        prompt=lambda context: f"Question: {context['question']}",
        out_name="answer",
        metadata_name="agent_run",
    )

    result = Executor().run(node, initial_data={"question": "What is a type?"})

    assert result.success
    assert isinstance(result.context["answer"], Answer)
    assert result.context["agent_run"]["usage"] is not None


def test_agent_module_builds_prompt_and_deps_from_context():
    received = {}

    class FakeAgent:
        name = "fake"

        def run_sync(self, prompt, **kwargs):
            received.update(prompt=prompt, **kwargs)
            return SimpleNamespace(output="ok")

    node = PydanticAgentModule(
        FakeAgent(),
        prompt=lambda context: context["question"],
        out_name="answer",
        deps_factory=lambda context: {"tenant": context["tenant"]},
        model="test",
    )
    node.run(Context({"question": "hello", "tenant": "acme"}))

    assert received == {
        "prompt": "hello",
        "deps": {"tenant": "acme"},
        "model": "test",
    }


def test_typed_agent_output_is_json_serialized_by_fastapi():
    registry = TaskRegistry()
    registry.register(
        "answer",
        "1.0.0",
        Serial(
            [
                PydanticAgentModule(
                    Agent(TestModel(), output_type=Answer),
                    "What is a type?",
                    "answer",
                )
            ]
        ),
        produces=["answer"],
    )

    response = TestClient(create_app(registry)).post(
        "/run/answer", json={"data": {}, "version": "1.0.0"}
    )

    assert response.status_code == 200
    assert response.json()["data"]["answer"] == {"answer": "a"}


@pytest.mark.asyncio
async def test_agent_module_uses_native_async_agent_run():
    class AsyncAgent:
        async def run(self, prompt, **kwargs):
            assert prompt == "hello"
            return SimpleNamespace(output="async-ok")

    context = Context()
    await PydanticAgentModule(AsyncAgent(), "hello", "answer").run_async(context)
    assert context["answer"] == "async-ok"


def test_parallel_agents_keep_outputs_separate():
    class FakeAgent:
        def __init__(self, output):
            self.output = output

        def run_sync(self, prompt, **kwargs):
            return SimpleNamespace(output=self.output)

    pipeline = Serial(
        [
            Parallel(
                [
                    PydanticAgentModule(FakeAgent("fast"), "question", "fast_draft"),
                    PydanticAgentModule(FakeAgent("careful"), "question", "careful_draft"),
                ]
            )
        ]
    )
    result = Executor().run(pipeline)
    assert result.success
    assert result.context.to_dict() == {"fast_draft": "fast", "careful_draft": "careful"}


def test_agent_module_rejects_ambiguous_dependencies():
    with pytest.raises(ValueError, match="either deps or deps_factory"):
        PydanticAgentModule(
            object(), "prompt", "answer", deps=object(), deps_factory=lambda _: object()
        )


def test_agent_module_wraps_agent_failures_with_node_name():
    class BrokenAgent:
        def run_sync(self, prompt, **kwargs):
            raise RuntimeError("unavailable")

    with pytest.raises(ExecutionError, match="unavailable"):
        PydanticAgentModule(BrokenAgent(), "prompt", "answer", name="draft").run(Context())
