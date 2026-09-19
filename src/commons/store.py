from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from commons.civic_case import PublicSpaceCase
from commons.models import CaseRecord, FoundingCapabilitySubmission, NeedRequest, OutcomeInput, OutcomeRecord


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
                CREATE TABLE IF NOT EXISTS needs (
                    need_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    record_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS civic_public_space_cases (
                    case_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
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


    def save_need(self, need: NeedRequest) -> NeedRequest:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO needs(need_id, created_at, record_json)
                VALUES (?, ?, ?)
                """,
                (
                    need.need_id,
                    need.created_at.isoformat(),
                    need.model_dump_json(),
                ),
            )
        return need

    def list_needs(self) -> list[NeedRequest]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT record_json FROM needs ORDER BY created_at ASC"
            ).fetchall()
        return [NeedRequest.model_validate_json(row["record_json"]) for row in rows]


    def save_public_space_case(self, record: PublicSpaceCase) -> PublicSpaceCase:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO civic_public_space_cases(case_id, created_at, updated_at, record_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(case_id) DO UPDATE SET
                    updated_at = excluded.updated_at,
                    record_json = excluded.record_json
                """,
                (
                    record.case_id,
                    record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                    record.model_dump_json(),
                ),
            )
        return record

    def get_public_space_case(self, case_id: str) -> PublicSpaceCase | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT record_json FROM civic_public_space_cases WHERE case_id = ?",
                (case_id,),
            ).fetchone()
        return PublicSpaceCase.model_validate_json(row["record_json"]) if row else None

    def list_public_space_cases(self) -> list[PublicSpaceCase]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT record_json
                FROM civic_public_space_cases
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [
            PublicSpaceCase.model_validate_json(row["record_json"])
            for row in rows
        ]
