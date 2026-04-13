"""SQLite trace store for student mode interactions.

Records each student query, code snippet, error, and agent response
so the teacher mode dashboard can surface analytics.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS student_traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    session_id TEXT NOT NULL,
    student_id TEXT NOT NULL DEFAULT 'student_01',
    query TEXT NOT NULL DEFAULT '',
    code_snippet TEXT NOT NULL DEFAULT '',
    error_traceback TEXT NOT NULL DEFAULT '',
    agent_response TEXT NOT NULL DEFAULT ''
)
"""


class StudentTraceStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._exec(lambda c: c.execute(_SCHEMA))

    def _exec(self, fn):
        with sqlite3.connect(str(self.db_path)) as conn:
            fn(conn)
            conn.commit()

    def record(
        self,
        session_id: str,
        student_id: str = "student_01",
        query: str = "",
        code_snippet: str = "",
        error_traceback: str = "",
        agent_response: str = "",
    ):
        timestamp = datetime.now(timezone.utc).isoformat()

        def _insert(conn):
            conn.execute(
                "INSERT INTO student_traces (timestamp, session_id, student_id, query, code_snippet, error_traceback, agent_response) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (timestamp, session_id, student_id, query, code_snippet, error_traceback, agent_response),
            )

        self._exec(_insert)

    def query_metrics(self) -> dict:
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute("SELECT COUNT(*) FROM student_traces").fetchone()
            total_traces = row[0] if row else 0

            row = conn.execute("SELECT COUNT(DISTINCT session_id) FROM student_traces").fetchone()
            total_sessions = row[0] if row else 0

            avg_queries = total_traces / total_sessions if total_sessions > 0 else 0.0

            rows = conn.execute("SELECT error_traceback FROM student_traces WHERE error_traceback != '' ORDER BY id DESC LIMIT 10").fetchall()
            top_errors = [r[0] for r in rows]

            rows = conn.execute("SELECT id, timestamp, session_id, query, error_traceback FROM student_traces ORDER BY id DESC LIMIT 10").fetchall()
            recent_traces = [
                {"id": r[0], "timestamp": r[1], "session_id": r[2], "query": r[3], "error_traceback": r[4]}
                for r in rows
            ]

        return {
            "total_traces": total_traces,
            "total_sessions": total_sessions,
            "avg_queries_per_session": avg_queries,
            "top_errors": top_errors,
            "recent_traces": recent_traces,
        }
