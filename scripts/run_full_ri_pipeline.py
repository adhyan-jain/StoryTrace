"""Full pipeline run over every parsed Reverend Insanity NarrativeUnit.

MODEL_PROVIDER defaults to "ollama" (see scripts/demo_pipeline._default_provider)
so this is free to run repeatedly during testing; set MODEL_PROVIDER=gemini for
the real/production pass later.
"""

import asyncio
import json

from backend.clickhouse.client import ClickHouseClient
from backend.ingestion.models import NarrativeUnit
from scripts.demo_pipeline import run_pipeline

STORY_UNIVERSE_ID = "reverend_insanity"


def main():
    with open("data/processed/ri_parsed.json", encoding="utf-8") as f:
        raw_units = json.load(f)
    units = [NarrativeUnit(**{**u, "story_universe_id": STORY_UNIVERSE_ID}) for u in raw_units]
    print(f"Loaded {len(units)} narrative units from data/processed/ri_parsed.json")

    client = ClickHouseClient()
    client.client.command("TRUNCATE TABLE storytrace.narrative_units")
    client.client.command("TRUNCATE TABLE storytrace.state_events")
    client.client.command("TRUNCATE TABLE storytrace.candidate_conflicts")

    asyncio.run(run_pipeline(units, STORY_UNIVERSE_ID, client))


if __name__ == "__main__":
    main()
