"""One-time data migration: copy every row from the local ClickHouse
(docker-compose, storytrace-clickhouse-1) into a ClickHouse Cloud instance.

Local connection is hardcoded to the docker-compose defaults (localhost:8123,
default/admin); Cloud connection is read from the environment the same way
ClickHouseClient does, so run this with the target Cloud values already
exported (e.g. `set -a; source .env; set +a` first).

Usage: python3 -m scripts.migrate_to_cloud
"""

import os

import clickhouse_connect

from backend.clickhouse.client import ClickHouseClient

_TABLES = [
    "users",
    "projects",
    "project_versions",
    "narrative_units",
    "entities",
    "state_events",
    "candidate_conflicts",
    "investigation_verdicts",
    "processing_status",
]


def main() -> None:
    local = clickhouse_connect.get_client(
        host="localhost", port=8123, user="default", password="admin", database="storytrace"
    )
    cloud = ClickHouseClient().client

    for table in _TABLES:
        result = local.query(f"SELECT * FROM {table}")
        rows = result.result_rows
        columns = result.column_names
        if not rows:
            print(f"{table}: 0 rows, skipping")
            continue
        cloud.insert(table, rows, column_names=columns)
        cloud_count = cloud.command(f"SELECT count() FROM {table}")
        print(f"{table}: copied {len(rows)} rows (cloud now has {cloud_count})")


if __name__ == "__main__":
    main()
