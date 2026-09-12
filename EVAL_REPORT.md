# StoryTrace Evaluation Report

**Document:** data/test_documents/controlled_test.txt

**Timestamp:** 2026-09-12T22:53:56.352718+00:00

**Overall F1:** 0.832 :white_check_mark:

## Phase Metrics

| Phase | Precision | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Extraction | 0.821 | 0.639 | 0.719 :warning: | 23 | 5 | 13 |
| Detection | 1.000 | 0.800 | 0.889 :white_check_mark: | 4 | 0 | 1 |
| Investigation | 1.000 | 0.800 | 0.889 :white_check_mark: | 4 | 0 | 1 |

## Per-Unit Extraction Breakdown

| Unit | Extracted | Matched | Missed | Missed Attributes |
| --- | --- | --- | --- | --- |
| 1 | 3 | 3 | 0 |  |
| 2 | 1 | 0 | 2 | location=doorframe, possession.file=lost |
| 3 | 3 | 3 | 2 | possession.radio=held, possession.radio=held |
| 4 | 1 | 1 | 2 | location=river access road, location=river access road |
| 5 | 2 | 2 | 1 | location=precinct |
| 6 | 1 | 0 | 1 |  |
| 7 | 3 | 3 | 1 | injury.forearm=injured |
| 8 | 1 | 1 | 1 | location=precinct |
| 9 | 2 | 2 | 1 | location=old rail yard |
| 10 | 3 | 2 | 1 |  |
| 11 | 1 | 1 | 0 |  |
| 12 | 2 | 1 | 1 | injury.forearm=injured |
| 13 | 1 | 1 | 1 | location=precinct |
| 14 | 1 | 1 | 0 |  |
| 15 | 0 | 0 | 1 | location=interrogation room |
| 16 | 1 | 0 | 1 |  |
| 17 | 2 | 2 | 0 |  |

## False Positives

### Extraction

- `MAYA` / `possession.badge` = `held`
- `COLE` / `injury.forearm` = `injured`
- `COLE` / `possession.badge` = `held`
- `COLE` / `injury.forearm` = `injured`
- `COLE` / `possession.report` = `held`

## False Negatives

### Extraction

- `COLE` / `location` = `river access road` @ unit 4
- `SUSPECT` / `location` = `river access road` @ unit 4
- `COLE` / `injury.forearm` = `injured` @ unit 12
- `COLE` / `injury.forearm` = `injured` @ unit 7
- `MAYA` / `location` = `doorframe` @ unit 2
- `COLE` / `possession.file` = `lost` @ unit 2
- `COLE` / `possession.radio` = `held` @ unit 3
- `MAYA` / `possession.radio` = `held` @ unit 3
- `COLE` / `location` = `precinct` @ unit 5
- `COLE` / `location` = `precinct` @ unit 8
- `COLE` / `location` = `old rail yard` @ unit 9
- `MAYA` / `location` = `precinct` @ unit 13
- `COLE` / `location` = `interrogation room` @ unit 15

### Detection

- `COLE` / `injury.forearm` (expected: uncertain) -- Climbs a ladder with both hands shortly after a forearm slash — injury status at this point is ambiguous, not clearly re-established or healed

### Investigation

- `COLE` / `injury.forearm` (expected: uncertain) -- Climbs a ladder with both hands shortly after a forearm slash — injury status at this point is ambiguous, not clearly re-established or healed

## Prompt Engineering Impact

Units tested: 5

| Condition | F1 |
| --- | --- |
| No constraints | 0.000 |
| With vocabulary + few-shot | 0.621 |

## Pipeline Notes

- Loaded 17 narrative units from data/test_documents/controlled_test.txt
- Extracted 28 state events across 17 units
- Detected 4 candidate conflicts
- Produced 4/4 investigation verdicts
- Eval completed in 431.0s
