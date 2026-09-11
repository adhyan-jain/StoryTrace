# StoryTrace Evaluation Report

**Document:** data/test_documents/controlled_test.txt

**Timestamp:** 2026-09-11T09:49:39.579861+00:00

**Overall F1:** 0.655 :warning:

## Phase Metrics

| Phase | Precision | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Extraction | 0.276 | 0.800 | 0.410 :x: | 16 | 42 | 4 |
| Detection | 1.000 | 0.800 | 0.889 :white_check_mark: | 4 | 0 | 1 |
| Investigation | 0.750 | 0.600 | 0.667 :warning: | 3 | 1 | 2 |

## Per-Unit Extraction Breakdown

| Unit | Extracted | Matched | Missed | Missed Attributes |
| --- | --- | --- | --- | --- |
| 1 | 5 | 3 | 1 | location=chicago precinct |
| 2 | 4 | 2 | 2 |  |
| 3 | 4 | 4 | 0 |  |
| 4 | 4 | 1 | 3 |  |
| 5 | 5 | 1 | 4 |  |
| 6 | 3 | 1 | 2 |  |
| 7 | 4 | 0 | 4 |  |
| 8 | 2 | 1 | 1 | possession.badge=held |
| 9 | 3 | 1 | 2 |  |
| 10 | 4 | 1 | 3 |  |
| 11 | 3 | 0 | 3 |  |
| 12 | 4 | 1 | 1 | injury.forearm=injured |
| 13 | 5 | 0 | 5 |  |
| 14 | 4 | 0 | 1 | injury.forearm=healed |
| 15 | 1 | 0 | 1 |  |
| 16 | 1 | 0 | 1 |  |
| 17 | 2 | 0 | 2 |  |

## False Positives

### Extraction

- `COLE` / `location` = `window of the Chicago precinct`
- `CASE FILE` / `possession` = `acquired`
- `COLE` / `location` = `table`
- `MAYA` / `possession.badge` = `held`
- `GUN` / `possession` = `lost`
- `COLE` / `location` = `river access road`
- `SUSPECT` / `location` = `river access road`
- `MAYA` / `possession.evidence bag` = `held`
- `MAYA` / `possession.badge` = `acquired`
- `MAYA` / `location` = `precinct`
- `COLE` / `location` = `precinct`
- `SUSPECT` / `possession.knife` = `lost`
- `SUSPECT` / `possession.knife` = `held`
- `COLE` / `location` = `couch`
- `MAYA` / `possession.badge` = `held`
- `COLE` / `injury.forearm` = `injured`
- `COLE` / `location` = `Coles apartment`
- `COLE` / `location` = `precinct doors`
- `THE SUSPECT` / `location` = `chain-link fence`
- `THE SUSPECT` / `location` = `old rail yard`
- `COLE` / `location` = `corner office`
- `COLE` / `possession.badge` = `held`
- `COLE` / `location` = `precinct`
- `COLE` / `location` = `rooftop`
- `COLE` / `location` = `fire escape behind a shuttered diner`
- `COLE` / `possession.rusted ladder` = `held`
- `PARAMEDIC` / `possession.field kit` = `held`
- `COLE` / `injury.forearm` = `injured`
- `COLE` / `location` = `beside paramedic`
- `MAYA` / `location` = `precinct`
- `MAYA` / `possession.folder of financial records` = `held`
- `COLE` / `possession.red string` = `held`
- `COLE` / `possession.photographs` = `held`
- `COLE` / `location` = `precinct`
- `COLE` / `location` = `his chair`
- `COLE` / `possession.bandage` = `lost`
- `COLE` / `injury.forearm` = `healed`
- `COLE` / `possession.coffee` = `acquired`
- `COLE` / `location` = `interrogation room`
- `COLE` / `possession.final report` = `held`
- `COLE` / `location` = `precinct`
- `MAYA` / `location` = `precinct`

### Investigation

- `COLE` / `injury.forearm`

## False Negatives

### Extraction

- `COLE` / `possession.badge` = `held` @ unit 8
- `COLE` / `location` = `chicago precinct` @ unit 1
- `COLE` / `injury.forearm` = `injured` @ unit 12
- `COLE` / `injury.forearm` = `healed` @ unit 14

### Detection

- `COLE` / `injury.forearm` (expected: uncertain) -- Climbs a ladder with both hands shortly after a forearm slash — injury status at this point is ambiguous, not clearly re-established or healed

### Investigation

- `COLE` / `injury.forearm` (expected: uncertain) -- Climbs a ladder with both hands shortly after a forearm slash — injury status at this point is ambiguous, not clearly re-established or healed
- `COLE` / `injury.forearm` (expected: resolved) -- Injury explicitly healed via paramedic treatment and narrated recovery — not a real conflict

## Prompt Engineering Impact

Units tested: 5

| Condition | F1 |
| --- | --- |
| No constraints | 0.000 |
| With vocabulary + few-shot | 0.727 |

## Pipeline Notes

- Loaded 17 narrative units from data/test_documents/controlled_test.txt
- Extracted 58 state events across 17 units
- Detected 4 candidate conflicts
- Produced 4/4 investigation verdicts
- Eval completed in 460.7s
