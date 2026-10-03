"""AI Assistant Service — PRD Phase 12 / Cross-cutting Service.

Unified provider-agnostic AI assistant integration powered by NVIDIA NIM
(nvidia/nemotron-3.5-lightning-30b-a3b) with reasoning token extraction,
streaming SSE support, structured Pydantic schema validation, and safe fallbacks.
"""

from __future__ import annotations

import json
import re
from collections.abc import AsyncGenerator
from typing import Any, TypeVar

import structlog
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import settings

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

# Default system persona adapted from Pantheon PRD
DEFAULT_SYSTEM_PROMPT = """You are Pantheon AI, an elite offensive & defensive cybersecurity AI reasoning assistant embedded inside the Pantheon platform.
Your mission is to formulate safe, realistic attack scenarios, analyze security posture, and guide engineers in remediating vulnerabilities.
Adhere strictly to authorized testing standards. When generating JSON or structured output, formulate pure JSON matching the requested schema.
"""


class AIService:
    """NVIDIA NIM / OpenAI-compatible AI Assistant Service."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.base_url = base_url or settings.nvidia_nim_base_url
        self.api_key = api_key or settings.nvidia_nim_api_key
        self.model = model or settings.nvidia_nim_model
        self._client: AsyncOpenAI | None = None

    def get_client(self) -> AsyncOpenAI:
        """Lazy-initialize AsyncOpenAI client."""
        if self._client is None:
            self._client = AsyncOpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=25.0,
            )
        return self._client

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        enable_thinking: bool = True,
        reasoning_budget: int | None = None,
    ) -> AsyncGenerator[dict[str, str], None]:
        """Stream chat completion yielding reasoning and content deltas.

        Yields:
            {"type": "reasoning", "delta": "..."}
            {"type": "content", "delta": "..."}
            {"type": "done", "reasoning": "...", "content": "..."}
        """
        client = self.get_client()

        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        formatted_messages.extend(messages)

        extra_body: dict[str, Any] = {}
        if enable_thinking:
            extra_body["chat_template_kwargs"] = {"enable_thinking": True}
            extra_body["reasoning_budget"] = (
                reasoning_budget or settings.nvidia_nim_reasoning_budget
            )

        full_reasoning: list[str] = []
        full_content: list[str] = []

        try:
            stream = await client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,  # type: ignore[arg-type]
                temperature=temperature
                if temperature is not None
                else settings.nvidia_nim_temperature,
                top_p=settings.nvidia_nim_top_p,
                max_tokens=max_tokens or settings.nvidia_nim_max_tokens,
                extra_body=extra_body if extra_body else None,
                stream=True,
            )

            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta

                # Nemotron delivers reasoning trace in delta.reasoning_content
                reasoning_delta = getattr(delta, "reasoning_content", None)
                if reasoning_delta:
                    full_reasoning.append(reasoning_delta)
                    yield {"type": "reasoning", "delta": reasoning_delta}

                if delta.content is not None:
                    full_content.append(delta.content)
                    yield {"type": "content", "delta": delta.content}

            yield {
                "type": "done",
                "reasoning": "".join(full_reasoning),
                "content": "".join(full_content),
            }

        except Exception as e:
            logger.error("nvidia_nim_stream_error", error=str(e), model=self.model)
            yield {
                "type": "error",
                "message": f"NVIDIA NIM stream error: {e}",
            }

    async def generate_chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        enable_thinking: bool = True,
        reasoning_budget: int | None = None,
    ) -> tuple[str, str]:
        """Execute non-streaming completion and return (content, reasoning_trace)."""
        client = self.get_client()

        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        formatted_messages.extend(messages)

        extra_body: dict[str, Any] = {}
        if enable_thinking:
            extra_body["chat_template_kwargs"] = {"enable_thinking": True}
            extra_body["reasoning_budget"] = (
                reasoning_budget or settings.nvidia_nim_reasoning_budget
            )

        try:
            res = await client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,  # type: ignore[arg-type]
                temperature=temperature
                if temperature is not None
                else settings.nvidia_nim_temperature,
                top_p=settings.nvidia_nim_top_p,
                max_tokens=max_tokens or settings.nvidia_nim_max_tokens,
                extra_body=extra_body if extra_body else None,
                stream=False,
            )
            if not res.choices:
                return "", ""

            msg = res.choices[0].message
            content = msg.content or ""
            reasoning = getattr(msg, "reasoning_content", "") or ""
            return content, reasoning
        except Exception as e:
            logger.error("nvidia_nim_generate_error", error=str(e), model=self.model)
            raise

    async def generate_structured(
        self,
        prompt: str,
        schema_class: type[T],
        system_prompt: str | None = None,
        context: dict[str, Any] | None = None,
        enable_thinking: bool = True,
    ) -> tuple[T, str]:
        """Generate structured data strictly validated against a Pydantic schema.

        Returns (validated_instance, reasoning_trace).
        Never trusts raw LLM output directly.
        """
        schema_json = json.dumps(schema_class.model_json_schema(), indent=2)
        sys_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

        user_content = (
            f"{prompt}\n\n"
            f"You MUST output valid, parseable JSON matching the following JSON Schema:\n"
            f"```json\n{schema_json}\n```\n\n"
        )
        if context:
            user_content += (
                f"Target Application Context:\n```json\n{json.dumps(context, indent=2)}\n```\n\n"
            )

        user_content += "Respond ONLY with the JSON object. Do not include introductory conversational filler outside the JSON."

        messages = [{"role": "user", "content": user_content}]

        content, reasoning = await self.generate_chat(
            messages=messages,
            system_prompt=sys_prompt,
            temperature=0.3,
            enable_thinking=enable_thinking,
        )

        try:
            extracted_dict = self._extract_json_dict(content)
        except Exception:
            if reasoning:
                extracted_dict = self._extract_json_dict(reasoning)
            else:
                raise

        validated = schema_class.model_validate(extracted_dict)
        return validated, reasoning

    @staticmethod
    def _extract_json_dict(text: str) -> dict[str, Any]:
        """Extract and parse a JSON dictionary from model output text."""
        # 1. Try direct parse
        text_clean = text.strip()
        try:
            parsed = json.loads(text_clean)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        # 2. Extract ```json ... ``` code blocks
        json_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if json_block_match:
            candidate = json_block_match.group(1).strip()
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass

        # 3. Search for first { ... } matching span
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            candidate = text[first_brace : last_brace + 1]
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except Exception as e:
                logger.warning("json_substring_parse_failed", error=str(e), snippet=candidate[:200])

        raise ValueError(
            f"Could not parse valid JSON dictionary from model response: {text[:200]}..."
        )


# Global singleton instance
ai_service = AIService()
