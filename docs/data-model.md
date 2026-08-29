# Data Model

The system uses append-only temporal events. The core concept is: `previous state + events -> expected state`.

## Entities

### `Scene`
- `id`: string
- `screenplay_id`: string
- `number`: int
- `heading`: string
- `text`: string
- `start_page`: int
- `end_page`: int

### `Entity`
- `id`: string
- `screenplay_id`: string
- `type`: character | prop | location
- `name`: string
- `aliases`: list of strings

### `StateEvent`
- `id`: string
- `screenplay_id`: string
- `entity_id`: string
- `attribute`: presence | location | possession | injury | clothing
- `value`: string (e.g., "lost", "acquired", "injured", "healed")
- `scene_id`: string
- `page_ref`: int
- `raw_excerpt`: string
- `establishment_type`: string
- `confidence`: float

### `CandidateConflict`
- `id`: string
- `screenplay_id`: string
- `entity_id`: string
- `prior_evidence`: Evidence (from `StateEvent`)
- `current_evidence`: Evidence
- `intervening_evidence`: list of Evidence
- `description`: string

### `InvestigationVerdict`
- `id`: string
- `candidate_id`: string
- `status`: verified | resolved | uncertain | intentional
- `severity`: critical | warning | info
- `explanation`: string
- `confidence`: float
- `evidence`: list of Evidence
- `scenes_examined`: list of ints
- `investigation_actions`: list of strings

### `Evidence`
Used within other schemas to maintain provenance.
- `scene_id`: string
- `page_ref`: int
- `raw_excerpt`: string
- `confidence`: float
- `establishment_type`: string

## Temporal State Transitions
Transitions are calculated by replaying `StateEvent`s over time. A missing bridging event (e.g., lost -> held without an acquired event) triggers a `CandidateConflict`.
