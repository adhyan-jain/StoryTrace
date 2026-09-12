# StoryTrace Evaluation Report

**Document:** data/test_documents/controlled_test.txt

**Timestamp:** 2026-09-12T16:13:39.302165+00:00

**Overall F1:** 0.593 :x:

## Phase Metrics

| Phase | Precision | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Extraction | 0.500 | 0.564 | 0.530 :x: | 22 | 22 | 17 |
| Detection | 1.000 | 0.600 | 0.750 :warning: | 3 | 0 | 2 |
| Investigation | 0.667 | 0.400 | 0.500 :x: | 2 | 1 | 3 |

## Per-Unit Extraction Breakdown

| Unit | Extracted | Matched | Missed | Missed Attributes |
| --- | --- | --- | --- | --- |
| 1 | 3 | 3 | 0 |  |
| 2 | 3 | 1 | 1 | location=doorframe |
| 3 | 3 | 2 | 4 | location=warehouse district, location=opposite rows, possession.radio=held, possession.radio=held |
| 4 | 1 | 1 | 2 | location=river access road, location=river access road |
| 5 | 2 | 2 | 1 | location=precinct |
| 6 | 2 | 0 | 2 |  |
| 7 | 4 | 2 | 2 | possession.badge=acquired, injury.forearm=injured |
| 8 | 1 | 1 | 1 | location=precinct |
| 9 | 3 | 2 | 1 | location=old rail yard |
| 10 | 3 | 2 | 1 |  |
| 11 | 4 | 2 | 2 |  |
| 12 | 2 | 1 | 1 | injury.forearm=injured |
| 13 | 3 | 1 | 1 | location=precinct |
| 14 | 0 | 0 | 2 | injury.forearm=healed, injury.forearm=injured |
| 15 | 2 | 0 | 1 | location=interrogation room |
| 16 | 6 | 0 | 6 |  |
| 17 | 2 | 2 | 0 |  |

## False Positives

### Extraction

- `COLE` / `location` = `doorframe`
- `MAYA` / `possession.badge` = `held`
- `MAYA` / `location` = `warehouse district`
- `COLE` / `injury.forearm` = `injured`
- `COLE` / `location` = `opposite rows`
- `COLE` / `possession.badge` = `lost`
- `MAYA` / `possession.badge` = `acquired`
- `SUSPECT` / `injury.head` = `injured`
- `COLE` / `possession.badge` = `held`
- `COLE` / `location` = `top of the rooftop`
- `COLE` / `location` = `fire escape behind a shuttered diner`
- `COLE` / `injury.forearm` = `injured`
- `COLE` / `possession.photographs` = `held`
- `MAYA` / `location` = `precinct`
- `COLE` / `location` = `interrogation room`
- `SUSPECT'S LAWYER` / `location` = `interrogation room`
- `CAPTAIN` / `location` = `Chicago precinct`
- `COLE` / `location` = `captains office`
- `COLE` / `possession.report` = `held`
- `COLE` / `location` = `Chicago precinct`
- `MAYA` / `location` = `captains office`
- `MAYA` / `location` = `Chicago precinct`

### Investigation

- `COLE` / `possession.badge`

## False Negatives

### Extraction

- `COLE` / `location` = `river access road` @ unit 4
- `SUSPECT` / `location` = `river access road` @ unit 4
- `COLE` / `possession.badge` = `acquired` @ unit 7
- `COLE` / `injury.forearm` = `injured` @ unit 12
- `COLE` / `injury.forearm` = `healed` @ unit 14
- `COLE` / `injury.forearm` = `injured` @ unit 7
- `COLE` / `injury.forearm` = `injured` @ unit 14
- `MAYA` / `location` = `doorframe` @ unit 2
- `MAYA` / `location` = `warehouse district` @ unit 3
- `MAYA` / `location` = `opposite rows` @ unit 3
- `COLE` / `possession.radio` = `held` @ unit 3
- `MAYA` / `possession.radio` = `held` @ unit 3
- `COLE` / `location` = `precinct` @ unit 5
- `COLE` / `location` = `precinct` @ unit 8
- `COLE` / `location` = `old rail yard` @ unit 9
- `MAYA` / `location` = `precinct` @ unit 13
- `COLE` / `location` = `interrogation room` @ unit 15

### Detection

- `COLE` / `injury.forearm` (expected: uncertain) -- Climbs a ladder with both hands shortly after a forearm slash — injury status at this point is ambiguous, not clearly re-established or healed
- `COLE` / `injury.forearm` (expected: resolved) -- Injury explicitly healed via paramedic treatment and narrated recovery — not a real conflict

### Investigation

- `COLE` / `injury.forearm` (expected: uncertain) -- Climbs a ladder with both hands shortly after a forearm slash — injury status at this point is ambiguous, not clearly re-established or healed
- `COLE` / `possession.badge` (expected: resolved) -- Badge taken as evidence then explicitly returned next morning — not a real conflict
- `COLE` / `injury.forearm` (expected: resolved) -- Injury explicitly healed via paramedic treatment and narrated recovery — not a real conflict

## Prompt Engineering Impact

Units tested: 5

| Condition | F1 |
| --- | --- |
| No constraints | 0.000 |
| With vocabulary + few-shot | 0.621 |

## Pipeline Notes

- Loaded 17 narrative units from data/test_documents/controlled_test.txt
- Extracted 44 state events across 17 units
- Detected 3 candidate conflicts
- Produced 3/3 investigation verdicts
- Eval completed in 2009.8s
