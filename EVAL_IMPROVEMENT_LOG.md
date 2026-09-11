# Eval Improvement Log — live handoff doc

**Purpose**: this document is kept current so any agent (Claude, Antigravity,
or a human) can pick up this work cold if the session doing it gets cut off.
Update it after every meaningful change — don't let it go stale.

## Current status (as of 2026-09-11, eval run 5)

**Overall F1: 0.655** ("ACCEPTABLE"), up from a 0.347 baseline this morning.

| Phase | Precision | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Extraction | 0.276 | 0.800 | 0.410 | 16 | 42 | 4 |
| Detection | 1.000 | 0.800 | 0.889 | 4 | 0 | 1 |
| Investigation | 0.750 | 0.600 | 0.667 | 3 | 1 | 2 |

**Target set by user**: F1 > 0.9, without overfitting to `controlled_test.txt`
specifically — validate on a second small document
(`data/test_documents/controlled_test_v2.txt`, already in-repo, small/cheap)
once the primary target is hit. **Do not run against Reverend Insanity or
Oppenheimer test data for iteration — user explicitly flagged those as too
expensive to use for this kind of repeated testing.**

Run the eval with:
```bash
source venv/bin/activate && set -a && source .env && set +a
python3 -m scripts.eval
```
Takes 5-15 min (real LLM calls against Vertex AI + a fresh `mcp-clickhouse`
subprocess per investigation). Report lands in `EVAL_REPORT.md` at repo root.
**Always block on the run and read the real output — don't guess at results.**

## What's been fixed today (chronological, all committed to `main` except where noted)

