"""Vertex AI backend, implementing the same LLMProvider ABC as GeminiProvider
(backend/llm/client.py) and OllamaProvider (backend/llm/ollama.py) so pipeline
code can swap between them without changes.

Distinct from GeminiProvider: authenticates via Application Default
Credentials against a GCP project/region instead of an API key, and goes
through google-cloud-aiplatform's `vertexai` SDK rather than `google-genai`.
"""

import concurrent.futures
import os
import time

from google.api_core.exceptions import ResourceExhausted
from pydantic import BaseModel
from typing import TypeVar
from vertexai.generative_models import GenerationConfig, GenerativeModel
import vertexai

from .base import LLMParseError, LLMProvider, LLMRequest, LLMResult, LLMUnavailable, parse_into, schema_instructions

SchemaT = TypeVar("SchemaT", bound=BaseModel)

_REQUEST_TIMEOUT_S = 120.0
_MAX_RATE_LIMIT_RETRIES = 3
_RATE_LIMIT_BACKOFF_S = 15.0

# One worker is enough -- this just gives generate_content's blocking gRPC
# call something to time out on. The Vertex AI SDK's generate_content()
# doesn't accept a timeout kwarg directly, and a full-screenplay run
# (data/test_documents/pulp_fiction.txt) was observed to hang indefinitely
# (epoll_wait, no progress) on one call with no request-level timeout set.
_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=4)


class VertexAIProvider(LLMProvider):
    tier = "api"

    def __init__(self, model_name: str | None = None):
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not project:
            raise ValueError("GOOGLE_CLOUD_PROJECT env var required for Vertex AI")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        vertexai.init(project=project, location=location)
        self._model = model_name or os.environ.get("VERTEX_MODEL", "gemini-3.6-flash-lite")

        # backend/agent/adk_runner.py's suggest_fix_via_adk() builds its own
        # google-adk Agent, which goes through google-genai's Client() --
        # that reads GOOGLE_GENAI_USE_VERTEXAI to decide direct Gemini API
        # vs. Vertex AI. Unset, it silently fell through to the direct API
        # (using GEMINI_API_KEY) even under MODEL_PROVIDER=vertexai, and hit
        # a 404 once Google deprecated gemini-2.5-flash for new API-key
        # users there. Setting it here keeps every Gemini client constructed
        # for the rest of this process (this provider and ADK's) on Vertex,
        # authenticated the same way, against the same project/location.
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project)
        os.environ.setdefault("GOOGLE_CLOUD_LOCATION", location)

    @property
    def model(self) -> str:
        return self._model

    def _generate_with_retry(self, generative_model: GenerativeModel, prompt: str, generation_config: GenerationConfig):
        last_exc = None
        for attempt in range(_MAX_RATE_LIMIT_RETRIES + 1):
            future = _EXECUTOR.submit(generative_model.generate_content, prompt, generation_config=generation_config)
            try:
                return future.result(timeout=_REQUEST_TIMEOUT_S)
            except concurrent.futures.TimeoutError as exc:
                future.cancel()
                raise LLMUnavailable(f"Vertex AI request timed out after {_REQUEST_TIMEOUT_S}s") from exc
            except ResourceExhausted as exc:
                if attempt == _MAX_RATE_LIMIT_RETRIES:
                    raise LLMUnavailable(f"Vertex AI request failed: {exc}") from exc
                last_exc = exc
                time.sleep(_RATE_LIMIT_BACKOFF_S)
            except Exception as exc:
                raise LLMUnavailable(f"Vertex AI request failed: {exc}") from exc
        raise LLMUnavailable(f"Vertex AI request failed: {last_exc}")

    def complete(self, request: LLMRequest, schema: type[SchemaT]) -> LLMResult[SchemaT]:
        start = time.time()

        sys_prompt = request.system
        if sys_prompt:
            sys_prompt += "\n\n"
        sys_prompt += schema_instructions(schema)

        generative_model = GenerativeModel(model_name=self._model, system_instruction=sys_prompt)
        generation_config = GenerationConfig(
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
            response_mime_type="application/json",
        )

        response = self._generate_with_retry(generative_model, request.prompt, generation_config)

        text = response.text
        if not text:
            raise LLMParseError("Empty response from Vertex AI")

        parsed = parse_into(schema, text)
        latency = int((time.time() - start) * 1000)

        usage = response.usage_metadata
        prompt_tokens = usage.prompt_token_count if usage else 0
        comp_tokens = usage.candidates_token_count if usage else 0

        return LLMResult(
            value=parsed,
            model=self._model,
            tier=self.tier,
            prompt_tokens=prompt_tokens,
            completion_tokens=comp_tokens,
            latency_ms=latency,
        )
