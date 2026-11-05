#!/usr/bin/env python3
"""Copy PATI's local SQLite database into PostgreSQL.

The destination schema is created by ConversationRepository before rows are
copied. Existing destination rows are preserved, making the operation safe to
retry after a network interruption.
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from ai_tutor.memory.repository import ConversationRepository

TABLES = (
    "users", "sessions", "avatars", "protocol_acceptances", "conversations",
    "messages", "student_profiles", "concept_mastery", "learning_evidence",
    "student_misconceptions", "learning_events", "micro_checks",
    "assessment_attempts", "student_self_reports", "understanding_evaluations",
)


def _source_row_is_valid(source, table: str, row) -> bool:
    """Skip legacy orphan rows instead of aborting an otherwise valid migration.

    A couple of early development databases contain messages whose conversation
    was deleted. PostgreSQL enforces the foreign key that SQLite historically
    allowed, so those rows cannot be copied safely. They are reported and left
    in the SQLite backup for auditability.
    """
    if table == "messages":
        return source.execute(
            "SELECT 1 FROM conversations WHERE conversation_id = ?",
            (row["conversation_id"],),
        ).fetchone() is not None
    return True


def migrate(sqlite_path: Path, postgres_url: str) -> dict[str, int]:
    # Initializing the repository creates the complete PostgreSQL schema.
    destination = ConversationRepository(postgres_url)
    counts: dict[str, int] = {}
    with sqlite3.connect(str(sqlite_path)) as source, destination._connect() as target:
        source.row_factory = sqlite3.Row
        for table in TABLES:
            exists = source.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
            if not exists:
                counts[table] = 0
                continue
            rows = source.execute(f"SELECT * FROM {table}").fetchall()
            if not rows:
                counts[table] = 0
                continue
            columns = list(rows[0].keys())
            names = ",".join(columns)
            placeholders = ",".join("%s" for _ in columns)
            statement = f"INSERT INTO {table} ({names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
            skipped = 0
            for row in rows:
                if not _source_row_is_valid(source, table, row):
                    skipped += 1
                    continue
                target.execute(statement, tuple(row[column] for column in columns))
            counts[table] = len(rows) - skipped
            if skipped:
                counts[f"{table}_skipped_orphans"] = skipped
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite", required=True, type=Path)
    parser.add_argument("--postgres-url", required=True)
    args = parser.parse_args()
    if not args.sqlite.exists():
        raise SystemExit(f"No existe la base SQLite: {args.sqlite}")
    counts = migrate(args.sqlite, args.postgres_url)
    for table, count in counts.items():
        print(f"{table}: {count} filas procesadas")


if __name__ == "__main__":
    main()
