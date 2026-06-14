from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "argument_trainer.db"


def _connect(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_database(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with closing(_connect(db_path)) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS training_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_claim TEXT NOT NULL,
                    opponent_strength TEXT NOT NULL,
                    initial_analysis_json TEXT NOT NULL,
                    analysis_mode TEXT NOT NULL DEFAULT 'rule',
                    final_score_json TEXT,
                    final_rewrite TEXT,
                    is_completed INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            existing_columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(training_sessions)"
                ).fetchall()
            }
            migrations = {
                "final_score_json": "TEXT",
                "final_rewrite": "TEXT",
                "is_completed": "INTEGER NOT NULL DEFAULT 0",
                "analysis_mode": "TEXT NOT NULL DEFAULT 'rule'",
            }
            for column_name, column_type in migrations.items():
                if column_name not in existing_columns:
                    connection.execute(
                        f"ALTER TABLE training_sessions "
                        f"ADD COLUMN {column_name} {column_type}"
                    )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS debate_turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    turn_number INTEGER NOT NULL CHECK (turn_number BETWEEN 1 AND 5),
                    opponent_question TEXT NOT NULL,
                    question_type TEXT NOT NULL,
                    why_ask TEXT NOT NULL,
                    user_answer TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES training_sessions(id)
                        ON DELETE CASCADE,
                    UNIQUE (session_id, turn_number)
                )
                """
            )


def create_training_session(
    original_claim: str,
    opponent_strength: str,
    initial_analysis: dict[str, Any],
    db_path: str | Path = DEFAULT_DB_PATH,
    analysis_mode: str = "rule",
) -> int:
    init_database(db_path)
    with closing(_connect(db_path)) as connection:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO training_sessions (
                    original_claim,
                    opponent_strength,
                    initial_analysis_json,
                    analysis_mode
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    original_claim.strip(),
                    opponent_strength,
                    json.dumps(initial_analysis, ensure_ascii=False),
                    analysis_mode,
                ),
            )
            return int(cursor.lastrowid)


def _deserialize_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    result = dict(row)
    result["initial_analysis"] = json.loads(result.pop("initial_analysis_json"))
    final_score_json = result.pop("final_score_json", None)
    result["final_score"] = (
        json.loads(final_score_json) if final_score_json else None
    )
    result["is_completed"] = bool(result.get("is_completed", 0))
    return result


def list_training_sessions(
    db_path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    init_database(db_path)
    with closing(_connect(db_path)) as connection:
        rows = connection.execute(
            "SELECT * FROM training_sessions ORDER BY id DESC"
        ).fetchall()
    return [_deserialize_row(row) for row in rows]


def get_training_session(
    session_id: int,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any] | None:
    init_database(db_path)
    with closing(_connect(db_path)) as connection:
        row = connection.execute(
            "SELECT * FROM training_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    return _deserialize_row(row)


def delete_training_session(
    session_id: int,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> bool:
    init_database(db_path)
    with closing(_connect(db_path)) as connection:
        with connection:
            connection.execute(
                "DELETE FROM debate_turns WHERE session_id = ?",
                (session_id,),
            )
            cursor = connection.execute(
                "DELETE FROM training_sessions WHERE id = ?",
                (session_id,),
            )
            return cursor.rowcount > 0


def create_debate_turn(
    session_id: int,
    turn_number: int,
    opponent_question: str,
    question_type: str,
    why_ask: str,
    user_answer: str,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> int:
    init_database(db_path)
    if not 1 <= turn_number <= 5:
        raise ValueError("追问轮次必须在 1 到 5 之间。")
    if not user_answer.strip():
        raise ValueError("回答不能为空。")

    with closing(_connect(db_path)) as connection:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO debate_turns (
                    session_id,
                    turn_number,
                    opponent_question,
                    question_type,
                    why_ask,
                    user_answer
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    turn_number,
                    opponent_question.strip(),
                    question_type.strip(),
                    why_ask.strip(),
                    user_answer.strip(),
                ),
            )
            return int(cursor.lastrowid)


def get_debate_turns(
    session_id: int,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    init_database(db_path)
    with closing(_connect(db_path)) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM debate_turns
            WHERE session_id = ?
            ORDER BY turn_number ASC
            """,
            (session_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def save_training_score(
    session_id: int,
    score_result: dict[str, Any],
    db_path: str | Path = DEFAULT_DB_PATH,
) -> bool:
    init_database(db_path)
    final_rewrite = str(score_result.get("final_rewrite", "")).strip()
    if not final_rewrite:
        raise ValueError("最终严谨表达不能为空。")

    with closing(_connect(db_path)) as connection:
        turn_count = connection.execute(
            "SELECT COUNT(*) FROM debate_turns WHERE session_id = ?",
            (session_id,),
        ).fetchone()[0]
        if turn_count != 5:
            raise ValueError("必须完成 5 轮追问后才能保存评分。")

        with connection:
            cursor = connection.execute(
                """
                UPDATE training_sessions
                SET final_score_json = ?,
                    final_rewrite = ?,
                    is_completed = 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    json.dumps(score_result, ensure_ascii=False),
                    final_rewrite,
                    session_id,
                ),
            )
            return cursor.rowcount > 0
