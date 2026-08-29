CREATE DATABASE IF NOT EXISTS storytrace;

CREATE TABLE IF NOT EXISTS storytrace.scenes (
    id String,
    screenplay_id String,
    number Int32,
    heading String,
    text String,
    start_page Int32,
    end_page Int32,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (screenplay_id, number);

CREATE TABLE IF NOT EXISTS storytrace.entities (
    id String,
    screenplay_id String,
    type Enum8('character' = 1, 'prop' = 2, 'location' = 3),
    name String,
    aliases Array(String),
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (screenplay_id, type, id);

CREATE TABLE IF NOT EXISTS storytrace.state_events (
    id String,
    screenplay_id String,
    entity_id String,
    attribute Enum8('presence' = 1, 'location' = 2, 'possession' = 3, 'injury' = 4, 'clothing' = 5),
    value String,
    scene_id String,
    scene_number Int32,
    page_ref Int32,
    raw_excerpt String,
    establishment_type String,
    confidence Float32,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (screenplay_id, entity_id, scene_number);

CREATE TABLE IF NOT EXISTS storytrace.candidate_conflicts (
    id String,
    screenplay_id String,
    entity_id String,
    prior_evidence_scene_id String,
    prior_evidence_excerpt String,
    current_evidence_scene_id String,
    current_evidence_excerpt String,
    description String,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (screenplay_id, entity_id, created_at);

CREATE TABLE IF NOT EXISTS storytrace.investigation_verdicts (
    id String,
    candidate_id String,
    status Enum8('verified' = 1, 'resolved' = 2, 'uncertain' = 3, 'intentional' = 4),
    severity Enum8('critical' = 1, 'warning' = 2, 'info' = 3),
    explanation String,
    confidence Float32,
    investigation_actions Array(String),
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (candidate_id, created_at);
