# StoryTrace Data Model

The data model unifies screenplays and novels under a single temporal event schema, grouping documents into a `story_universe`.

## 1. Document & Universe
A story universe can contain multiple documents (e.g., Book 1, Book 2, Screenplay 1).
- `story_universe_id` (str)
- `document_id` (str)
- `document_type` (str) - e.g., 'screenplay', 'novel'

## 2. NarrativeUnit
Replaces the old `Scene` model to support both formats.
- `unit_id` (str)
- `story_universe_id` (str)
- `document_id` (str)
- `unit_type` (str) - 'scene', 'chapter', 'passage'
- `sequence_number` (int) - For absolute ordering across the document
- `title` (str) - E.g., 'INT. WAREHOUSE - NIGHT' or 'Chapter 1'
- `page_start` (int)
- `page_end` (int)
- `raw_text` (str)

## 3. EntityRegistry
The canonical dictionary of story objects across the universe.
- `entity_id` (str)
- `story_universe_id` (str)
- `type` (str) - 'character', 'prop', 'location'
- `canonical_name` (str)
- `aliases` (list[str])

## 4. StateEvent (Append-only Temporal Log)
A single state transition established in the text.
- `event_id` (str)
- `story_universe_id` (str)
- `document_id` (str)
- `unit_id` (str)
- `sequence_number` (int) - For temporal ordering
- `entity_id` (str)
- `attribute` (str) - 'presence', 'location', 'possession', 'injury', 'clothing'
- `value` (str)
- `page_ref` (int)
- `raw_excerpt` (str)
- `confidence` (float)

## 5. CandidateConflict
A suspicious state transition detected by ClickHouse analytics.
- `candidate_id` (str)
- `story_universe_id` (str)
- `entity_id` (str)
- `attribute` (str)
- `prior_unit_id` (str)
- `prior_excerpt` (str)
- `current_unit_id` (str)
- `current_excerpt` (str)
- `description` (str)

## 6. InvestigationVerdict
The agent's conclusion on a candidate.
- `verdict_id` (str)
- `candidate_id` (str)
- `status` (str) - 'verified' | 'resolved' | 'uncertain' | 'intentional'
- `explanation` (str)
- `investigation_actions` (list[str])
