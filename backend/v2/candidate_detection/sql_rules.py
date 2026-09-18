"""SQL Detection Rules for StoryTrace V2 Candidate Detector.

All rules are implemented purely as deterministic ClickHouse SQL window queries,
temporal joins, and analytical functions. Zero LLM inference is performed.
"""

RULE_1_POSSESSION_SQL = """
WITH ranked_events AS (
    SELECT
        entity_id,
        unit_id,
        sequence_number,
        attribute,
        value,
        raw_excerpt,
        time_anchor,
        related_entity_id,
        lagInFrame(value) OVER (PARTITION BY entity_id, attribute ORDER BY sequence_number) AS prev_value,
        lagInFrame(unit_id) OVER (PARTITION BY entity_id, attribute ORDER BY sequence_number) AS prev_unit_id,
        lagInFrame(raw_excerpt) OVER (PARTITION BY entity_id, attribute ORDER BY sequence_number) AS prev_raw_excerpt,
        lagInFrame(sequence_number) OVER (PARTITION BY entity_id, attribute ORDER BY sequence_number) AS prev_seq,
        lagInFrame(time_anchor) OVER (PARTITION BY entity_id, attribute ORDER BY sequence_number) AS prev_time_anchor
    FROM state_events_v2
    WHERE story_universe_id = {story_universe_id:String}
      AND (attribute = 'possession' OR startsWith(attribute, 'possession.'))
      AND time_anchor NOT IN ('FLASHBACK', 'DREAM_SEQUENCE')
    ORDER BY entity_id, sequence_number
)
SELECT
    'possession_machine' AS rule_type,
    [entity_id] AS entity_ids,
    attribute,
    prev_unit_id,
    prev_raw_excerpt,
    unit_id,
    raw_excerpt,
    concat('Possession anomaly for ', entity_id, ' on ', attribute, ': ', prev_value, ' -> ', value, ' without acquisition/transfer bridge.') AS description,
    'warning' AS severity_hint
FROM ranked_events
WHERE (prev_value = 'lost' AND value = 'held')
   OR (prev_value = 'lost' AND value = 'acquired')
"""

RULE_2_CO_PRESENCE_COLLISION_SQL = """
WITH ranked_scenes AS (
    SELECT
        id,
        unit_id,
        sequence_number,
        entity_ids,
        setting_type,
        environment,
        specific_room,
        time_anchor,
        lagInFrame(unit_id) OVER (ORDER BY sequence_number) AS prev_unit_id,
        lagInFrame(sequence_number) OVER (ORDER BY sequence_number) AS prev_seq,
        lagInFrame(entity_ids) OVER (ORDER BY sequence_number) AS prev_entity_ids,
        lagInFrame(environment) OVER (ORDER BY sequence_number) AS prev_environment,
        lagInFrame(specific_room) OVER (ORDER BY sequence_number) AS prev_specific_room
    FROM scene_co_presence_v2
    WHERE story_universe_id = {story_universe_id:String}
      AND time_anchor NOT IN ('FLASHBACK', 'DREAM_SEQUENCE')
    ORDER BY sequence_number
)
SELECT
    'co_presence_collision' AS rule_type,
    arrayIntersect(entity_ids, prev_entity_ids) AS entity_ids,
    'co_presence' AS attribute,
    prev_unit_id,
    concat('Present in ', prev_environment, ' (', prev_specific_room, ')') AS prev_raw_excerpt,
    unit_id,
    concat('Present in ', environment, ' (', specific_room, ')') AS current_raw_excerpt,
    concat('Entities ', toString(arrayIntersect(entity_ids, prev_entity_ids)), ' present in continuous scenes across disparate environments: ', prev_environment, ' -> ', environment) AS description,
    'critical' AS severity_hint
FROM ranked_scenes
WHERE time_anchor IN ('CONTINUOUS', 'MOMENTS_LATER')
  AND length(arrayIntersect(entity_ids, prev_entity_ids)) > 0
  AND environment != '' AND prev_environment != ''
  AND environment != prev_environment
"""

