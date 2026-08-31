from typing import Protocol, Dict, Any
import os

class LLMProvider(Protocol):
    async def complete(self, prompt: str, system: str = "") -> str:
        ...

    async def complete_structured(self, prompt: str, schema: dict, system: str = "") -> dict:
        ...

def get_llm_provider() -> LLMProvider:
    provider = os.getenv("MODEL_PROVIDER", "ollama")
    if provider == "gemini":
        from .gemini import GeminiProvider
        return GeminiProvider()
    else:
        from .ollama import OllamaProvider
        return OllamaProvider()
