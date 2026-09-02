CREATE DATABASE IF NOT EXISTS storytrace;

CREATE TABLE IF NOT EXISTS storytrace.narrative_units (
    id String,
    story_universe_id String,
    document_id String,
    unit_type String,
    sequence_number Int32,
    title String,
    text String,
    start_page Int32,
    end_page Int32,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (story_universe_id, sequence_number);

CREATE TABLE IF NOT EXISTS storytrace.entities (
    id String,
    story_universe_id String,
    type Enum8('character' = 1, 'prop' = 2, 'location' = 3),
    name String,
    aliases Array(String),
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (story_universe_id, type, id);

CREATE TABLE IF NOT EXISTS storytrace.state_events (
    id String,
    story_universe_id String,
    entity_id String,
    -- Full dotted attribute path ("location", "possession.gun",
    -- "injury.left_arm", "clothing.jacket") rather than a fixed enum, so a
    -- transition on one specific prop/body part doesn't get conflated with
    -- every other prop/body part sharing the same coarse category.
    attribute String,
    value String,
    unit_id String,
    sequence_number Int32,
    page_ref Int32,
    raw_excerpt String,
    establishment_type String,
    confidence Float32,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (story_universe_id, entity_id, sequence_number);

CREATE TABLE IF NOT EXISTS storytrace.candidate_conflicts (
    id String,
    story_universe_id String,
    entity_id String,
    attribute String,
    prior_evidence_unit_id String,
    prior_evidence_excerpt String,
    current_evidence_unit_id String,
    current_evidence_excerpt String,
    description String,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (story_universe_id, entity_id, created_at);

CREATE TABLE IF NOT EXISTS storytrace.processing_status (
    story_universe_id String,
    status Enum8(
        'parsing'=1,'extracting'=2,'detecting'=3,
        'investigating'=4,'complete'=5,'failed'=6
    ),
    total_units UInt32,
    units_extracted UInt32,
    candidates_detected UInt32,
    verdicts_complete UInt32,
    error_message String DEFAULT '',
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (story_universe_id);

CREATE TABLE IF NOT EXISTS storytrace.users (
    id String,
    email String,
    password_hash String,
    created_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(created_at)
ORDER BY (email);

CREATE TABLE IF NOT EXISTS storytrace.projects (
    id String,
    user_id String,
    title String,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (user_id, created_at);

CREATE TABLE IF NOT EXISTS storytrace.project_versions (
    -- id == the story_universe_id that version's pipeline run is keyed by,
    -- so every existing narrative_units/state_events/candidate_conflicts
    -- query (all scoped by story_universe_id) needs no change.
    id String,
    project_id String,
    version_number UInt32,
    document_title String,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (project_id, version_number);

CREATE TABLE IF NOT EXISTS storytrace.investigation_verdicts (
    id String,
    candidate_id String,
    status Enum8('verified' = 1, 'resolved' = 2, 'uncertain' = 3, 'intentional' = 4),
    severity Enum8('critical' = 1, 'warning' = 2, 'info' = 3),
    explanation String,
    confidence Float32,
    investigation_actions Array(String),
    suggested_fix String DEFAULT '',
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (candidate_id, created_at);
