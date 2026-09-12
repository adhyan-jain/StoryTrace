# StoryTrace Evaluation Report

**Document:** data/test_documents/controlled_test.txt

**Timestamp:** 2026-09-12T20:06:46.966048+00:00

**Overall F1:** 0.784 :warning:

## Phase Metrics

| Phase | Precision | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Extraction | 0.568 | 0.583 | 0.575 :x: | 21 | 16 | 15 |
| Detection | 1.000 | 0.800 | 0.889 :white_check_mark: | 4 | 0 | 1 |
| Investigation | 1.000 | 0.800 | 0.889 :white_check_mark: | 4 | 0 | 1 |

## Per-Unit Extraction Breakdown

| Unit | Extracted | Matched | Missed | Missed Attributes |
| --- | --- | --- | --- | --- |
| 1 | 3 | 2 | 1 | possession.file=acquired |
| 2 | 2 | 1 | 1 | location=doorframe |
| 3 | 3 | 3 | 2 | possession.radio=held, possession.radio=held |
| 4 | 1 | 1 | 2 | location=river access road, location=river access road |
| 5 | 2 | 2 | 1 | location=precinct |
| 6 | 2 | 0 | 2 |  |
| 7 | 3 | 2 | 2 | possession.badge=acquired, injury.forearm=injured |
| 8 | 1 | 1 | 1 | location=precinct |
| 9 | 2 | 1 | 2 | location=old rail yard, location=old rail yard |
| 10 | 3 | 2 | 1 |  |
| 11 | 2 | 1 | 1 |  |
| 12 | 2 | 1 | 1 | injury.forearm=injured |
| 13 | 2 | 1 | 1 | location=precinct |
| 14 | 1 | 1 | 0 |  |
| 15 | 2 | 0 | 1 | location=interrogation room |
| 16 | 4 | 0 | 4 |  |
| 17 | 2 | 2 | 0 |  |

## False Positives

### Extraction

- `COLE` / `possession.file` = `held`
- `MAYA` / `possession.badge` = `held`
- `COLE` / `injury.forearm` = `injured`
- `COLE` / `location` = `opposite rows`
- `MAYA` / `possession.badge` = `acquired`
- `SUSPECT` / `injury.head` = `injured`
- `COLE` / `possession.badge` = `held`
- `COLE` / `location` = `top of the rooftop`
- `COLE` / `injury.forearm` = `injured`
- `MAYA` / `location` = `precinct`
- `COLE` / `location` = `interrogation room`
- `SUSPECT'S LAWYER` / `location` = `interrogation room`
- `CAPTAIN` / `location` = `captains office`
- `COLE` / `location` = `captains office`
- `COLE` / `possession.report` = `held`
- `MAYA` / `location` = `captains office`

## False Negatives

### Extraction

- `COLE` / `location` = `river access road` @ unit 4
- `SUSPECT` / `location` = `river access road` @ unit 4
- `COLE` / `possession.badge` = `acquired` @ unit 7
- `COLE` / `injury.forearm` = `injured` @ unit 12
- `COLE` / `injury.forearm` = `injured` @ unit 7
- `COLE` / `possession.file` = `acquired` @ unit 1
- `MAYA` / `location` = `doorframe` @ unit 2
- `COLE` / `possession.radio` = `held` @ unit 3
- `MAYA` / `possession.radio` = `held` @ unit 3
- `COLE` / `location` = `precinct` @ unit 5
- `COLE` / `location` = `precinct` @ unit 8
- `COLE` / `location` = `old rail yard` @ unit 9
- `SUSPECT` / `location` = `old rail yard` @ unit 9
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
- Extracted 37 state events across 17 units
- Detected 4 candidate conflicts
- Produced 4/4 investigation verdicts
- Eval completed in 599.1s
