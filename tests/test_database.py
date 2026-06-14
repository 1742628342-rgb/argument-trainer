import sqlite3
import tempfile
import unittest
from pathlib import Path

from modules.database import (
    create_debate_turn,
    create_training_session,
    delete_training_session,
    get_debate_turns,
    get_training_session,
    init_database,
    list_training_sessions,
    save_training_score,
)


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        init_database(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_list_get_and_delete_session(self):
        analysis = {
            "supporting_reasons": ["理由"],
            "opposing_reasons": ["反对"],
            "conditions": ["条件"],
            "concept_shift_risks": ["风险"],
            "rigorous_expression": "表达",
            "detected_features": {},
        }

        session_id = create_training_session(
            "努力可能提高成功概率。",
            "正常",
            analysis,
            self.db_path,
        )

        rows = list_training_sessions(self.db_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], session_id)

        row = get_training_session(session_id, self.db_path)
        self.assertEqual(row["original_claim"], "努力可能提高成功概率。")
        self.assertEqual(row["initial_analysis"], analysis)
        self.assertTrue(row["created_at"])
        self.assertTrue(row["updated_at"])
        self.assertEqual(row["analysis_mode"], "rule")

        self.assertTrue(delete_training_session(session_id, self.db_path))
        self.assertIsNone(get_training_session(session_id, self.db_path))
        self.assertFalse(delete_training_session(session_id, self.db_path))

    def test_creates_missing_data_directory_and_database_file(self):
        nested_path = Path(self.temp_dir.name) / "missing" / "data" / "new.db"

        self.assertFalse(nested_path.parent.exists())
        init_database(nested_path)

        self.assertTrue(nested_path.parent.is_dir())
        self.assertTrue(nested_path.is_file())
        connection = sqlite3.connect(nested_path)
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        connection.close()
        self.assertIn("training_sessions", tables)
        self.assertIn("debate_turns", tables)

    def test_create_list_and_cascade_delete_debate_turns(self):
        session_id = create_training_session(
            "所有成功都由努力决定。",
            "正常",
            {"supporting_reasons": [], "opposing_reasons": []},
            self.db_path,
        )

        turn_id = create_debate_turn(
            session_id=session_id,
            turn_number=1,
            opponent_question="观点中的“成功”具体是什么意思？",
            question_type="定义追问",
            why_ask="先统一核心概念。",
            user_answer="成功是达到自己设定的目标。",
            db_path=self.db_path,
        )

        turns = get_debate_turns(session_id, self.db_path)
        self.assertEqual(len(turns), 1)
        self.assertEqual(turns[0]["id"], turn_id)
        self.assertEqual(turns[0]["turn_number"], 1)
        self.assertEqual(turns[0]["user_answer"], "成功是达到自己设定的目标。")

        delete_training_session(session_id, self.db_path)
        self.assertEqual(get_debate_turns(session_id, self.db_path), [])

    def test_migrates_existing_training_sessions_table(self):
        legacy_path = Path(self.temp_dir.name) / "legacy.db"
        connection = sqlite3.connect(legacy_path)
        connection.execute(
            """
            CREATE TABLE training_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_claim TEXT NOT NULL,
                opponent_strength TEXT NOT NULL,
                initial_analysis_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            INSERT INTO training_sessions (
                original_claim, opponent_strength, initial_analysis_json
            ) VALUES ('旧观点', '正常', '{}')
            """
        )
        connection.commit()
        connection.close()

        init_database(legacy_path)

        connection = sqlite3.connect(legacy_path)
        columns = {
            row[1]: row
            for row in connection.execute(
                "PRAGMA table_info(training_sessions)"
            ).fetchall()
        }
        original_claim = connection.execute(
            "SELECT original_claim FROM training_sessions"
        ).fetchone()[0]
        connection.close()

        self.assertIn("final_score_json", columns)
        self.assertIn("final_rewrite", columns)
        self.assertIn("is_completed", columns)
        self.assertIn("analysis_mode", columns)
        self.assertEqual(original_claim, "旧观点")

    def test_saves_selected_analysis_mode(self):
        session_id = create_training_session(
            "观点",
            "正常",
            {"rigorous_expression": "改写"},
            self.db_path,
            analysis_mode="gemini",
        )

        session = get_training_session(session_id, self.db_path)
        self.assertEqual(session["analysis_mode"], "gemini")

    def test_saves_score_only_after_five_turns(self):
        session_id = create_training_session(
            "所有成功都由努力决定。",
            "正常",
            {"rigorous_expression": "更严谨表达"},
            self.db_path,
        )
        score = {
            "scores": {"concept_clarity": 7},
            "total_score": 36,
            "main_problem": "边界不足",
            "strongest_part": "有反例意识",
            "next_training_advice": "补充适用范围",
            "final_rewrite": "努力可能提高部分情境下的成功概率。",
        }

        with self.assertRaises(ValueError):
            save_training_score(session_id, score, self.db_path)

        for turn_number in range(1, 6):
            create_debate_turn(
                session_id,
                turn_number,
                f"问题 {turn_number}",
                f"类型 {turn_number}",
                "目的",
                f"回答 {turn_number}",
                self.db_path,
            )

        self.assertTrue(save_training_score(session_id, score, self.db_path))
        session = get_training_session(session_id, self.db_path)
        self.assertEqual(session["final_score"], score)
        self.assertEqual(session["final_rewrite"], score["final_rewrite"])
        self.assertTrue(session["is_completed"])


if __name__ == "__main__":
    unittest.main()
