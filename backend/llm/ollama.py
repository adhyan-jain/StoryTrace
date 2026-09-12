"""Local Ollama backend, implementing the same LLMProvider ABC as
GeminiProvider (backend/llm/client.py) so pipeline code can swap between
them without changes -- this is the "run it locally for free, switch to
Gemini later" tier.
"""

import os
import time

import httpx
from pydantic import BaseModel
from typing import TypeVar

from .base import LLMParseError, LLMProvider, LLMRequest, LLMResult, LLMUnavailable, parse_into, schema_instructions

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class OllamaProvider(LLMProvider):
    tier = "local"

    def __init__(self, model_name: str | None = None, base_url: str | None = None):
        self._model = model_name or os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
        self.base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        # Default num_ctx (4096) is small enough that qwen2.5:7b's weights +
        # KV cache fit entirely in an 8GB laptop GPU (measured: the model's
        # own default of 32768 forced a 15%/85% CPU/GPU split via `ollama ps`
        # -- CPU offload we don't want for eval-loop latency). num_gpu=-1
        # tells the runner to offload every layer it can to GPU rather than
        # leaving any on CPU by default.
        self._num_ctx = int(os.environ.get("OLLAMA_NUM_CTX", "4096"))

    @property
    def model(self) -> str:
        return self._model

    def available(self) -> bool:
        try:
            httpx.get(f"{self.base_url}/api/tags", timeout=3.0).raise_for_status()
            return True
        except Exception:
            return False

    def complete(self, request: LLMRequest, schema: type[SchemaT]) -> LLMResult[SchemaT]:
        start = time.time()

        sys_prompt = request.system
        if sys_prompt:
            sys_prompt += "\n\n"
        sys_prompt += schema_instructions(schema)

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": request.prompt},
            ],
            "format": "json",
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_ctx": self._num_ctx,
                "num_gpu": -1,  # offload every layer possible to GPU, none to CPU
            },
        }

        try:
            response = httpx.post(f"{self.base_url}/api/chat", json=payload, timeout=180.0)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMUnavailable(f"Ollama request failed: {exc}") from exc

        data = response.json()
        text = data.get("message", {}).get("content", "")
        if not text:
            raise LLMParseError("Empty response from Ollama")

        parsed = parse_into(schema, text)
        latency = int((time.time() - start) * 1000)

        eval_count = data.get("eval_count", 0)
        prompt_eval_count = data.get("prompt_eval_count", 0)

        return LLMResult(
            value=parsed,
            model=self._model,
            tier=self.tier,
            prompt_tokens=prompt_eval_count,
            completion_tokens=eval_count,
            latency_ms=latency,
        )
