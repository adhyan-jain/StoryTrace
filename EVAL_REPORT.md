# StoryTrace Evaluation Report

**Document:** data/test_documents/controlled_test.txt

**Timestamp:** 2026-09-12T10:54:58.740298+00:00

**Overall F1:** 0.667 :warning:

## Phase Metrics

| Phase | Precision | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Extraction | 0.606 | 0.426 | 0.500 :x: | 20 | 13 | 27 |
| Detection | 1.000 | 0.600 | 0.750 :warning: | 3 | 0 | 2 |
| Investigation | 1.000 | 0.600 | 0.750 :warning: | 3 | 0 | 2 |

## Per-Unit Extraction Breakdown

| Unit | Extracted | Matched | Missed | Missed Attributes |
| --- | --- | --- | --- | --- |
| 1 | 3 | 2 | 2 | location=briefing room, possession.file=acquired |
| 2 | 3 | 2 | 1 |  |
| 3 | 2 | 2 | 4 | location=warehouse district, location=opposite rows, possession.radio=held, possession.radio=held |
| 4 | 1 | 1 | 0 |  |
| 5 | 3 | 2 | 1 | possession.badge=acquired |
| 6 | 1 | 0 | 1 |  |
| 7 | 3 | 2 | 2 | possession.badge=acquired, injury.forearm=injured |
| 8 | 1 | 1 | 1 | location=precinct |
| 9 | 2 | 1 | 1 | location=old rail yard |
| 10 | 3 | 2 | 1 |  |
| 11 | 2 | 1 | 2 | location=rooftop, location=fire escape |
| 12 | 2 | 2 | 1 | injury.forearm=injured |
| 13 | 2 | 0 | 1 | location=precinct |
| 14 | 0 | 0 | 2 | injury.forearm=healed, location=interrogation room |
| 15 | 1 | 0 | 4 | location=precinct, location=Chicago precinct, location=precinct, location=Chicago precinct |
| 16 | 2 | 0 | 2 | location=Chicago precinct, location=Chicago precinct |
| 17 | 2 | 2 | 4 | location=precinct, location=Chicago precinct, location=precinct, location=Chicago precinct |

## False Positives

### Extraction

- `COLE` / `possession.file` = `held`
- `FILE` / `possession` = `acquired`
- `COLE` / `location` = `Chicago precinct`
- `COLE` / `injury.forearm` = `injured`
- `MAYA` / `possession.badge` = `acquired`
- `SUSPECT` / `injury.head` = `injured`
- `COLE` / `possession.badge` = `held`
- `COLE` / `location` = `top of the rooftop`
- `COLE` / `location` = `Chicago precinct`
- `MAYA` / `location` = `Chicago precinct`
- `COLE` / `location` = `interrogation room`
- `COLE` / `location` = `Chicago precinct`
- `MAYA` / `location` = `Chicago precinct`

## False Negatives

### Extraction

- `COLE` / `possession.badge` = `acquired` @ unit 7
- `COLE` / `injury.forearm` = `injured` @ unit 12
- `COLE` / `injury.forearm` = `healed` @ unit 14
- `COLE` / `injury.forearm` = `injured` @ unit 7
- `COLE` / `location` = `briefing room` @ unit 1
- `COLE` / `possession.file` = `acquired` @ unit 1
- `MAYA` / `location` = `warehouse district` @ unit 3
- `MAYA` / `location` = `opposite rows` @ unit 3
- `COLE` / `possession.radio` = `held` @ unit 3
- `MAYA` / `possession.radio` = `held` @ unit 3
- `COLE` / `location` = `precinct` @ unit 8
- `COLE` / `location` = `old rail yard` @ unit 9
- `COLE` / `location` = `rooftop` @ unit 11
- `COLE` / `location` = `precinct` @ unit 13
- `COLE` / `location` = `interrogation room` @ unit 14
- `COLE` / `location` = `fire escape` @ unit 11
- `COLE` / `location` = `precinct` @ unit 15
- `COLE` / `location` = `Chicago precinct` @ unit 15
- `MAYA` / `location` = `precinct` @ unit 15
- `MAYA` / `location` = `Chicago precinct` @ unit 15
- `MAYA` / `possession.badge` = `acquired` @ unit 5
- `COLE` / `location` = `Chicago precinct` @ unit 16
- `MAYA` / `location` = `Chicago precinct` @ unit 16
- `COLE` / `location` = `precinct` @ unit 17
- `COLE` / `location` = `Chicago precinct` @ unit 17
- `MAYA` / `location` = `precinct` @ unit 17
- `MAYA` / `location` = `Chicago precinct` @ unit 17

### Detection

- `COLE` / `injury.forearm` (expected: uncertain) -- Climbs a ladder with both hands shortly after a forearm slash — injury status at this point is ambiguous, not clearly re-established or healed
- `COLE` / `injury.forearm` (expected: resolved) -- Injury explicitly healed via paramedic treatment and narrated recovery — not a real conflict

### Investigation

- `COLE` / `injury.forearm` (expected: uncertain) -- Climbs a ladder with both hands shortly after a forearm slash — injury status at this point is ambiguous, not clearly re-established or healed
- `COLE` / `injury.forearm` (expected: resolved) -- Injury explicitly healed via paramedic treatment and narrated recovery — not a real conflict

## Prompt Engineering Impact

Units tested: 5

| Condition | F1 |
| --- | --- |
| No constraints | 0.000 |
| With vocabulary + few-shot | 0.615 |

## Pipeline Notes

- Loaded 17 narrative units from data/test_documents/controlled_test.txt
- Extracted 33 state events across 17 units
- Detected 3 candidate conflicts
- Produced 3/3 investigation verdicts
- Eval completed in 1881.8s
