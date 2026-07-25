import os
import sqlite3
import tempfile
import unittest

import importlib.util
import os
import sqlite3
import sys
import tempfile
import unittest

module_path = os.path.join(os.path.dirname(__file__), "..", "main.py")
spec = importlib.util.spec_from_file_location("main", module_path)
main = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = main
spec.loader.exec_module(main)


class MainAppTests(unittest.TestCase):
    def setUp(self):
        self.settings = main.Settings()
        self.settings.operations = ["+"]
        self.settings.addition_bounds = [2.0, 10.0, 2.0, 10.0]
        self.settings.multiplication_bounds = [2.0, 12.0, 2.0, 100.0]

    def test_generate_problem_returns_string_and_numeric_answer(self):
        expr, answer = main.generate_problem(self.settings)
        self.assertIsInstance(expr, str)
        self.assertTrue(expr.count("+") == 1 or expr.count("-") == 1 or expr.count("*") == 1 or expr.count("/") == 1)
        self.assertIsInstance(answer, (int, float))

    def test_settings_do_not_expose_game_mode(self):
        self.assertFalse(hasattr(main.Settings(), "current_game_mode"))

    def test_load_settings_uses_default_operations_when_config_is_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = main.AppState(config_dir=tmpdir, db_path=os.path.join(tmpdir, "runs.db"))
            self.assertEqual(state.settings.operations, ["+", "-", "*", "/"])

    def test_load_settings_clones_defaults_for_legacy_partial_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "settings.json")
            with open(config_path, "w", encoding="utf-8") as handle:
                handle.write('{"operations": ["+", "-"]}')
            state = main.AppState(config_dir=tmpdir, db_path=os.path.join(tmpdir, "runs.db"))
            self.assertEqual(state.settings.operations, ["+", "-", "*", "/"])
            self.assertEqual(state.settings.addition_bounds, main.DEFAULT_SETTINGS["addition_bounds"])

    def test_record_run_persists_and_reads_rows(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "runs.db")
            conn = sqlite3.connect(db_path)
            rows_before = main.get_recent_runs(conn)
            main.record_run(conn, "runs", 5, {"1": "2 + 2"})
            rows_after = main.get_recent_runs(conn)
            self.assertEqual(len(rows_after), len(rows_before) + 1)
            self.assertEqual(rows_after[-1]["score"], 5)


if __name__ == "__main__":
    unittest.main()
