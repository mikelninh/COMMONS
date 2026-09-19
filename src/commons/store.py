from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from commons.models import CaseRecord, FoundingCapabilitySubmission, OutcomeInput, OutcomeRecord


class CaseStore:
    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path or os.getenv("COMMONS_DB_PATH", "commons.db"))
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cases (
                    case_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    record_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS founding_capabilities (
                    submission_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    record_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS outcomes (
                    case_id TEXT PRIMARY KEY,
                    recorded_at TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    FOREIGN KEY(case_id) REFERENCES cases(case_id)
                )
                """
            )

    def save_case(self, record: CaseRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO cases(case_id, created_at, record_json) VALUES (?, ?, ?)",
                (
                    record.case_id,
                    record.created_at.isoformat(),
                    record.model_dump_json(),
                ),
            )

    def get_case(self, case_id: str) -> CaseRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT record_json FROM cases WHERE case_id = ?", (case_id,)
            ).fetchone()
        return CaseRecord.model_validate_json(row["record_json"]) if row else None

    def save_outcome(self, case_id: str, outcome: OutcomeInput) -> OutcomeRecord:
        if self.get_case(case_id) is None:
            raise KeyError(case_id)

        record = OutcomeRecord(case_id=case_id, **outcome.model_dump())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO outcomes(case_id, recorded_at, record_json)
                VALUES (?, ?, ?)
                """,
                (
                    record.case_id,
                    record.recorded_at.isoformat(),
                    record.model_dump_json(),
                ),
            )
        return record

    def get_outcome(self, case_id: str) -> OutcomeRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT record_json FROM outcomes WHERE case_id = ?", (case_id,)
            ).fetchone()
        return OutcomeRecord.model_validate_json(row["record_json"]) if row else None


    def save_founding_capability(
        self,
        submission: FoundingCapabilitySubmission,
    ) -> FoundingCapabilitySubmission:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO founding_capabilities(submission_id, created_at, record_json)
                VALUES (?, ?, ?)
                """,
                (
                    submission.submission_id,
                    submission.created_at.isoformat(),
                    submission.model_dump_json(),
                ),
            )
        return submission

    def list_founding_capabilities(self) -> list[FoundingCapabilitySubmission]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT record_json
                FROM founding_capabilities
                ORDER BY created_at ASC
                """
            ).fetchall()
        return [
            FoundingCapabilitySubmission.model_validate_json(row["record_json"])
            for row in rows
        ]
