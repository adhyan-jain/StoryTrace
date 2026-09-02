import os
import clickhouse_connect
from pydantic import BaseModel
from typing import List, Any

class ClickHouseClient:
    def __init__(self):
        host = os.environ.get("CLICKHOUSE_HOST", "localhost")
        port = int(os.environ.get("CLICKHOUSE_PORT", "8123"))
        user = os.environ.get("CLICKHOUSE_USER", "default")
        password = os.environ.get("CLICKHOUSE_PASSWORD", "admin")
        database = os.environ.get("CLICKHOUSE_DB", "storytrace")

        self.client = clickhouse_connect.get_client(
            host=host, port=port, user=user, password=password, database=database
        )

    # -- Auth / projects / versions -----------------------------------

    def get_user_by_email(self, email: str) -> Any:
        rows = self.client.query(
            "SELECT id, email, password_hash, created_at FROM users WHERE email = {email:String} LIMIT 1",
            parameters={"email": email},
        ).result_rows
        return rows[0] if rows else None

    def create_user(self, user_id: str, email: str, password_hash: str) -> None:
        self.client.insert(
            "users",
            [[user_id, email, password_hash]],
            column_names=["id", "email", "password_hash"],
        )

    def get_user_by_id(self, user_id: str) -> Any:
        rows = self.client.query(
            "SELECT id, email, created_at FROM users WHERE id = {id:String} LIMIT 1",
            parameters={"id": user_id},
        ).result_rows
        return rows[0] if rows else None

    def create_project(self, project_id: str, user_id: str, title: str) -> None:
        self.client.insert(
            "projects",
            [[project_id, user_id, title]],
            column_names=["id", "user_id", "title"],
        )

    def get_project(self, project_id: str) -> Any:
        rows = self.client.query(
            "SELECT id, user_id, title, created_at FROM projects WHERE id = {id:String} LIMIT 1",
            parameters={"id": project_id},
        ).result_rows
        return rows[0] if rows else None

    def list_projects(self, user_id: str) -> List[Any]:
        return self.client.query(
            "SELECT id, user_id, title, created_at FROM projects WHERE user_id = {user_id:String} ORDER BY created_at DESC",
            parameters={"user_id": user_id},
        ).result_rows

    def create_project_version(self, version_id: str, project_id: str, version_number: int, document_title: str) -> None:
        self.client.insert(
            "project_versions",
            [[version_id, project_id, version_number, document_title]],
            column_names=["id", "project_id", "version_number", "document_title"],
        )

    def list_project_versions(self, project_id: str) -> List[Any]:
        return self.client.query(
            """SELECT id, project_id, version_number, document_title, created_at
               FROM project_versions WHERE project_id = {project_id:String}
               ORDER BY version_number ASC""",
            parameters={"project_id": project_id},
        ).result_rows

    def get_latest_version_number(self, project_id: str) -> int:
        rows = self.client.query(
            "SELECT max(version_number) FROM project_versions WHERE project_id = {project_id:String}",
            parameters={"project_id": project_id},
        ).result_rows
        return rows[0][0] if rows and rows[0][0] is not None else 0

    def upsert_processing_status(
        self,
        story_universe_id: str,
        status: str,
        total_units: int = 0,
        units_extracted: int = 0,
        candidates_detected: int = 0,
        verdicts_complete: int = 0,
        error_message: str = "",
    ) -> None:
        """ReplacingMergeTree keyed on story_universe_id -- each call inserts a
        new row that supersedes the prior one (on the next merge) rather than
        mutating in place, which is the standard ClickHouse pattern for a
        small, frequently-updated status row."""
        self.client.insert(
            "processing_status",
            [[story_universe_id, status, total_units, units_extracted, candidates_detected, verdicts_complete, error_message]],
            column_names=[
                "story_universe_id", "status", "total_units", "units_extracted",
                "candidates_detected", "verdicts_complete", "error_message",
            ],
        )

    def insert_narrative_units(self, units: List[BaseModel]):
        if not units:
            return

        data = [
            [
                u.unit_id, u.story_universe_id, u.document_id, u.unit_type,
                u.sequence_number, u.title, u.raw_text, u.page_start, u.page_end
            ]
            for u in units
        ]

        self.client.insert(
            'narrative_units',
            data,
            column_names=['id', 'story_universe_id', 'document_id', 'unit_type', 'sequence_number', 'title', 'text', 'start_page', 'end_page']
        )

    def insert_entities(self, entities: List[Any]):
        if not entities:
            return

        data = [
            [
                e.id, e.story_universe_id, e.type, e.name, e.aliases
            ]
            for e in entities
        ]

        self.client.insert(
            'entities',
            data,
            column_names=['id', 'story_universe_id', 'type', 'name', 'aliases']
        )

    def insert_state_events(self, events: List[Any]):
        if not events:
            return

        data = [
            [
                e.id, e.story_universe_id, e.entity_id, e.attribute,
                e.value, e.unit_id, e.sequence_number, e.page_ref,
                e.raw_excerpt, e.establishment_type, e.confidence
            ]
            for e in events
        ]

        self.client.insert(
            'state_events',
            data,
            column_names=['id', 'story_universe_id', 'entity_id', 'attribute', 'value', 'unit_id', 'sequence_number', 'page_ref', 'raw_excerpt', 'establishment_type', 'confidence']
        )

    def insert_candidate_conflicts(self, conflicts: List[Any]):
        if not conflicts:
            return

        data = [
            [
                c.id, c.story_universe_id, c.entity_id, c.attribute,
                c.prior_evidence_unit_id, c.prior_evidence_excerpt,
                c.current_evidence_unit_id, c.current_evidence_excerpt,
                c.description
            ]
            for c in conflicts
        ]

        self.client.insert(
            'candidate_conflicts',
            data,
            column_names=['id', 'story_universe_id', 'entity_id', 'attribute', 'prior_evidence_unit_id', 'prior_evidence_excerpt', 'current_evidence_unit_id', 'current_evidence_excerpt', 'description']
        )

    def insert_investigation_verdicts(self, verdicts: List[Any]):
        if not verdicts:
            return

        data = [
            [
                v.id, v.candidate_id, v.status, v.severity,
                v.explanation, v.confidence, v.investigation_actions, v.suggested_fix
            ]
            for v in verdicts
        ]

        self.client.insert(
            'investigation_verdicts',
            data,
            column_names=['id', 'candidate_id', 'status', 'severity', 'explanation', 'confidence', 'investigation_actions', 'suggested_fix']
        )
