"""Step 5 validation: run the pipeline on the first 10 NarrativeUnits of the
Reverend Insanity dataset and report what happened. See PIPELINE_VERIFICATION.md
for the query output this produces.
"""

import asyncio
import json

from backend.clickhouse.client import ClickHouseClient
from backend.ingestion.models import NarrativeUnit
from scripts.demo_pipeline import run_pipeline

STORY_UNIVERSE_ID = "reverend_insanity"


def main():
    with open("data/processed/ri_parsed.json", encoding="utf-8") as f:
        raw_units = json.load(f)[:10]
    # ri_parsed.json carries NovelParser's default "default_universe" on each
    # unit; override it so narrative_units and state_events (which is tagged
    # with STORY_UNIVERSE_ID explicitly) agree on one id.
    units = [NarrativeUnit(**{**u, "story_universe_id": STORY_UNIVERSE_ID}) for u in raw_units]
    print(f"Loaded {len(units)} narrative units from data/processed/ri_parsed.json")

    client = ClickHouseClient()
    asyncio.run(run_pipeline(units, STORY_UNIVERSE_ID, client))


if __name__ == "__main__":
    main()
