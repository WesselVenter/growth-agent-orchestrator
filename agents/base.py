"""Shared Agent base class used by every agent in the orchestrator."""

from __future__ import annotations

import json
import os
import time
from typing import Any, TypeVar

import anthropic
from pydantic import BaseModel, ValidationError

from orchestration.trace import AgentCallRecord, ToolCallRecord, Trace, now_iso

ModelT = TypeVar("ModelT", bound=BaseModel)

DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
DEFAULT_MAX_TOKENS = 4096

# Anthropic's server-side web search tool.
WEB_SEARCH_TOOL: dict[str, Any] = {
    "type": "web_search_20250305",
    "name": "web_search",
}


class Agent:
    """A single-purpose agent: a name, a system prompt, and a call() method.

    Every call() is logged to the shared Trace: timestamp, agent name,
    input, output, tool calls made, and duration.
    """

    def __init__(
        self,
        name: str,
        system_prompt: str,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        use_web_search: bool = False,
        client: anthropic.Anthropic | None = None,
    ) -> None:
        self.name = name
        self.system_prompt = system_prompt
        self.model = model
        self.max_tokens = max_tokens
        self.use_web_search = use_web_search
        self.client = client or anthropic.Anthropic()

    def call(self, user_input: str, trace: Trace | None = None) -> str:
        """Send user_input to the model under this agent's system prompt.

        Returns the final text output. If a Trace is provided, logs the
        call (including any tool calls made along the way).
        """
        if trace is not None:
            trace.start_call(self.name, user_input)

        started_at = now_iso()
        start = time.monotonic()

        tools = [WEB_SEARCH_TOOL] if self.use_web_search else []
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": self.system_prompt,
            "messages": [{"role": "user", "content": user_input}],
        }
        if tools:
            kwargs["tools"] = tools

        response = self.client.messages.create(**kwargs)

        output_text_parts: list[str] = []
        tool_calls: list[ToolCallRecord] = []
        for block in response.content:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                output_text_parts.append(block.text)
            elif block_type in ("server_tool_use", "tool_use"):
                tool_calls.append(
                    ToolCallRecord(name=block.name, input=block.input)
                )

        output_text = "\n".join(output_text_parts).strip()
        duration = time.monotonic() - start
        ended_at = now_iso()

        if trace is not None:
            trace.log_call(
                AgentCallRecord(
                    agent_name=self.name,
                    started_at=started_at,
                    ended_at=ended_at,
                    duration_seconds=duration,
                    input=user_input,
                    output=output_text,
                    tool_calls=tool_calls,
                )
            )

        return output_text

    def call_structured(
        self,
        user_input: str,
        output_model: type[ModelT],
        trace: Trace | None = None,
        tool_name: str = "output",
        _retries_left: int = 1,
    ) -> ModelT:
        """Send user_input and force the model to respond via a tool call
        matching output_model's schema. Returns a validated instance of
        output_model. Logs to trace like call().

        The model occasionally violates constraints the JSON schema alone
        doesn't strictly enforce (e.g. array min_length) — if the response
        fails Pydantic validation, retries once with the validation error
        appended, asking the model to correct it. Each attempt (including
        the retry) is logged to trace individually.

        Note: does not mix with use_web_search — this forces a single
        specific tool, so it's for agents doing pure structuring/analysis.
        """
        if trace is not None:
            trace.start_call(self.name, user_input)

        started_at = now_iso()
        start = time.monotonic()

        tool = {
            "name": tool_name,
            "description": f"Return the result as structured {output_model.__name__} data.",
            "input_schema": output_model.model_json_schema(),
        }

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_input}],
            tools=[tool],
            tool_choice={"type": "tool", "name": tool_name},
        )

        tool_calls: list[ToolCallRecord] = []
        output_data: dict[str, Any] | None = None
        for block in response.content:
            block_type = getattr(block, "type", None)
            if block_type == "tool_use":
                tool_calls.append(ToolCallRecord(name=block.name, input=block.input))
                if block.name == tool_name:
                    output_data = block.input

        duration = time.monotonic() - start
        ended_at = now_iso()

        if output_data is None:
            raise ValueError(
                f"{self.name}: model did not return structured output via '{tool_name}' tool"
            )

        try:
            result = output_model.model_validate(output_data)
        except ValidationError as exc:
            if trace is not None:
                trace.log_call(
                    AgentCallRecord(
                        agent_name=self.name,
                        started_at=started_at,
                        ended_at=ended_at,
                        duration_seconds=duration,
                        input=user_input,
                        output=f"INVALID: {json.dumps(output_data, ensure_ascii=False)} ({exc})",
                        tool_calls=tool_calls,
                    )
                )
            if _retries_left <= 0:
                raise
            corrective_input = (
                f"{user_input}\n\n"
                f"Your previous response did not satisfy the required schema:\n{exc}\n"
                "Correct this and respond again via the same tool, strictly satisfying "
                "every constraint (including array length limits)."
            )
            return self.call_structured(
                corrective_input, output_model, trace=trace, tool_name=tool_name,
                _retries_left=_retries_left - 1,
            )

        if trace is not None:
            trace.log_call(
                AgentCallRecord(
                    agent_name=self.name,
                    started_at=started_at,
                    ended_at=ended_at,
                    duration_seconds=duration,
                    input=user_input,
                    output=json.dumps(output_data, ensure_ascii=False),
                    tool_calls=tool_calls,
                )
            )

        return result
