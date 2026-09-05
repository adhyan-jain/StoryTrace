"""Seeds every user account with pre-run demo projects (results included),
so a new signup lands on a populated dashboard instead of an empty one.

The sources are real pipeline runs already sitting in ClickHouse. This script
clones their rows -- narrative units, entities, state events, candidate
conflicts, verdicts, processing status, project + version(s) -- into a fresh
project scoped to a target user, via ClickHouse INSERT ... SELECT with
replaceAll() on the id columns (entity/candidate/unit ids all embed the
project_id or story_universe_id as a string prefix, so a substring swap is
enough to re-scope a whole row tree without touching business logic).

Run manually for existing accounts:
    python -m backend.seed_demo_projects --user-id <id>
    python -m backend.seed_demo_projects --all-users

Called automatically for every new signup from backend/api/main.py.
"""

import argparse
import uuid

from backend.clickhouse.client import ClickHouseClient

# Each entry is one demo project, possibly with more than one version --
# "source_project_id" scopes entity ids for ALL of that project's versions
# (see EntityRegistry's id_scope), so version_number/story_universe_id pairs
# under the same project clone together and stay diffable against each other
# the same way the original run was. Do not delete these source rows -- every
# user's seeded copy is derived from them at signup/seed time.
DEMO_SOURCES = [
    {
        "source_project_id": "0dec3afb5ebe4483a4ea45136f3eea20",
        "title": "Reverend Insanity (Sample)",
        "versions": [
            (1, "ri_sample_41f2c938", "Reverend Insanity -- complete"),
        ],
    },
    {
        "source_project_id": "e5ee7501878c4c24ae9f1d831f5316aa",
        "title": "Demo: Controlled Test",
        "versions": [
            (1, "dbec5a9296404283b043006ecf917ebb", "controlled_test.txt"),
            (2, "fd5465d6b7e54b63b666165077095e3f", "controlled_test_v2.txt"),
        ],
    },
    {
        "source_project_id": "af78c054e6a9427881e297a0a6162589",
        "title": "Demo: Oppenheimer",
        "versions": [
            (1, "edfb34d65ef94001a3a5e2d53ad7a795", "oppenheimer.pdf"),
        ],
    },
]

_DEMO_TITLES = [source["title"] for source in DEMO_SOURCES]


def _new_id() -> str:
    return uuid.uuid4().hex


def seed_demo_projects_for_user(client: ClickHouseClient, user_id: str) -> list[str]:
    """Clones the fixed demo projects (each with all of its versions) into
    new projects owned by user_id. Returns the new project ids. Safe to call
    more than once -- each call creates a fresh independent copy, so call
    only when a user has none yet (see has_demo_projects) unless duplicates
    are intended."""
    created_project_ids = []

    for source in DEMO_SOURCES:
        old_pid = source["source_project_id"]
        title = source["title"]
        new_pid = _new_id()
        created_project_ids.append(new_pid)

        client.client.command(
            "INSERT INTO projects (id, user_id, title) VALUES ({pid:String}, {uid:String}, {title:String})",
            parameters={"pid": new_pid, "uid": user_id, "title": title},
        )

        for version_number, old_suid, version_title in source["versions"]:
            new_suid = _new_id()
            client.client.command(
                "INSERT INTO project_versions (id, project_id, version_number, document_title) "
                "VALUES ({suid:String}, {pid:String}, {vnum:UInt32}, {title:String})",
                parameters={"suid": new_suid, "pid": new_pid, "vnum": version_number, "title": version_title},
            )
            _clone_version(client, old_pid, new_pid, old_suid, new_suid)

    return created_project_ids