RULE_3_SPATIAL_JUMP_SQL = """
WITH ranked_locations AS (
    SELECT
        entity_id,
        unit_id,
        sequence_number,
        attribute,
        value,
        raw_excerpt,
        hier_setting_type,
        hier_environment,
        hier_specific_room,
        hier_city_region,
        time_anchor,
        lagInFrame(hier_environment) OVER (PARTITION BY entity_id ORDER BY sequence_number) AS prev_env,
        lagInFrame(hier_specific_room) OVER (PARTITION BY entity_id ORDER BY sequence_number) AS prev_room,
        lagInFrame(hier_city_region) OVER (PARTITION BY entity_id ORDER BY sequence_number) AS prev_city,
        lagInFrame(unit_id) OVER (PARTITION BY entity_id ORDER BY sequence_number) AS prev_unit_id,
        lagInFrame(raw_excerpt) OVER (PARTITION BY entity_id ORDER BY sequence_number) AS prev_raw_excerpt
    FROM state_events_v2
    WHERE story_universe_id = {story_universe_id:String}
      AND (attribute = 'location' OR startsWith(attribute, 'location.'))
      AND time_anchor NOT IN ('FLASHBACK', 'DREAM_SEQUENCE')
    ORDER BY entity_id, sequence_number
)
SELECT
    'continuous_spatial_jump' AS rule_type,
    [entity_id] AS entity_ids,
    attribute,
    prev_unit_id,
    prev_raw_excerpt,
    unit_id,
    raw_excerpt,
    concat('Unbridged continuous spatial jump for ', entity_id, ' from [', prev_city, ' / ', prev_env, ' / ', prev_room, '] to [', hier_city_region, ' / ', hier_environment, ' / ', hier_specific_room, '] under pacing ', time_anchor) AS description,
    CASE 
        WHEN prev_city != '' AND hier_city_region != '' AND prev_city != hier_city_region THEN 'critical'
        WHEN prev_env != '' AND hier_environment != '' AND prev_env != hier_environment THEN 'warning'
        ELSE 'info'
    END AS severity_hint
FROM ranked_locations
WHERE time_anchor IN ('CONTINUOUS', 'MOMENTS_LATER')
  AND (
      (prev_city != '' AND hier_city_region != '' AND prev_city != hier_city_region) OR
      (prev_env != '' AND hier_environment != '' AND prev_env != hier_environment)
  )
"""

RULE_4_PHYSICAL_INVERSION_SQL = """
WITH ranked_physical AS (
    SELECT
        entity_id,
        unit_id,
        sequence_number,
        attribute,
        value,
        raw_excerpt,
        time_anchor,
        lagInFrame(value) OVER (PARTITION BY entity_id, attribute ORDER BY sequence_number) AS prev_value,
        lagInFrame(unit_id) OVER (PARTITION BY entity_id, attribute ORDER BY sequence_number) AS prev_unit_id,
        lagInFrame(raw_excerpt) OVER (PARTITION BY entity_id, attribute ORDER BY sequence_number) AS prev_raw_excerpt
    FROM state_events_v2
    WHERE story_universe_id = {story_universe_id:String}
      AND (startsWith(attribute, 'injury.') OR startsWith(attribute, 'physical.'))
      AND time_anchor NOT IN ('FLASHBACK', 'DREAM_SEQUENCE')
    ORDER BY entity_id, sequence_number
)
SELECT
    'physical_inversion' AS rule_type,
    [entity_id] AS entity_ids,
    attribute,
    prev_unit_id,
    prev_raw_excerpt,
    unit_id,
    raw_excerpt,
    concat('Physical state inversion for ', entity_id, ' on ', attribute, ': ', prev_value, ' -> ', value, ' without recorded medical/recovery event.') AS description,
    'warning' AS severity_hint
FROM ranked_physical
WHERE (prev_value = 'injured' AND value = 'healed')
   OR (prev_value = 'dead' AND value IN ('active', 'alive', 'healed', 'held', 'wearing'))
   OR (prev_value = 'restrained' AND value = 'free')
"""

RULE_5_CLOTHING_SWAP_SQL = """
WITH ranked_clothing AS (
    SELECT
        entity_id,
        unit_id,
        sequence_number,
        attribute,
        value,
        raw_excerpt,
        time_anchor,
        lagInFrame(value) OVER (PARTITION BY entity_id, attribute ORDER BY sequence_number) AS prev_value,
        lagInFrame(unit_id) OVER (PARTITION BY entity_id, attribute ORDER BY sequence_number) AS prev_unit_id,
        lagInFrame(raw_excerpt) OVER (PARTITION BY entity_id, attribute ORDER BY sequence_number) AS prev_raw_excerpt
    FROM state_events_v2
    WHERE story_universe_id = {story_universe_id:String}
      AND startsWith(attribute, 'clothing.')
      AND time_anchor NOT IN ('FLASHBACK', 'DREAM_SEQUENCE')
    ORDER BY entity_id, sequence_number
)
SELECT
    'clothing_swap' AS rule_type,
    [entity_id] AS entity_ids,
    attribute,
    prev_unit_id,
    prev_raw_excerpt,
    unit_id,
    raw_excerpt,
    concat('Instantaneous wardrobe change for ', entity_id, ' on ', attribute, ': "', prev_value, '" -> "', value, '" under continuous pacing.') AS description,
    'info' AS severity_hint
FROM ranked_clothing
WHERE time_anchor IN ('CONTINUOUS', 'MOMENTS_LATER')
  AND prev_value != '' AND value != '' AND prev_value != value
"""

