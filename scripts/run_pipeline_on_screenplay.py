"""Run the full StoryTrace pipeline on a plain-text screenplay, split into
NarrativeUnits at scene headings (INT./EXT. lines), falling back to
paragraph splitting if no headings are found.

Usage: python3 -m scripts.run_pipeline_on_screenplay <path.txt>
"""

import asyncio
import os
import re
import sys
from pathlib import Path

from backend.agent.investigator import InvestigationAgent
from backend.candidate_detection.detector import CandidateDetector
from backend.clickhouse.client import ClickHouseClient
from backend.ingestion.models import NarrativeUnit
from backend.llm.client import GeminiProvider
from backend.llm.ollama import OllamaProvider
from backend.pipeline.entity_resolution import EntityRegistry
from backend.pipeline.state_extraction import extract_state_events, write_state_events

HEADING_PATTERN = re.compile(r"^\s*(?:INT\.|EXT\.|INT/EXT\.|I/E\.)\s+.*$")


def _get_provider():
    """Gemini's free tier caps at 20 requests/DAY -- exhausted almost
    immediately on a full screenplay. MODEL_PROVIDER=ollama (default here)
    runs local instead, no daily cap. =gemini switches back."""
    if os.environ.get("MODEL_PROVIDER", "ollama") == "gemini":
        return GeminiProvider()
    return OllamaProvider()


def load_units(text_path: str, story_universe_id: str) -> list[NarrativeUnit]:
    with open(text_path, encoding="utf-8") as f:
        lines = f.readlines()

    heading_lines = [i for i, line in enumerate(lines) if HEADING_PATTERN.match(line)]

    units: list[NarrativeUnit] = []
    if heading_lines:
        boundaries = heading_lines + [len(lines)]
        for seq, (start, end) in enumerate(zip(boundaries, boundaries[1:]), start=1):
            chunk = "".join(lines[start:end]).strip()
            if not chunk:
                continue
            units.append(
                NarrativeUnit(
                    unit_id=f"{story_universe_id}_unit_{seq}",
                    story_universe_id=story_universe_id,
                    document_id=story_universe_id,
                    unit_type="scene",
                    sequence_number=seq,
                    title=lines[start].strip()[:80],
                    page_start=1,
                    page_end=1,
                    raw_text=chunk,
                )
            )
    else:
        text = "".join(lines)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        for seq, paragraph in enumerate(paragraphs, start=1):
            units.append(
                NarrativeUnit(
                    unit_id=f"{story_universe_id}_unit_{seq}",
                    story_universe_id=story_universe_id,
                    document_id=story_universe_id,
                    unit_type="passage",
                    sequence_number=seq,
                    title=f"Passage {seq}",
                    page_start=1,
                    page_end=1,
                    raw_text=paragraph,
                )
            )
    return units


def clear_existing(client: ClickHouseClient, story_universe_id: str) -> None:
    settings = {"mutations_sync": "1"}
    for table in ("narrative_units", "state_events", "candidate_conflicts"):
        client.client.command(
            f"ALTER TABLE {table} DELETE WHERE story_universe_id = '{story_universe_id}'", settings=settings
        )
    client.client.command(
        f"ALTER TABLE investigation_verdicts DELETE WHERE candidate_id LIKE '{story_universe_id}_%'",
        settings=settings,
    )


async def run(text_path: str) -> None:
    story_universe_id = Path(text_path).stem

    units = load_units(text_path, story_universe_id)
    print(f"Units processed: {len(units)} (story_universe_id={story_universe_id})")

    client = ClickHouseClient()
    clear_existing(client, story_universe_id)
    client.insert_narrative_units(units)

    llm = _get_provider()
    print(f"  Using {llm.tier} provider: {llm.model}")
    registry = EntityRegistry(story_universe_id)
    total_events = 0
    for i, unit in enumerate(units, 1):
        events = await extract_state_events(unit, story_universe_id, llm, registry)
        await write_state_events(events, client)
        total_events += len(events)
        print(f"  [{i}/{len(units)}] {unit.unit_id}: {len(events)} events", flush=True)
    client.insert_entities(registry.get_all())
    print(f"State events extracted: {total_events}")

    detector = CandidateDetector(client)
    conflicts = detector.detect_conflicts(story_universe_id)
    client.insert_candidate_conflicts(conflicts)
    print(f"Candidates detected: {len(conflicts)}")

    agent = InvestigationAgent(llm, story_universe_id)
    counts = {"verified": 0, "resolved": 0, "uncertain": 0, "intentional": 0}
    for conflict in conflicts:
        verdict = await agent.investigate_async(conflict)
        client.insert_investigation_verdicts([verdict])
        counts[verdict.status] = counts.get(verdict.status, 0) + 1

    print(
        f"Verdicts - verified: {counts.get('verified', 0)} / resolved: {counts.get('resolved', 0)} "
        f"/ uncertain: {counts.get('uncertain', 0)}"
    )

    print(f"\nSample state_events for {story_universe_id}:")
    rows = client.client.query(
        f"""SELECT entity_id, attribute, value, raw_excerpt FROM state_events
            WHERE story_universe_id = '{story_universe_id}' ORDER BY sequence_number LIMIT 20"""
    ).result_rows
    for r in rows:
        print(f"  {r[0]:<35} {r[1]:<22} {r[2]:<12} {r[3][:60]}")

    print(f"\nVerdict counts for {story_universe_id}:")
    for r in client.client.query(
        f"""SELECT v.status, count() FROM investigation_verdicts v
            WHERE v.candidate_id LIKE '{story_universe_id}_%' GROUP BY v.status"""
    ).result_rows:
        print(f"  {r[0]}: {r[1]}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 -m scripts.run_pipeline_on_screenplay <path.txt>")
        raise SystemExit(1)
    asyncio.run(run(sys.argv[1]))

    from scripts.compliance_check import main as print_compliance

    print_compliance()


if __name__ == "__main__":
    main()
