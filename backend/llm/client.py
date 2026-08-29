import os
import json
from google import genai
from pydantic import BaseModel
from typing import TypeVar, Any
import time

from .base import LLMProvider, LLMRequest, LLMResult, parse_into, schema_instructions

SchemaT = TypeVar("SchemaT", bound=BaseModel)

class GeminiProvider(LLMProvider):
    tier = "api"
    
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self._model = model_name
        # Initialize the client. It will automatically pick up GEMINI_API_KEY from env.
        self.client = genai.Client()

    @property
    def model(self) -> str:
        return self._model

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

        response = self.client.models.generate_content(
            model=self._model,
            contents=request.prompt,
            config=config
        )
        
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