RULE_6_EPISTEMIC_ORDERING_SQL = """
WITH ranked_epistemic AS (
    SELECT
        entity_id,
        unit_id,
        sequence_number,
        attribute,
        value,
        raw_excerpt,
        time_anchor,
        lagInFrame(value) OVER (PARTITION BY entity_id, attribute ORDER BY sequence_number) AS prev_value,
        lagInFrame(unit_id) OVER (PARTITION BY entity_id, attribute ORDER BY sequence_number) AS prev_unit_id,
        lagInFrame(raw_excerpt) OVER (PARTITION BY entity_id, attribute ORDER BY sequence_number) AS prev_raw_excerpt
    FROM state_events_v2
    WHERE story_universe_id = {story_universe_id:String}
      AND startsWith(attribute, 'knowledge.')
      AND time_anchor NOT IN ('FLASHBACK', 'DREAM_SEQUENCE')
    ORDER BY entity_id, sequence_number
)
SELECT
    'epistemic_anomaly' AS rule_type,
    [entity_id] AS entity_ids,
    attribute,
    prev_unit_id,
    prev_raw_excerpt,
    unit_id,
    raw_excerpt,
    concat('Epistemic jump for ', entity_id, ' on ', attribute, ': was "', prev_value, '" but now acts as "', value, '" without discovery event.') AS description,
    'warning' AS severity_hint
FROM ranked_epistemic
WHERE time_anchor IN ('CONTINUOUS', 'MOMENTS_LATER')
  AND prev_value = 'unaware' AND value = 'knows'
"""

RULE_7_RELATIONAL_RUPTURE_SQL = """
WITH ranked_relational AS (
    SELECT
        entity_id,
        unit_id,
        sequence_number,
        attribute,
        value,
        raw_excerpt,
        time_anchor,
        lagInFrame(value) OVER (PARTITION BY entity_id, attribute ORDER BY sequence_number) AS prev_value,
        lagInFrame(unit_id) OVER (PARTITION BY entity_id, attribute ORDER BY sequence_number) AS prev_unit_id,
        lagInFrame(raw_excerpt) OVER (PARTITION BY entity_id, attribute ORDER BY sequence_number) AS prev_raw_excerpt
    FROM state_events_v2
    WHERE story_universe_id = {story_universe_id:String}
      AND startsWith(attribute, 'relation.')
      AND time_anchor NOT IN ('FLASHBACK', 'DREAM_SEQUENCE')
    ORDER BY entity_id, sequence_number
)
SELECT
    'relational_rupture' AS rule_type,
    [entity_id] AS entity_ids,
    attribute,
    prev_unit_id,
    prev_raw_excerpt,
    unit_id,
    raw_excerpt,
    concat('Unexplained alliance transition for ', entity_id, ' on ', attribute, ': "', prev_value, '" -> "', value, '" under continuous scene pacing.') AS description,
    'warning' AS severity_hint
FROM ranked_relational
WHERE time_anchor IN ('CONTINUOUS', 'MOMENTS_LATER')
  AND prev_value IN ('enemy', 'hostile', 'estranged', 'captive')
  AND value IN ('ally', 'partner', 'friend')
"""

RULE_8_EVENT_CHRONOLOGY_SQL = """
WITH ranked_events AS (
    SELECT
        entity_id,
        unit_id,
        sequence_number,
        attribute,
        value,
        raw_excerpt,
        time_anchor,
        lagInFrame(sequence_number) OVER (PARTITION BY entity_id, attribute ORDER BY sequence_number) AS prev_seq,
        lagInFrame(unit_id) OVER (PARTITION BY entity_id, attribute ORDER BY sequence_number) AS prev_unit_id,
        lagInFrame(raw_excerpt) OVER (PARTITION BY entity_id, attribute ORDER BY sequence_number) AS prev_raw_excerpt
    FROM state_events_v2
    WHERE story_universe_id = {story_universe_id:String}
      AND time_anchor = 'FLASHBACK'
    ORDER BY entity_id, sequence_number
)
SELECT
    'chronology_inversion' AS rule_type,
    [entity_id] AS entity_ids,
    attribute,
    prev_unit_id,
    prev_raw_excerpt,
    unit_id,
    raw_excerpt,
    concat('Non-linear flashback marker detected for ', entity_id, ' on ', attribute, ' across narrative sequence.') AS description,
    'info' AS severity_hint
FROM ranked_events
WHERE prev_unit_id != ''
"""
