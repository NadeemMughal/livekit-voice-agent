"""
Claude (Anthropic) LLM client using the native async SDK.

Uses AsyncAnthropic directly — no langchain overhead, no Pydantic-v1 warnings,
and truly non-blocking so the event loop stays free during API calls.
"""
import anthropic

_VOICE_SYSTEM_PROMPT = (
    "You are a helpful voice assistant. "
    "Keep every reply under 2 sentences — short, clear, and conversational. "
    "No lists, no markdown, no preamble."
)


class ClaudeClient:
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.model = model
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def generate(self, prompt: str) -> str:
        message = await self._client.messages.create(
            model=self.model,
            max_tokens=150,
            system=_VOICE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text


__all__ = ["ClaudeClient"]
