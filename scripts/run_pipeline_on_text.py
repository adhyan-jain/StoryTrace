"""Run the full StoryTrace pipeline on a plain-text document, split into
NarrativeUnits by paragraph (double-newline) breaks.

Usage: python3 -m scripts.run_pipeline_on_text <path.txt>
"""

import asyncio
import os
import sys

from backend.agent.investigator import InvestigationAgent
from backend.candidate_detection.detector import CandidateDetector
from backend.clickhouse.client import ClickHouseClient
from backend.ingestion.models import NarrativeUnit
from backend.llm.client import GeminiProvider
from backend.llm.ollama import OllamaProvider
from backend.pipeline.entity_resolution import EntityRegistry
from backend.pipeline.state_extraction import extract_state_events, write_state_events


def _get_provider():
    """Gemini's free tier caps at 20 requests/DAY (not per-minute) --
    exhausted almost immediately by a multi-unit run plus multi-step
    investigation. MODEL_PROVIDER=ollama (default here) runs local instead,
    no daily cap, at the cost of per-call latency. =gemini switches back."""
    if os.environ.get("MODEL_PROVIDER", "ollama") == "gemini":
        return GeminiProvider()
    return OllamaProvider()

STORY_UNIVERSE_ID = "controlled_test_v1"


def load_units(text_path: str) -> list[NarrativeUnit]:
    with open(text_path, encoding="utf-8") as f:
        text = f.read()

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    units = []
    for i, paragraph in enumerate(paragraphs, start=1):
        units.append(
            NarrativeUnit(
                unit_id=f"{STORY_UNIVERSE_ID}_unit_{i}",
                story_universe_id=STORY_UNIVERSE_ID,
                document_id=STORY_UNIVERSE_ID,
                unit_type="scene",
                sequence_number=i,
                title=f"Scene {i}",
                page_start=1,
                page_end=1,
                raw_text=paragraph,
            )
        )
    return units


def clear_existing(client: ClickHouseClient) -> None:
    # mutations_sync=1 makes the ALTER DELETE block until applied (it's async
    # by default in ClickHouse) so the clear is guaranteed done before the
    # fresh insert that follows.
    settings = {"mutations_sync": "1"}
    for table in ("narrative_units", "state_events", "candidate_conflicts"):
        client.client.command(
            f"ALTER TABLE {table} DELETE WHERE story_universe_id = '{STORY_UNIVERSE_ID}'", settings=settings
        )
    # investigation_verdicts has no story_universe_id column; candidate ids
    # are f"{story_universe_id}_{hex}", so match by prefix instead.
    client.client.command(
        f"ALTER TABLE investigation_verdicts DELETE WHERE candidate_id LIKE '{STORY_UNIVERSE_ID}_%'",
        settings=settings,
    )


async def run(text_path: str) -> None:
    units = load_units(text_path)
    print(f"Units processed: {len(units)}")

    client = ClickHouseClient()
    clear_existing(client)
    client.insert_narrative_units(units)

    llm = _get_provider()
    print(f"  Using {llm.tier} provider: {llm.model}")
    registry = EntityRegistry(STORY_UNIVERSE_ID)
    total_events = 0
    for i, unit in enumerate(units, 1):
        events = await extract_state_events(unit, STORY_UNIVERSE_ID, llm, registry)
        await write_state_events(events, client)
        total_events += len(events)
        print(f"  [{i}/{len(units)}] {unit.unit_id}: {len(events)} events", flush=True)
    client.insert_entities(registry.get_all())
    print(f"State events extracted: {total_events}")

    detector = CandidateDetector(client)
    conflicts = detector.detect_conflicts(STORY_UNIVERSE_ID)
    client.insert_candidate_conflicts(conflicts)
    print(f"Candidates detected: {len(conflicts)}")

    if total_events > 0 and len(conflicts) == 0:
        print("\nNo candidates found. First 20 extracted state events, grouped by attribute+value:")
        rows = client.client.query(
            f"""SELECT attribute, value, entity_id, unit_id, raw_excerpt
                FROM state_events WHERE story_universe_id = '{STORY_UNIVERSE_ID}'
                ORDER BY attribute, value LIMIT 20"""
        ).result_rows
        for r in rows:
            print(f"  {r[0]:<22} {r[1]:<12} {r[2]:<30} {r[3]:<25} {r[4][:60]}")

    agent = InvestigationAgent(llm, STORY_UNIVERSE_ID)
    counts = {"verified": 0, "resolved": 0, "uncertain": 0, "intentional": 0}
    for conflict in conflicts:
        verdict = await agent.investigate_async(conflict)
        client.insert_investigation_verdicts([verdict])
        counts[verdict.status] = counts.get(verdict.status, 0) + 1

    print(
        f"Verdicts - verified: {counts.get('verified', 0)} / resolved: {counts.get('resolved', 0)} "
        f"/ uncertain: {counts.get('uncertain', 0)}"
    )


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 -m scripts.run_pipeline_on_text <path.txt>")
        raise SystemExit(1)
    asyncio.run(run(sys.argv[1]))

    from scripts.compliance_check import main as print_compliance

    print_compliance()


if __name__ == "__main__":
    main()