1. **Extraction canonicalization** (`backend/pipeline/state_extraction.py`):
   injury-body-part laterality stripping (`right_forearm`→`forearm`),
   possession sub-attribute alias table (`case file`→`file`), location
   leading-article stripping (`"the precinct"`→`"precinct"`), and a new
   `location.city` attribute (see #4).
2. **Golden dataset expansion** (`data/eval/golden_dataset.py`): added
   previously-uncovered-but-correct facts that were being scored as false
   positives purely because the fixture never listed them.
3. **Reverted a failed experiment**: a detector rule flagging ANY scene-level
   `location` change was tried, then reverted after it flagged nearly every
   ordinary scene transition (16/18 candidates were FPs, tanked Detection
   precision 1.0→0.111). Lesson: "is this narratively explained" is not a
   structural SQL-detectable property.
4. **`location.city` attribute + detector rule** (the fix that replaced #3):
   extraction now emits a separate `location.city` fact ONLY when a real
   city/region is explicitly named (rare by construction — once or twice per
   story, not every scene), so a bare value-change rule on it is safe. This
   is what caught the Chicago→New York conflict.
5. **`possession: lost → acquired` detector rule** (new, alongside the
   existing `lost → held`): catches a `lost→acquired→held` chain (the badge
   conflict) at its first suspicious transition.
6. **ClickHouse Cloud reliability bug** (`scripts/eval/run_eval.py`,
   `_wait_for_count`): `insert_narrative_units` wasn't reliably visible to an
   immediate subsequent read on Cloud's `SharedMergeTree` engine (a
   delete-then-insert-then-read race), silently corrupting Detection/
   Investigation scoring (every unit_id→sequence_number lookup resolved to
   -1) without raising any error. Fixed by polling until the expected row
   count is actually visible before proceeding. **This was pure measurement
   noise, not a real pipeline regression** — cost us one wasted eval run
   (run 3, reported F1 0.122) before being diagnosed.
7. **Investigation Agent bridge-guidance prompt** (`backend/agent/investigator.py`,
   `_run_loop`): iterated 3 times today —
   - v1: generic "what counts as a valid bridge" criteria per conflict type.
   - v2: tightened injury-bridge wording (treatment event alone is
     sufficient, don't also require an explicit time-skip phrase) +
     `max_calls` 6→8 (longer prompt needs more room).
   - v3 (current): explicitly told the agent to check `get_unit_text` on the
     prior/current units AND call `find_attribute_changes`/
     `get_entity_timeline` for intervening steps before concluding "no
     bridge" (a real miss: the badge's actual return event was in an
     intervening unit the agent's given excerpts didn't show), and
     clarified the treatment-event bridge counts even when it's described in
     the SAME unit as the "prior/injured" evidence (not just a separate
     later event).
   - Result of v3: badge case now resolves correctly (was the biggest
     Investigation FP). Injury case still wrong — see Known Remaining Issues.

## Known remaining issues (not yet fixed)

1. **Investigation FP**: `COLE/injury.forearm` (units 12→14, the paramedic
   treatment case) — expected `resolved`, currently getting `uncertain`
   (an improvement over earlier runs' `verified`, but still not matching).
   Worth one more look at the actual verdict explanation
   (`investigation_verdicts.explanation` in ClickHouse, joined against
   `candidate_conflicts` — see query pattern used throughout this session in
   the conversation transcript) before touching the prompt again.
2. **Detection/Investigation FN (expected, structural)**:
   `COLE/injury.forearm` (units 6→11, "climbs a ladder with both hands
   shortly after a forearm slash") — expected `uncertain`. This needs
   comparing a PERSISTENT state (still injured) against a narrated ACTION
   (climbing with both hands), which is a fundamentally different signal
   shape than any value-diff SQL rule can express. Would need a new
   extraction vocabulary (e.g. `action.uses_both_hands`) plus a cross-
   attribute join in the detector — real scope increase, not a tweak. Not
   attempted yet.
3. **Extraction precision is still low (0.276)** despite recall being decent
   (0.800) — 42 FPs this run. Some of this is genuinely-correct extractions
   the golden dataset still doesn't cover (same root cause as the original
   0.109 precision problem, partially but not fully addressed by golden
   dataset expansion #2 above) — e.g. `COLE/location = "window of the
   Chicago precinct"` is a real fact, just phrased slightly differently than
   whatever golden entry might exist for it. This is an eval-fixture
   coverage gap more than a pipeline bug, but hasn't been rigorously
   separated from real extraction noise (e.g. `CASE FILE / possession =
   acquired` — entity_name should be COLE, not "CASE FILE", so the
   extractor is sometimes making the prop itself the entity instead of the
   character holding it -- that IS a real bug worth a prompt fix).
4. **LLM non-determinism makes single eval runs unreliable** for judging any
   one change — established empirically today (same code, wildly different
   F1 across runs before the ClickHouse bug was found; even after fixing
   that, extraction's exact per-unit output varies run to run, e.g. the
   badge "acquired" fact landed on a different unit run to run). Treat any
   single run as a noisy sample, not ground truth — the ecc plugin's
   `agent-eval` skill explicitly recommends 3+ trials per change to judge
   consistency; we've mostly only run 1 per change today due to ~5-15min/run
   cost. Consider running the current state 2-3 more times before declaring
   the F1 number "the" number.

## Files touched today

- `backend/pipeline/state_extraction.py` — canonicalization + `location.city`
- `backend/candidate_detection/detector.py` — `lost→acquired`, `location.city` rule (and the reverted-then-removed broad location rule, documented inline)
- `backend/agent/investigator.py` — bridge guidance (3 iterations), `max_calls` 6→8
- `backend/agent/tools.py` — (from earlier in session, unrelated to F1 work) observation-shortening, not touched today
- `data/eval/golden_dataset.py` — expanded facts, `location.city` attribute updates, docstring rewrites tracking detector capability
- `scripts/eval/run_eval.py` — `_wait_for_count` reliability fix
- `EVAL_REPORT.md` — regenerated by every eval run, always reflects the LAST run only (not committed per-run; check git history if you need an old snapshot, or just re-run)

## Next steps (in priority order)

1. Look at the current injury/`resolved`-vs-`uncertain` mismatch's actual
   verdict explanation before changing the prompt again — don't guess.
2. Consider the `entity_name` mis-attribution bug (props being extracted as
   their own entity instead of the character possessing them) — likely a
   real, fixable extraction prompt gap contributing to precision.
3. Run the eval 2-3 more times at current state to establish a real
   (not single-sample) F1 baseline before making further changes, per the
   ecc `agent-eval` skill's variance-check guidance.
4. Once F1 is high and stable on `controlled_test.txt`, run once against
   `data/test_documents/controlled_test_v2.txt` (already golden-dataset-free
   — would need a small golden fixture written for it, or just a qualitative
   read of its output) to check for overfitting to the primary test
   document's specific wording. **Do not use Reverend Insanity or
   Oppenheimer for this** — explicitly too expensive per user direction.
