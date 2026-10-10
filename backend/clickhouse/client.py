import os
import json
import re
import sqlite3
import logging
from typing import List, Any, Optional
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("storytrace.db")

class SQLQueryResult:
    def __init__(self, result_rows):
        self.result_rows = result_rows

class SQLClientCompat:
    def __init__(self, db_type="sqlite", conn=None):
        self.db_type = db_type
        self.conn = conn
        self.param_style = "?" if db_type == "sqlite" else "%s"
        self._init_tables()

    def _init_tables(self):
        cur = self.conn.cursor()
        tables = [
            """CREATE TABLE IF NOT EXISTS narrative_units (
                id TEXT PRIMARY KEY, story_universe_id TEXT, document_id TEXT, unit_type TEXT,
                sequence_number INTEGER, title TEXT, text TEXT, start_page INTEGER, end_page INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
            """CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY, story_universe_id TEXT, type TEXT, name TEXT, aliases TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
            """CREATE TABLE IF NOT EXISTS state_events (
                id TEXT PRIMARY KEY, story_universe_id TEXT, entity_id TEXT, attribute TEXT, value TEXT,
                unit_id TEXT, sequence_number INTEGER, page_ref INTEGER, raw_excerpt TEXT,
                establishment_type TEXT, confidence REAL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
            """CREATE TABLE IF NOT EXISTS candidate_conflicts (
                id TEXT PRIMARY KEY, story_universe_id TEXT, entity_id TEXT, attribute TEXT,
                prior_evidence_unit_id TEXT, prior_evidence_excerpt TEXT,
                current_evidence_unit_id TEXT, current_evidence_excerpt TEXT,
                description TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
            """CREATE TABLE IF NOT EXISTS processing_status (
                story_universe_id TEXT PRIMARY KEY, status TEXT, total_units INTEGER, units_extracted INTEGER,
                candidates_detected INTEGER, verdicts_complete INTEGER, error_message TEXT DEFAULT '',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
            """CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY, email TEXT UNIQUE, password_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
            """CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY, user_id TEXT, title TEXT, demo_source_id TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
            """CREATE TABLE IF NOT EXISTS project_versions (
                id TEXT PRIMARY KEY, project_id TEXT, version_number INTEGER, document_title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
            """CREATE TABLE IF NOT EXISTS investigation_verdicts (
                id TEXT PRIMARY KEY, candidate_id TEXT, status TEXT, severity TEXT,
                explanation TEXT, confidence REAL, investigation_actions TEXT, suggested_fix TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );"""
        ]
        for stmt in tables:
            cur.execute(stmt)
        self.conn.commit()

    def translate_query(self, sql):
        if 'ARRAY JOIN [c.prior_evidence_unit_id' in sql:
            sql = '''
            SELECT c.id, v.severity, c.prior_evidence_unit_id AS unit_id, c.prior_evidence_excerpt AS excerpt, v.id AS verdict_id
            FROM candidate_conflicts c
            LEFT JOIN investigation_verdicts v ON c.id = v.candidate_id
            WHERE c.story_universe_id = {sid:String}
            UNION ALL
            SELECT c.id, v.severity, c.current_evidence_unit_id AS unit_id, c.current_evidence_excerpt AS excerpt, v.id AS verdict_id
            FROM candidate_conflicts c
            LEFT JOIN investigation_verdicts v ON c.id = v.candidate_id
            WHERE c.story_universe_id = {sid:String}
            '''
        sql = re.sub(r'ALTER TABLE\s+([a-zA-Z0-9_]+)\s+UPDATE\s+(.+?)\s+WHERE\s+(.+)', r'UPDATE \1 SET \2 WHERE \3', sql, flags=re.IGNORECASE)
        sql = re.sub(r'ALTER TABLE\s+([a-zA-Z0-9_]+)\s+DELETE\s+WHERE\s+(.+)', r'DELETE FROM \1 WHERE \2', sql, flags=re.IGNORECASE)
        sql = sql.replace('lagInFrame(', 'LAG(')
        if self.db_type == 'sqlite':
            sql = sql.replace('groupArray(', 'json_group_array(')
        else:
            sql = sql.replace('groupArray(', 'ARRAY_AGG(')
        sql = re.sub(r'startsWith\(([a-zA-Z0-9_\.]+),\s*\'([^\']+)\'\)', r"\1 LIKE '\2%'", sql)
        return sql

    def _convert_params(self, sql, parameters):
        if not parameters:
            return sql, []
        param_list = []
        def replacer(match):
            pname = match.group(1)
            ptype = match.group(2)
            val = parameters.get(pname)
            if ptype.startswith('Array'):
                if not val:
                    return "('__EMPTY__')"
                placeholders = ', '.join([self.param_style] * len(val))
                param_list.extend(val)
                return f'({placeholders})'
            else:
                param_list.append(val)
                return self.param_style

        conv_sql = re.sub(r'\{([a-zA-Z0-9_]+):([^\}]+)\}', replacer, sql)
        return conv_sql, param_list

    def query(self, sql, parameters=None):
        tsql = self.translate_query(sql)
        csql, params = self._convert_params(tsql, parameters)
        cur = self.conn.cursor()
        cur.execute(csql, params)
        rows = cur.fetchall()
        processed = []
        for r in rows:
            p_row = list(r)
            for i in range(len(p_row)):
                if isinstance(p_row[i], str) and (p_row[i].startswith('[') or p_row[i].startswith('{')):
                    try:
                        p_row[i] = json.loads(p_row[i])
                    except Exception:
                        pass
            processed.append(tuple(p_row))
        return SQLQueryResult(processed)

    def command(self, sql, parameters=None):
        tsql = self.translate_query(sql)
        csql, params = self._convert_params(tsql, parameters)
        cur = self.conn.cursor()
        cur.execute(csql, params)
        self.conn.commit()

    def insert(self, table, data, column_names=None):
        if not data:
            return
        cur = self.conn.cursor()
        if column_names:
            cols_str = ', '.join(column_names)
            placeholders = ', '.join([self.param_style] * len(column_names))
            sql = f'INSERT INTO {table} ({cols_str}) VALUES ({placeholders})'
        else:
            placeholders = ', '.join([self.param_style] * len(data[0]))
            sql = f'INSERT INTO {table} VALUES ({placeholders})'
        
        cleaned_data = []
        for row in data:
            c_row = []
            for item in row:
                if isinstance(item, (list, dict)):
                    c_row.append(json.dumps(item))
                else:
                    c_row.append(item)
            cleaned_data.append(c_row)
        
        if table == 'processing_status':
            if self.db_type == 'sqlite':
                updates = ', '.join([f'{col}=excluded.{col}' for col in column_names if col != 'story_universe_id'])
                sql = f'INSERT INTO {table} ({cols_str}) VALUES ({placeholders}) ON CONFLICT(story_universe_id) DO UPDATE SET {updates}, updated_at=CURRENT_TIMESTAMP'
            else:
                updates = ', '.join([f'{col}=EXCLUDED.{col}' for col in column_names if col != 'story_universe_id'])
                sql = f'INSERT INTO {table} ({cols_str}) VALUES ({placeholders}) ON CONFLICT(story_universe_id) DO UPDATE SET {updates}, updated_at=CURRENT_TIMESTAMP'
        elif table == 'users':
            if self.db_type == 'sqlite':
                sql = f'INSERT INTO {table} ({cols_str}) VALUES ({placeholders}) ON CONFLICT(email) DO UPDATE SET password_hash=excluded.password_hash'
            else:
                sql = f'INSERT INTO {table} ({cols_str}) VALUES ({placeholders}) ON CONFLICT(email) DO UPDATE SET password_hash=EXCLUDED.password_hash'

        cur.executemany(sql, cleaned_data)
        self.conn.commit()


_SQLITE_SHARED_CONN = None

def _get_sqlite_connection():
    global _SQLITE_SHARED_CONN
    if _SQLITE_SHARED_CONN is None:
        db_path = os.environ.get("SQLITE_DB_PATH")
        if not db_path:
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "storytrace.db")
            try:
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
            except Exception:
                db_path = "/tmp/storytrace.db"
        _SQLITE_SHARED_CONN = sqlite3.connect(db_path, check_same_thread=False)
    return _SQLITE_SHARED_CONN


class ClickHouseClient:
    def __init__(self):
        provider = os.environ.get("DB_PROVIDER", "").strip().lower()
        
        # If DB_PROVIDER explicitly set to postgres or cloudsql
        if provider in ("postgres", "cloudsql") or os.environ.get("POSTGRES_HOST") or os.environ.get("DATABASE_URL"):
            try:
                import psycopg2
                host = os.environ.get("POSTGRES_HOST", os.environ.get("DB_HOST", "localhost"))
                port = int(os.environ.get("POSTGRES_PORT", os.environ.get("DB_PORT", "5432")))
                user = os.environ.get("POSTGRES_USER", os.environ.get("DB_USER", "postgres"))
                password = os.environ.get("POSTGRES_PASSWORD", os.environ.get("DB_PASSWORD", ""))
                database = os.environ.get("POSTGRES_DB", os.environ.get("DB_NAME", "storytrace"))
                conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=database)
                self.client = SQLClientCompat(db_type="postgres", conn=conn)
                self.provider = "postgres"
                return
            except Exception as e:
                logger.warning(f"PostgreSQL connection failed: {e}. Falling back to SQLite/ClickHouse.")

        if provider == "sqlite":
            conn = _get_sqlite_connection()
            self.client = SQLClientCompat(db_type="sqlite", conn=conn)
            self.provider = "sqlite"
            return

        # Default or explicit clickhouse
        if provider == "clickhouse" or not provider:
            try:
                import clickhouse_connect
                host = os.environ.get("CLICKHOUSE_HOST", "localhost")
                port = int(os.environ.get("CLICKHOUSE_PORT", "8123"))
                user = os.environ.get("CLICKHOUSE_USER", "default")
                password = os.environ.get("CLICKHOUSE_PASSWORD")
                if password:
                    secure = os.environ.get("CLICKHOUSE_SECURE", "false").strip().lower() in ("1", "true", "yes")
                    database = os.environ.get("CLICKHOUSE_DB", "storytrace")
                    self.client = clickhouse_connect.get_client(
                        host=host, port=port, user=user, password=password, database=database, secure=secure,
                        connect_timeout=10, send_receive_timeout=30,
                    )
                    self.provider = "clickhouse"
                    return
            except Exception as e:
                logger.warning(f"ClickHouse connection failed: {e}. Falling back to SQLite.")

        # Fallback to SQLite
        conn = _get_sqlite_connection()
        self.client = SQLClientCompat(db_type="sqlite", conn=conn)
        self.provider = "sqlite"

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

    def get_earliest_user_id_for_email(self, email: str) -> Any:
        rows = self.client.query(
            "SELECT id FROM users WHERE email = {email:String} "
            "ORDER BY created_at ASC, id ASC LIMIT 1",
            parameters={"email": email},
        ).result_rows
        return rows[0][0] if rows else None

    def get_user_by_id(self, user_id: str) -> Any:
        rows = self.client.query(
            "SELECT id, email, created_at FROM users WHERE id = {id:String} LIMIT 1",
            parameters={"id": user_id},
        ).result_rows
        return rows[0] if rows else None

    def create_project(self, project_id: str, user_id: str, title: str, demo_source_id: str = "") -> None:
        self.client.insert(
            "projects",
            [[project_id, user_id, title, demo_source_id]],
            column_names=["id", "user_id", "title", "demo_source_id"],
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

    def get_version_title(self, story_universe_id: str) -> Any:
        rows = self.client.query(
            "SELECT document_title FROM project_versions WHERE id = {id:String} LIMIT 1",
            parameters={"id": story_universe_id},
        ).result_rows
        return rows[0][0] if rows else None

    def rename_project_version(self, story_universe_id: str, title: str) -> None:
        self.client.command(
            "ALTER TABLE project_versions UPDATE document_title = {title:String} WHERE id = {id:String}",
            parameters={"title": title, "id": story_universe_id},
        )

    def rename_project(self, project_id: str, title: str) -> None:
        self.client.command(
            "ALTER TABLE projects UPDATE title = {title:String} WHERE id = {id:String}",
            parameters={"title": title, "id": project_id},
        )

    def delete_project(self, project_id: str) -> None:
        story_universe_ids = [v[0] for v in self.list_project_versions(project_id)]
        for story_universe_id in story_universe_ids:
            for table in ("narrative_units", "entities", "state_events", "candidate_conflicts", "processing_status"):
                self.client.command(
                    f"ALTER TABLE {table} DELETE WHERE story_universe_id = {{sid:String}}",
                    parameters={"sid": story_universe_id},
                )
            self.client.command(
                "ALTER TABLE investigation_verdicts DELETE WHERE candidate_id LIKE {prefix:String}",
                parameters={"prefix": f"{story_universe_id}_%"},
            )
        self.client.command(
            "ALTER TABLE project_versions DELETE WHERE project_id = {project_id:String}",
            parameters={"project_id": project_id},
        )
        self.client.command(
            "ALTER TABLE projects DELETE WHERE id = {project_id:String}",
            parameters={"project_id": project_id},
        )

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
        column_names = ['id', 'story_universe_id', 'document_id', 'unit_type', 'sequence_number', 'title', 'text', 'start_page', 'end_page']
        self.client.insert('narrative_units', data, column_names=column_names)

    def _retry_call(self, fn, *args, **kwargs):
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(1)

    def insert_entities(self, entities: List[Any]):
        if not entities:
            return
        data = [
            [e.id, e.story_universe_id, e.type, e.name, e.aliases]
            for e in entities
        ]
        self.client.insert(
            'entities', data, column_names=['id', 'story_universe_id', 'type', 'name', 'aliases']
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
            'state_events', data,
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
            'candidate_conflicts', data,
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
            'investigation_verdicts', data,
            column_names=['id', 'candidate_id', 'status', 'severity', 'explanation', 'confidence', 'investigation_actions', 'suggested_fix']
        )
