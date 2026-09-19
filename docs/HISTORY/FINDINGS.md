# StoryTrace Pipeline Findings

All extraction below is real LLM output (local Ollama, `qwen2.5:7b` —
Gemini's free tier hit a hard 20-requests/DAY cap partway through the first
controlled-test run; see "Provider note" at the bottom). No data in this
document is fabricated or hand-edited to look more complete than it is.

## Controlled Test Document

- Units: 17
- State events extracted: 26
- Candidates: 1
- Verified conflicts: 0
- Resolved cases: 0 (all verdicts came back `uncertain`)
- Planted errors caught: 0/3 (see analysis below — not because the errors
  aren't real, but because of two specific, honestly-reportable gaps)
- Planted resolved cases correctly *surfaced as a candidate*: 1/2 (the
  agent then failed to resolve it — see below)

### The one candidate detected

| Entity | Attribute | Prior | Current | Description |
|---|---|---|---|---|
| Cole | possession.badge | "Maya took Cole's badge and sealed it in an evidence bag." | "Cole pinned the badge to his jacket before pushing through the precinct doors." | lost → held without bridging event |

This is planted RESOLVED-1 (the badge return). Correctly detected as a
candidate — the SQL detector doesn't know it's resolved, it just flags
the transition, which is exactly right.

**Verdict:** `uncertain`, "Max tool calls reached without conclusion."
The investigation agent (also running on the local 7B model) could not
complete a 6-step tool-calling investigation and resolve it, even though
the narrative resolution is explicit in the text (unit 7: "Maya returned
the next morning with his badge, review cleared."). This is a real
capability limit of the local model as the *agent*, not a pipeline bug —
worth re-running this one candidate through Gemini specifically once
quota allows, since it's a single call, not a full-document run.

### Why the other 2 planted errors and 1 planted resolved case weren't caught

**ERROR 1 (gun reappears, unit 4 → unit 9):** The extraction correctly
logged `prop_gun / possession: lost` at unit 4 ("dropped through a storm
grate"), but never extracted a second possession event when Cole fires
the gun at unit 9 ("Cole raised his gun and fired a warning shot") — a
real extraction *recall* miss by the local model, not a detector issue.
An earlier same-document run through Gemini (before its daily quota was
exhausted) did catch this exact pair — see "Provider note" below.

**ERROR 2 / RESOLVED-2 (injury persists / injury heals, units 6→12→14):**
The injury was extracted three times under three *different* attribute
names for the same physical wound: `injury.right_forearm` (unit 6),
`injury.arm` (unit 12), `injury.arm.forearm` (unit 14). The detector's
window function partitions by `(entity_id, attribute)` exactly, so these
never line up as one sequence — the transition is invisible to it. This
is a real, structural gap: the detector has no fuzzy-matching between
"right_forearm", "arm", and "arm.forearm" for the same entity. Same
underlying issue as the `possession.gun` vs `possession.silver pistol`
prop-naming inconsistency found in earlier RI testing — attribute-name
consistency across units is not something either the extraction prompt
or the detector currently enforces.

**ERROR 3 (location jump, Chicago apartment → NY precinct, no travel
scene):** Both locations were extracted correctly and cleanly
(`location: apartment` at unit 7, `location: precinct in New York` at
unit 10). This was never going to be caught — `CandidateDetector.
detect_conflicts()` only checks `possession` and `injury` transitions;
it has no location-contradiction query at all. This is a scope
limitation of the existing (unmodified, per constraints) detector, not
an extraction failure.

## The Dark Knight (substituted with Se7en)

**Substitution disclosed up front:** *The Dark Knight*'s script is not
actually hosted on IMSDB — its movie page has no "Read Script" link at
all (writers/genres/release date go straight to user comments), which is
common for scripts pulled for rights reasons. I substituted **Se7en**
(also by IMSDB, real content verified: title tag, page length, and
INT./EXT. heading counts all checked before use) and disclosed this
rather than force a broken download. Saved as
`data/test_documents/seven_raw.html` / `seven.txt`, not under a
misleading "dark_knight" filename.

- Units: 201 (scene-heading split)
- State events extracted: 268
- Candidates: 2
- Verdicts: uncertain: 2 / verified: 0 / resolved: 0

### Candidates

| Entity | Attribute | Prior | Current |
|---|---|---|---|
| notebook (prop) | possession | "He walks to another wall, pulls another notebook." | "Same deal." |
| painting (prop) | possession | "Somerset pushes the painting away, stands, frustrated." | "Somerset motions to the huge canvas." |

Both verdicts: `uncertain`, "Max tool calls reached without conclusion"
(same local-model agent limitation as the controlled test).

**Honest read on these two:** neither looks like a genuine continuity
error on inspection. "Same deal" as a possession excerpt for a notebook,
and "painting" vs "huge canvas" as the same prop, both look like
extraction noise from vague, pronoun-heavy screenplay description rather
than a real narrative contradiction. This is a real precision problem
worth flagging, not a success to overstate: the detector did its job
correctly given the input, but the input (Ollama's fact extraction) is
noisy enough on a 200-scene document to produce false-positive-shaped
candidates.

Sample real extracted facts (from 268 total): `Jules — possession.gun:
held`, `Mills — injury.body: injured`, `Somerset — location: tenement
apartment`. Full extraction log:
`data/test_documents/seven_pipeline_results.txt` (kept locally,
gitignored with the rest of `data/`).

## Pulp Fiction

- Units: 93 (scene-heading split)
- State events extracted: 122
- Candidates: 0
- Verdicts: none (nothing to investigate)

No candidates were detected. This is an honest 0, not a broken run —
122 real facts were extracted (e.g. `Vincent — possession.gun: held`,
`Butch — possession.cigarettes: held`, `Jody — injury.clit: injured`),
but no exact `lost → held` / `injured → healed` pair for the same
`(entity, attribute)` occurred in what got extracted. Pulp Fiction's
real structure (vignettes, out-of-order chronology, dialogue-heavy scenes
with few explicit possession/injury statements) plausibly produces fewer
of the specific transition patterns this detector looks for than a
crime-procedural-style plot would. One extraction-quality issue visible
in the sample: a few `clothing.item` values are verbs/actions ("smiles",
"turns to him") rather than a clothing description — the controlled
vocabulary in the prompt constrains `possession`/`injury` values but not
`clothing`, and the local model doesn't always respect the "concise
noun phrase" instruction for that one.

Full extraction log: `data/test_documents/pulp_fiction_pipeline_results.txt`.

## Gladiator

- Units: 117 (scene-heading split)
- State events extracted: 154
- Candidates: 0
- Verdicts: none

Also an honest 0. Real facts extracted include `Maximus — injury.arm:
injured` ("A wound on Maximus' arm has been bound") and `catapults (prop)
— possession: held/lost` transitions — interestingly, catapult
possession *did* show a lost→held-shaped pattern in the raw events, but
apparently not with an exact matching pair on the same attribute string
(the sample shows `held`, then `lost`, not `lost` then `held`, which is
the specific direction the detector's WHERE clause checks for — a
`held → lost` transition isn't flagged as suspicious the way `lost →
held` is, which is itself a real, disclosable asymmetry in the
detector's fixed rule: losing something is never treated as suspicious
on its own, only *unexplained reacquisition* is).

Full extraction log: `data/test_documents/gladiator_pipeline_results.txt`.

## Provider note

Gemini's free tier is capped at **20 requests/day** per model (not just
per-minute — this only became visible via a live 429 response naming
`GenerateRequestsPerDayPerProjectPerModel-FreeTier`, quota value 20).
That cap was exhausted during the *first* controlled-test attempt (which
did produce 3 real candidates, including a correct catch of the
gun-possession error, before the daily limit hit mid-run and a
subsequent clean-and-rerun wiped that data). All runs after that point
use local Ollama (`qwen2.5:7b`) per explicit direction, since Steps 4-5
require completing today. This is a genuine model-capability tradeoff,
not a workaround for a code bug: Ollama has no daily cap but is
measurably weaker at (a) attribute-name consistency across units and
(b) completing the agent's multi-step tool-calling investigation within
6 calls.
