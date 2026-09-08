# StoryTrace Evaluation Report

**Document:** data/test_documents/controlled_test.txt

**Timestamp:** 2026-09-08T14:11:02.260951+00:00

**Overall F1:** 0.347 :x:

## Phase Metrics

| Phase | Precision | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Extraction | 0.109 | 0.600 | 0.185 :x: | 6 | 49 | 4 |
| Detection | 1.000 | 0.400 | 0.571 :x: | 2 | 0 | 3 |
| Investigation | 0.500 | 0.200 | 0.286 :x: | 1 | 1 | 4 |

## Per-Unit Extraction Breakdown

| Unit | Extracted | Matched | Missed | Missed Attributes |
| --- | --- | --- | --- | --- |
| 1 | 3 | 0 | 1 | location=chicago |
| 2 | 3 | 0 | 3 |  |
| 3 | 4 | 0 | 4 |  |
| 4 | 2 | 1 | 1 |  |
| 5 | 6 | 1 | 5 |  |
| 6 | 3 | 0 | 3 |  |
| 7 | 5 | 2 | 3 |  |
| 8 | 2 | 1 | 1 |  |
| 9 | 2 | 1 | 1 |  |
| 10 | 2 | 0 | 1 | location=new york |
| 11 | 3 | 0 | 3 |  |
| 12 | 3 | 0 | 1 | injury.forearm=injured |
| 13 | 7 | 0 | 7 |  |
| 14 | 4 | 0 | 1 | injury.forearm=healed |
| 15 | 3 | 0 | 3 |  |
| 16 | 1 | 0 | 1 |  |
| 17 | 2 | 0 | 2 |  |

## False Positives

### Extraction

- `COLE` / `possession.case file` = `acquired`
- `COLE` / `location` = `briefing room`
- `COLE` / `location` = `Chicago precinct`
- `COLE` / `possession.file` = `lost`
- `MAYA` / `location` = `doorframe`
- `MAYA` / `clothing.badge` = `badge`
- `COLE` / `location` = `opposite rows`
- `COLE` / `possession.radio` = `held`
- `MAYA` / `location` = `opposite rows`
- `MAYA` / `possession.radio` = `held`
- `GUN` / `possession` = `lost`
- `COLE` / `location` = `the precinct`
- `COLE` / `possession.intake form` = `acquired`
- `MAYA` / `location` = `the precinct`
- `MAYA` / `possession.evidence bag` = `acquired`
- `MAYA` / `possession.badge` = `acquired`
- `COLE` / `injury.right_forearm` = `injured`
- `SUSPECT` / `possession.knife` = `held`
- `SUSPECT` / `possession.knife` = `lost`
- `MAYA` / `possession.badge` = `lost`
- `COLE` / `location` = `Coles apartment`
- `MAYA` / `location` = `Coles apartment`
- `COLE` / `location` = `precinct`
- `THE SUSPECT` / `location` = `chain-link fence`
- `COLE` / `location` = `precinct in New York`
- `COLE` / `possession.badge` = `held`
- `COLE` / `location` = `fire escape behind a shuttered diner`
- `COLE` / `clothing.boots` = `boots`
- `COLE` / `location` = `rooftop`
- `COLE` / `injury.forearm` = `injured`
- `PARAMEDIC` / `possession.field_kit` = `held`
- `PARAMEDIC` / `possession.gauze` = `held`
- `COLE` / `possession.corkboard` = `held`
- `COLE` / `possession.photographs` = `held`
- `COLE` / `location` = `precinct`
- `COLE` / `possession.red string` = `held`
- `MAYA` / `location` = `precinct`
- `MAYA` / `possession.financial records` = `held`
- `MAYA` / `possession.folder` = `held`
- `COLE` / `injury.forearm` = `healed`
- `COLE` / `possession.bandage` = `lost`
- `COLE` / `possession.coffee` = `acquired`
- `BANDAGE` / `possession` = `lost`
- `COLE` / `location` = `interrogation room`
- `SUSPECT` / `location` = `interrogation room`
- `SUSPECT'S LAWYER` / `location` = `interrogation room`
- `COLE` / `possession.final report` = `lost`
- `COLE` / `location` = `city`
- `MAYA` / `location` = `city`

### Investigation

- `COLE` / `injury.forearm`

## False Negatives

### Extraction

- `COLE` / `location` = `chicago` @ unit 1
- `COLE` / `location` = `new york` @ unit 10
- `COLE` / `injury.forearm` = `injured` @ unit 12
- `COLE` / `injury.forearm` = `healed` @ unit 14

### Detection

- `COLE` / `location` (expected: verified) -- Chicago precinct to New York precinct with no travel established
- `COLE` / `injury.forearm` (expected: uncertain) -- Climbs a ladder with both hands shortly after a forearm slash — injury status at this point is ambiguous, not clearly re-established or healed
- `COLE` / `possession.badge` (expected: resolved) -- Badge taken as evidence then explicitly returned next morning — not a real conflict

### Investigation

- `COLE` / `location` (expected: verified) -- Chicago precinct to New York precinct with no travel established
- `COLE` / `injury.forearm` (expected: uncertain) -- Climbs a ladder with both hands shortly after a forearm slash — injury status at this point is ambiguous, not clearly re-established or healed
- `COLE` / `possession.badge` (expected: resolved) -- Badge taken as evidence then explicitly returned next morning — not a real conflict
- `COLE` / `injury.forearm` (expected: resolved) -- Injury explicitly healed via paramedic treatment and narrated recovery — not a real conflict

## Prompt Engineering Impact

Units tested: 5

| Condition | F1 |
| --- | --- |
| No constraints | 0.000 |
| With vocabulary + few-shot | 0.174 |

## Pipeline Notes

- Loaded 17 narrative units from data/test_documents/controlled_test.txt
- Extracted 55 state events across 17 units
- Detected 2 candidate conflicts
- Produced 2/2 investigation verdicts
- Eval completed in 638.4s
