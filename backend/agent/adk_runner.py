"""google-adk wrapper for the counterfactual fix-suggestion call.

ADK's Agent/Runner primitives are Gemini-model-native, so this path only
activates for the Gemini-tier provider ("api"). The local Ollama tier has no
ADK runner, so investigator.py keeps using the plain LLMProvider.complete()
path for that case -- this module exists purely so a real ADK agent is
constructed and run at runtime for the Gemini path, per hackathon rules.
"""

from __future__ import annotations

import uuid

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types


async def suggest_fix_via_adk(model_name: str, system_prompt: str, user_prompt: str) -> str:
    agent = Agent(
        name="screenplay_doctor",
        model=model_name,
        instruction=system_prompt,
    )
    app_name = "storytrace_fix_suggestion"
    runner = InMemoryRunner(agent=agent, app_name=app_name)
    user_id = "storytrace"
    session_id = uuid.uuid4().hex
    await runner.session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)

    content = genai_types.Content(role="user", parts=[genai_types.Part(text=user_prompt)])
    final_text = ""
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(part.text or "" for part in event.content.parts)
    return final_text.strip()
