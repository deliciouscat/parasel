"""First-class Pydantic AI agent nodes for Parasel pipelines.

Parasel owns orchestration (serial/parallel composition, fan-out and deployment)
while Pydantic AI owns model calls, tool execution, output validation and usage.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from parasel.core.context import Context
from parasel.core.node import ExecutionError, Node

PromptFactory = Callable[[Context], Any]
DepsFactory = Callable[[Context], Any]


class PydanticAgentModule(Node):
    """Run a Pydantic AI ``Agent`` as a typed Parasel node.

    The wrapped agent validates its own ``output_type`` before this node writes
    ``result.output`` to the context. A prompt or dependency factory makes the
    inputs explicit and keeps pipeline functions free of model-provider code.

    Args:
        agent: A configured :class:`pydantic_ai.Agent` instance. The concrete
            type is intentionally duck-typed so applications can supply a test
            double without importing Pydantic AI in their test modules.
        prompt: A static prompt, or a callable receiving the current Context.
        out_name: Context key that receives the validated ``result.output``.
        deps: Static Pydantic AI dependencies, if the agent uses them.
        deps_factory: Builds per-run dependencies from the Context. It is
            mutually exclusive with ``deps``.
        run_kwargs: Extra keyword arguments forwarded to ``agent.run`` and
            ``agent.run_sync`` (for example ``model`` or ``model_settings``).
        metadata_name: Optional Context key for a small execution record with
            model usage and all model messages.
    """

    def __init__(
        self,
        agent: Any,
        prompt: Any | PromptFactory,
        out_name: str,
        *,
        name: str | None = None,
        deps: Any = None,
        deps_factory: DepsFactory | None = None,
        metadata_name: str | None = None,
        **run_kwargs: Any,
    ):
        if deps is not None and deps_factory is not None:
            raise ValueError("Specify either deps or deps_factory, not both")
        if not out_name:
            raise ValueError("out_name is required for a PydanticAgentModule")

        node_kwargs = {
            key: run_kwargs.pop(key)
            for key in ("timeout", "retries", "metadata")
            if key in run_kwargs
        }
        agent_name = getattr(agent, "name", None)
        super().__init__(name=name or agent_name or "PydanticAgent", **node_kwargs)
        self.agent = agent
        self.prompt = prompt
        self.out_name = out_name
        self.deps = deps
        self.deps_factory = deps_factory
        self.metadata_name = metadata_name
        self.run_kwargs = run_kwargs

    def _prompt_for(self, context: Context) -> Any:
        return self.prompt(context) if callable(self.prompt) else self.prompt

    def _deps_for(self, context: Context) -> Any:
        return self.deps_factory(context) if self.deps_factory else self.deps

    def _kwargs_for(self, context: Context) -> dict[str, Any]:
        kwargs = dict(self.run_kwargs)
        deps = self._deps_for(context)
        if deps is not None:
            kwargs["deps"] = deps
        return kwargs

    def _store(self, context: Context, result: Any) -> None:
        if not hasattr(result, "output"):
            raise ExecutionError(
                f"Pydantic AI agent '{self.name}' returned no output",
                node_name=self.name,
            )
        context[self.out_name] = result.output
        if self.metadata_name:
            usage = getattr(result, "usage", None)
            messages = getattr(result, "all_messages", None)
            context[self.metadata_name] = {
                "usage": usage,
                "messages": messages() if callable(messages) else messages,
            }

    def run(self, context: Context) -> None:
        """Run an agent from synchronous Parasel code."""
        try:
            result = self.agent.run_sync(self._prompt_for(context), **self._kwargs_for(context))
            self._store(context, result)
        except ExecutionError:
            raise
        except Exception as exc:
            raise ExecutionError(
                f"Pydantic AI agent '{self.name}' failed: {exc}",
                node_name=self.name,
                cause=exc,
            ) from exc

    async def run_async(self, context: Context) -> None:
        """Run an agent through Pydantic AI's native async interface."""
        try:
            result = await self.agent.run(self._prompt_for(context), **self._kwargs_for(context))
            self._store(context, result)
        except ExecutionError:
            raise
        except Exception as exc:
            raise ExecutionError(
                f"Pydantic AI agent '{self.name}' failed: {exc}",
                node_name=self.name,
                cause=exc,
            ) from exc