def _clone_version(client: ClickHouseClient, old_pid: str, new_pid: str, old_suid: str, new_suid: str) -> None:
    """Clones one version's narrative_units/entities/state_events/
    candidate_conflicts/investigation_verdicts/processing_status rows from
    (old_pid, old_suid) to (new_pid, new_suid)."""
    client.client.command(
        """
        INSERT INTO narrative_units
            (id, story_universe_id, document_id, unit_type, sequence_number,
             title, text, start_page, end_page)
        SELECT
            replaceAll(id, {old_suid:String}, {new_suid:String}),
            {new_suid:String},
            replaceAll(document_id, {old_suid:String}, {new_suid:String}),
            unit_type, sequence_number, title, text, start_page, end_page
        FROM narrative_units WHERE story_universe_id = {old_suid:String}
        """,
        parameters={"old_suid": old_suid, "new_suid": new_suid},
    )

    client.client.command(
        """
        INSERT INTO entities (id, story_universe_id, type, name, aliases)
        SELECT
            replaceAll(replaceAll(id, {old_pid:String}, {new_pid:String}), {old_suid:String}, {new_suid:String}),
            {new_suid:String},
            type, name, aliases
        FROM entities WHERE story_universe_id = {old_suid:String}
        """,
        parameters={"old_pid": old_pid, "new_pid": new_pid, "old_suid": old_suid, "new_suid": new_suid},
    )

    client.client.command(
        """
        INSERT INTO state_events
            (id, story_universe_id, entity_id, attribute, value, unit_id,
             sequence_number, page_ref, raw_excerpt, establishment_type, confidence)
        SELECT
            generateUUIDv4(),
            {new_suid:String},
            replaceAll(replaceAll(entity_id, {old_pid:String}, {new_pid:String}), {old_suid:String}, {new_suid:String}),
            attribute, value,
            replaceAll(unit_id, {old_suid:String}, {new_suid:String}),
            sequence_number, page_ref, raw_excerpt, establishment_type, confidence
        FROM state_events WHERE story_universe_id = {old_suid:String}
        """,
        parameters={"old_pid": old_pid, "new_pid": new_pid, "old_suid": old_suid, "new_suid": new_suid},
    )

    client.client.command(
        """
        INSERT INTO candidate_conflicts
            (id, story_universe_id, entity_id, attribute,
             prior_evidence_unit_id, prior_evidence_excerpt,
             current_evidence_unit_id, current_evidence_excerpt, description)
        SELECT
            replaceAll(id, {old_suid:String}, {new_suid:String}),
            {new_suid:String},
            replaceAll(replaceAll(entity_id, {old_pid:String}, {new_pid:String}), {old_suid:String}, {new_suid:String}),
            attribute,
            replaceAll(prior_evidence_unit_id, {old_suid:String}, {new_suid:String}),
            prior_evidence_excerpt,
            replaceAll(current_evidence_unit_id, {old_suid:String}, {new_suid:String}),
            current_evidence_excerpt, description
        FROM candidate_conflicts WHERE story_universe_id = {old_suid:String}
        """,
        parameters={"old_pid": old_pid, "new_pid": new_pid, "old_suid": old_suid, "new_suid": new_suid},
    )

    client.client.command(
        """
        INSERT INTO investigation_verdicts
            (id, candidate_id, status, severity, explanation, confidence,
             investigation_actions, suggested_fix)
        SELECT
            replaceAll(id, {old_suid:String}, {new_suid:String}),
            replaceAll(candidate_id, {old_suid:String}, {new_suid:String}),
            status, severity, explanation, confidence,
            investigation_actions, suggested_fix
        FROM investigation_verdicts
        WHERE candidate_id IN (
            SELECT id FROM candidate_conflicts WHERE story_universe_id = {old_suid:String}
        )
        """,
        parameters={"old_suid": old_suid, "new_suid": new_suid},
    )

    client.client.command(
        """
        INSERT INTO processing_status
            (story_universe_id, status, total_units, units_extracted,
             candidates_detected, verdicts_complete, error_message)
        SELECT {new_suid:String}, status, total_units, units_extracted,
               candidates_detected, verdicts_complete, error_message
        FROM processing_status WHERE story_universe_id = {old_suid:String}
        """,
        parameters={"old_suid": old_suid, "new_suid": new_suid},
    )


def has_demo_projects(client: ClickHouseClient, user_id: str) -> bool:
    rows = client.client.query(
        "SELECT count() FROM projects WHERE user_id = {uid:String} AND title IN {titles:Array(String)}",
        parameters={"uid": user_id, "titles": _DEMO_TITLES},
    ).result_rows
    return bool(rows and rows[0][0] > 0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--user-id", help="Seed demo projects for one existing user id")
    group.add_argument("--all-users", action="store_true", help="Seed every existing user missing demo projects")
    args = parser.parse_args()

    client = ClickHouseClient()

    if args.user_id:
        targets = [args.user_id]
    else:
        targets = [row[0] for row in client.client.query("SELECT id FROM users").result_rows]

    for user_id in targets:
        if has_demo_projects(client, user_id):
            print(f"skip {user_id}: already has demo projects")
            continue
        seed_demo_projects_for_user(client, user_id)
        print(f"seeded {user_id}")


if __name__ == "__main__":
    main()
