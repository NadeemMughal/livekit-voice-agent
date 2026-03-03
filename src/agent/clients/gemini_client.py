"""
Gemini (Generative) client wrapper using Langchain.

This provides a wrapper to call Gemini 2.0 Flash Lite via Langchain,
which handles all API complexity automatically.
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage


class GeminiClient:
    def __init__(self, api_key: str, model: str = None):
        self.api_key = api_key
        # Use default model if not specified; override with env if needed
        self.model = model or "gemini-2.0-flash"
        # Strip any preview/date-based suffixes from model name
        if "native-audio-preview" in self.model:
            self.model = "gemini-2.0-flash"
        self.llm = ChatGoogleGenerativeAI(
            model=self.model,
            google_api_key=api_key,
            temperature=0.2,
            max_output_tokens=256,
        )

    async def generate(self, prompt: str, temperature: float = 0.2) -> str:
        """Generate a text response from Gemini using Langchain.
        
        Args:
            prompt: The input text to generate a response for
            temperature: Controls randomness (0.0 = deterministic, 1.0 = random)
        
        Returns:
            The generated response text
        """
        try:
            message = HumanMessage(content=prompt)
            response = self.llm.invoke([message])
            return response.content
        except Exception as e:
            raise RuntimeError(f"Gemini error: {str(e)}")


__all__ = ["GeminiClient"]
