from google import genai
import json
import os

DEFAULT_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-pro")

class GeminiProvider:
    def __init__(self):
        self.model = DEFAULT_GEMINI_MODEL
        # genai.Client picks up GOOGLE_API_KEY or GOOGLE_APPLICATION_CREDENTIALS automatically
        self.client = genai.Client()

    async def complete(self, prompt: str, system: str = "") -> str:
        # We can use generate_content_async if the client supports it, but currently google-genai
        # supports async on some methods. We'll wrap in a standard sync call for now.
        config = {}
        if system:
            config["system_instruction"] = system

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config
        )
        return response.text

    async def complete_structured(self, prompt: str, schema: dict, system: str = "") -> dict:
        config = {
            "response_mime_type": "application/json",
            "response_schema": schema
        }
        if system:
            config["system_instruction"] = system

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config
        )
        return json.loads(response.text)
