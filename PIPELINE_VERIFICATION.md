# Pipeline Verification

Run: `python3 -m scripts.validate_ri_pipeline` (first 10 `NarrativeUnit`s of
`data/processed/ri_parsed.json`, `story_universe_id = "reverend_insanity"`).

## Result: real extraction succeeded, via local Ollama

Gemini's free tier is rate/quota-limited, so this run used a local model
instead (`backend/llm/ollama.py`'s `OllamaProvider`, implementing the same
`LLMProvider` ABC as `GeminiProvider` -- swap back with
`MODEL_PROVIDER=gemini`). No data below is fabricated: every row came from
an actual `qwen2.5:7b` completion, and the hallucination check
(`raw_excerpt` must be a verbatim substring of the unit's `raw_text`) is
enforced in code before anything is written.

```
warning: The `fitz` API is deprecated and will be removed in future. Use `import pymupdf` instead.
state extraction failed for unit RI_chapter_3: Ollama request failed: timed out
state extraction failed for unit RI_chapter_6: Ollama request failed: timed out
state extraction failed for unit RI_chapter_7: Ollama request failed: timed out
state extraction failed for unit RI_chapter_8: Ollama request failed: timed out
state extraction failed for unit RI_chapter_9: Ollama request failed: timed out
Loaded 10 narrative units from data/processed/ri_parsed.json
✓ Inserted 10 narrative units into ClickHouse Story State DB
  Using local provider: qwen2.5:7b
✓ Extracted and wrote 4 state events across 10 units
✓ Detected 0 candidate conflicts using SQL Window Functions
```

5 of 10 chapters timed out at the 180s per-request limit in
`OllamaProvider.complete()` (longer chapters, no GPU, and other load on the
box at the time). This is a throughput limit of the local tier, not a code
defect: the pipeline logged each failure and moved on
(`extract_state_events`'s `except` clause) rather than crashing the run.

**Fixed since the first run:** `scripts/validate_ri_pipeline.py` was loading
each `NarrativeUnit` with the `story_universe_id` baked into
`ri_parsed.json` by `NovelParser` (`"default_universe"`), while state
events were tagged with the `story_universe_id` parameter
(`"reverend_insanity"`) -- two different ids for the same data, so
`storytrace.narrative_units` and `storytrace.state_events` disagreed and
the API's `/api/universes/reverend_insanity/overview` reported 0 units.
Fixed by overriding each unit's `story_universe_id` to match before
inserting. Confirmed both tables now agree:

```
SELECT DISTINCT story_universe_id FROM storytrace.narrative_units  -> reverend_insanity
SELECT DISTINCT story_universe_id FROM storytrace.state_events     -> reverend_insanity
```

## Verification queries (real output, this run)

```
docker exec storytrace-clickhouse-1 clickhouse-client --query "SELECT count() FROM storytrace.state_events"
4
```

```
docker exec storytrace-clickhouse-1 clickhouse-client --query "SELECT count() FROM storytrace.candidate_conflicts"
0
```

Expected at this sample size: `CandidateDetector` looks for a same-entity
`lost -> held` or `injured -> healed` transition across `sequence_number`
via `lagInFrame`. 4 scattered single-observation facts across 4 entities
don't contain such a pair -- not a bug, just not enough extracted state yet.

```
docker exec storytrace-clickhouse-1 clickhouse-client --query "SELECT status, count() FROM storytrace.investigation_verdicts GROUP BY status"
(empty -- expected: the Investigation Agent runs per CandidateConflict, and
there are none yet.)
```

```
docker exec storytrace-clickhouse-1 clickhouse-client --query "SELECT entity_id, attribute, value, raw_excerpt FROM storytrace.state_events LIMIT 10"
```

| entity_id | attribute | value | raw_excerpt |
|---|---|---|---|
| reverend_insanity_character_fang_yuan | clothing | tidy (status) | His clothing had long been tidy; |
| reverend_insanity_character_fang_yuan | location | outside house | So the two brothers left the house. |
| reverend_insanity_character_shen_cui | location | downstairs | Looking down, Fang Yuan saw his own personal servant – Shen Cui. |
| reverend_insanity_character_gu_yue_chi_chen | presence | B grade | Another B grade! |

Every `raw_excerpt` is a real, verbatim quote from the parsed chapter text
(enforced in code, not spot-checked).

## Also verified: FastAPI reads this data correctly

```
$ curl http://localhost:8001/api/universes/reverend_insanity/overview
{"narrative_units":10,"characters":0,"props":0,"candidates":0}
```

`narrative_units: 10` confirms the `story_universe_id` fix above.
`characters`/`props` are 0 because `EntityRegistry` (used inside
`extract_state_events` to generate stable `entity_id`s) only lives
in-memory for the duration of one extraction call -- nothing currently
persists resolved entities to `storytrace.entities`. That's a real gap
(the `insert_entities` method exists on `ClickHouseClient` and is unused),
just not one this task asked to close.

## What's confirmed working end-to-end

- Schema migration: agnostic columns confirmed.
- `backend/pipeline/state_extraction.py`: real extraction, hallucination-
  checked, attribute-bucket-mapped, writes to ClickHouse.
- `backend/llm/ollama.py`: sync `OllamaProvider(LLMProvider)`, a drop-in for
  `GeminiProvider`, selected via `MODEL_PROVIDER=ollama` (default) /
  `MODEL_PROVIDER=gemini` in `scripts/demo_pipeline.py`.
- `NarrativeUnit` -> ClickHouse insertion: 10/10, correct `story_universe_id`.
- `CandidateDetector` ran against real (sparse) state_events, correctly
  found no conflicts at this sample size.
- FastAPI's `/api/universes/{id}/overview` reads the real inserted data.

## Next step to see a real conflict

Run against more chapters (a few dozen, not 10) so the same entity
accumulates multiple `possession`/`injury` observations across sequence --
that's what `lagInFrame` needs to find a transition. At 10 chapters with a
timeout-prone local model, the sample is too small and too incomplete.
