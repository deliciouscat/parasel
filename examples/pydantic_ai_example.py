"""Typed Pydantic AI agents composed by Parasel.

Uses Pydantic AI's TestModel, so this example needs no API key or model provider.
"""

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from parasel import Context, ModuleAdapter, Parallel, PydanticAgentModule, Serial


class Draft(BaseModel):
    answer: str


def render(context: Context, out_name: str):
    draft: Draft = context["draft"]
    context[out_name] = draft.answer.upper()


agent = Agent(
    TestModel(),
    output_type=Draft,
    instructions="Answer the supplied research question concisely.",
    name="research-drafter",
)

pipeline = Serial(
    [
        PydanticAgentModule(
            agent,
            prompt=lambda context: f"Question: {context['question']}",
            out_name="draft",
            metadata_name="draft_run",
        ),
        Parallel(
            [
                ModuleAdapter(render, out_name="rendered"),
            ]
        ),
    ]
).expose(["draft", "rendered", "draft_run"])


if __name__ == "__main__":
    from parasel import Executor

    result = Executor().run(pipeline, initial_data={"question": "What is typed output?"})
    print(result.context.to_dict())
