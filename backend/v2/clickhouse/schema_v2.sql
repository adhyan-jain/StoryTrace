CREATE DATABASE IF NOT EXISTS storytrace;

CREATE TABLE IF NOT EXISTS storytrace.state_events_v2 (
    id String,
    story_universe_id String,
    entity_id String,
    attribute String,
    value String,
    unit_id String,
    sequence_number Int32,
    page_ref Int32,
    raw_excerpt String,
    establishment_type String,
    confidence Float32,
    hier_setting_type String,
    hier_environment String,
    hier_specific_room String,
    hier_city_region String,
    time_anchor String,
    related_entity_id String,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (story_universe_id, entity_id, sequence_number);

CREATE TABLE IF NOT EXISTS storytrace.scene_co_presence_v2 (
    id String,
    story_universe_id String,
    unit_id String,
    sequence_number Int32,
    entity_ids Array(String),
    setting_type String,
    environment String,
    specific_room String,
    time_of_day String,
    time_anchor String,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (story_universe_id, sequence_number);

CREATE TABLE IF NOT EXISTS storytrace.candidate_conflicts_v2 (
    id String,
    story_universe_id String,
    rule_type String,
    entity_ids Array(String),
    attribute String,
    prior_evidence_unit_id String,
    prior_evidence_excerpt String,
    current_evidence_unit_id String,
    current_evidence_excerpt String,
    description String,
    severity_hint String,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (story_universe_id, created_at);

CREATE TABLE IF NOT EXISTS storytrace.investigation_verdicts_v2 (
    id String,
    candidate_id String,
    status String,
    severity String,
    explanation String,
    confidence Float32,
    investigation_actions Array(String),
    suggested_fix String,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (candidate_id, created_at);
