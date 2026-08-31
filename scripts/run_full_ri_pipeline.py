"""Pipeline run over the parsed Reverend Insanity NarrativeUnits.

MODEL_PROVIDER defaults to "ollama" (see scripts/demo_pipeline._default_provider)
so this is free to run repeatedly during testing; set MODEL_PROVIDER=gemini for
the real/production pass later.

Usage: python3 -m scripts.run_full_ri_pipeline [count]
  count: how many units to process, in sequence order (default: all 501).
  Local Ollama inference runs ~60-90s/chapter successful, up to a 180s
  timeout on failure -- the full set takes on the order of half a day.
"""

import asyncio
import json
import sys

from backend.clickhouse.client import ClickHouseClient
from backend.ingestion.models import NarrativeUnit
from scripts.demo_pipeline import run_pipeline

STORY_UNIVERSE_ID = "reverend_insanity"


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    with open("data/processed/ri_parsed.json", encoding="utf-8") as f:
        raw_units = json.load(f)
    if limit is not None:
        raw_units = raw_units[:limit]
    units = [NarrativeUnit(**{**u, "story_universe_id": STORY_UNIVERSE_ID}) for u in raw_units]
    print(f"Loaded {len(units)} narrative units from data/processed/ri_parsed.json")

    client = ClickHouseClient()
    client.client.command("TRUNCATE TABLE storytrace.narrative_units")
    client.client.command("TRUNCATE TABLE storytrace.state_events")
    client.client.command("TRUNCATE TABLE storytrace.candidate_conflicts")

    asyncio.run(run_pipeline(units, STORY_UNIVERSE_ID, client))


if __name__ == "__main__":
    main()
