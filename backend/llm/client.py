import os
import json
import re
from google import genai
from google.genai import errors as genai_errors
from pydantic import BaseModel
from typing import TypeVar, Any
import time

from .base import LLMProvider, LLMRequest, LLMResult, parse_into, schema_instructions

SchemaT = TypeVar("SchemaT", bound=BaseModel)

_RETRY_DELAY_RE = re.compile(r"retry in ([\d.]+)s", re.IGNORECASE)
_MAX_RATE_LIMIT_RETRIES = 3

class GeminiProvider(LLMProvider):
    tier = "api"
    
    def __init__(self, model_name: str | None = None):
        self._model = model_name or os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
        # Initialize the client. It will automatically pick up GEMINI_API_KEY from env.
        self.client = genai.Client()

    @property
    def model(self) -> str:
        return self._model

    def _generate_with_retry(self, config: dict, prompt: str):
        """The free tier's per-minute quota (5 req/min at time of writing) is
        routinely exhausted by a multi-step investigation or a multi-unit
        extraction run. Google's own 429 message names how long to wait --
        honor it (capped, bounded retries) rather than let a single quota
        blip surface as a fabricated 'uncertain' verdict downstream."""
        last_exc = None
        for attempt in range(_MAX_RATE_LIMIT_RETRIES + 1):
            try:
                return self.client.models.generate_content(
                    model=self._model,
                    contents=prompt,
                    config=config,
                )
            except genai_errors.ClientError as exc:
                if getattr(exc, "code", None) != 429 or attempt == _MAX_RATE_LIMIT_RETRIES:
                    raise
                last_exc = exc
                match = _RETRY_DELAY_RE.search(str(exc))
                delay = float(match.group(1)) + 1 if match else 15.0
                time.sleep(delay)
        raise last_exc

    def complete(self, request: LLMRequest, schema: type[SchemaT]) -> LLMResult[SchemaT]:
        start = time.time()
        
        # Merge system and schema instructions
        sys_prompt = request.system
        if sys_prompt:
            sys_prompt += "\n\n"
        sys_prompt += schema_instructions(schema)
        
        # Use genai GenerateContentConfig for strict output if possible
        config = {
            "system_instruction": sys_prompt,
            "temperature": request.temperature,
            "max_output_tokens": request.max_tokens,
            # We enforce schema in text anyway, but setting this can help natively if we provide response_schema
            "response_mime_type": "application/json"
        }
        
        # We supply the JSON schema explicitly
        response_schema = schema.model_json_schema()
        # Drop definitions for Gemini compatibility if needed, but usually schema_instructions is enough.

        response = self._generate_with_retry(config, request.prompt)

        text = response.text
        if not text:
            raise RuntimeError("Empty response from Gemini")
            
        latency = int((time.time() - start) * 1000)
        
        parsed = parse_into(schema, text)
        
        # Accounting
        usage = response.usage_metadata
        prompt_tokens = usage.prompt_token_count if usage else 0
        comp_tokens = usage.candidates_token_count if usage else 0
        
        return LLMResult(
            value=parsed,
            model=self._model,
            tier=self.tier,
            prompt_tokens=prompt_tokens,
            completion_tokens=comp_tokens,
            latency_ms=latency
        )
