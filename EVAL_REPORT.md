# StoryTrace Evaluation Report

**Document:** data/test_documents/controlled_test.txt

**Timestamp:** 2026-09-12T13:03:03.560600+00:00

**Overall F1:** 0.785 :warning:

## Phase Metrics

| Phase | Precision | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Extraction | 0.511 | 0.667 | 0.578 :x: | 24 | 23 | 12 |
| Detection | 1.000 | 0.800 | 0.889 :white_check_mark: | 4 | 0 | 1 |
| Investigation | 1.000 | 0.800 | 0.889 :white_check_mark: | 4 | 0 | 1 |

## Per-Unit Extraction Breakdown

| Unit | Extracted | Matched | Missed | Missed Attributes |
| --- | --- | --- | --- | --- |
| 1 | 4 | 4 | 0 |  |
| 2 | 2 | 1 | 1 | location=doorframe |
| 3 | 4 | 4 | 0 |  |
| 4 | 3 | 1 | 2 |  |
| 5 | 4 | 3 | 1 |  |
| 6 | 1 | 1 | 0 |  |
| 7 | 4 | 2 | 1 | location=apartment |
| 8 | 2 | 1 | 1 | possession.badge=held |
| 9 | 3 | 2 | 1 |  |
| 10 | 3 | 1 | 1 | location=precinct in New York |
| 11 | 2 | 2 | 0 |  |
| 12 | 5 | 1 | 1 | injury.forearm=injured |
| 13 | 6 | 1 | 5 |  |
| 14 | 2 | 0 | 2 | injury.forearm=healed, injury.forearm=injured |
| 15 | 2 | 0 | 1 | location=interrogation room |
| 17 | 0 | 0 | 4 | location=precinct, location=Chicago precinct, location=precinct, location=Chicago precinct |

## False Positives

### Extraction

- `MAYA` / `possession.badge` = `held`
- `COLE` / `location` = `river access road`
- `SUSPECT` / `location` = `river access road`
- `MAYA` / `location` = `precinct`
- `COLE` / `location` = `Coles apartment`
- `MAYA` / `possession.badge` = `held`
- `COLE` / `possession.badge` = `acquired`
- `SUSPECT` / `location` = `old rail yard`
- `COLE` / `possession.badge` = `held`
- `COLE` / `location` = `precinct`
- `COLE` / `injury.forearm` = `injured`
- `COLE` / `location` = `rooftop`
- `PARAMEDIC` / `possession.field_kit` = `held`
- `PARAMEDIC` / `location` = `rooftop`
- `COLE` / `possession.photographs` = `held`
- `COLE` / `possession.corkboard` = `held`
- `MAYA` / `location` = `precinct`
- `MAYA` / `possession.folder` = `held`
- `MAYA` / `possession.financial_records` = `held`
- `COLE` / `possession.bandage` = `lost`
- `COLE` / `injury.forearm` = `healed`
- `COLE` / `location` = `interrogation room`
- `SUSPECT'S LAWYER` / `location` = `interrogation room`

## False Negatives

### Extraction

- `COLE` / `possession.badge` = `held` @ unit 8
- `COLE` / `injury.forearm` = `injured` @ unit 12
- `COLE` / `injury.forearm` = `healed` @ unit 14
- `COLE` / `injury.forearm` = `injured` @ unit 14
- `MAYA` / `location` = `doorframe` @ unit 2
- `COLE` / `location` = `apartment` @ unit 7
- `COLE` / `location` = `interrogation room` @ unit 15
- `COLE` / `location` = `precinct in New York` @ unit 10
- `COLE` / `location` = `precinct` @ unit 17
- `COLE` / `location` = `Chicago precinct` @ unit 17
- `MAYA` / `location` = `precinct` @ unit 17
- `MAYA` / `location` = `Chicago precinct` @ unit 17

### Detection

- `COLE` / `injury.forearm` (expected: uncertain) -- Climbs a ladder with both hands shortly after a forearm slash — injury status at this point is ambiguous, not clearly re-established or healed

### Investigation

- `COLE` / `injury.forearm` (expected: uncertain) -- Climbs a ladder with both hands shortly after a forearm slash — injury status at this point is ambiguous, not clearly re-established or healed

## Prompt Engineering Impact

Units tested: 5

| Condition | F1 |
| --- | --- |
| No constraints | 0.000 |
| With vocabulary + few-shot | 0.824 |

## Pipeline Notes

- Loaded 17 narrative units from data/test_documents/controlled_test.txt
- Extracted 47 state events across 17 units
- Detected 4 candidate conflicts
- Produced 4/4 investigation verdicts
- Eval completed in 397.8s
