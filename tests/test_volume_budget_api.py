"""Integration test suite for /api/volumes and /api/budget HTTP endpoints."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.backend import db as db_mod
from app.backend.server import LauncherHandler


class TestVolumeBudgetApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.isolated_runtime = Path(cls.temp_dir.name)
        cls.db_path = cls.isolated_runtime / "test_api.sqlite"

        cls.patch_db = patch("app.backend.db.DB_PATH", cls.db_path)
        cls.patch_dir = patch("app.backend.db.DB_DIR", cls.isolated_runtime)
        cls.patch_db.start()
        cls.patch_dir.start()

        db_mod.init_db()

        # Seed an object into database
        conn = db_mod.get_connection()
        try:
            # Create a sample project folder with a dummy PDF
            cls.proj_dir = cls.isolated_runtime / "sample_project"
            cls.proj_dir.mkdir(parents=True, exist_ok=True)
            
            conn.execute(
                "INSERT INTO roots (id, path, project_name) VALUES (?, ?, ?)",
                (
                    1,
                    str(cls.proj_dir),
                    "БЦ на Энгельса Тест",
                ),
            )
            conn.commit()
        finally:
            conn.close()

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), LauncherHandler)
        cls.port = cls.server.server_port
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.server.shutdown()
            cls.server.server_close()
        except Exception:
            pass
        cls.patch_db.stop()
        cls.patch_dir.stop()
        try:
            cls.temp_dir.cleanup()
        except Exception:
            pass

    def _url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def test_01_api_volumes_missing_id(self):
        req = urllib.request.Request(self._url("/api/volumes"))
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 400)

    def test_02_api_volumes_not_found_object(self):
        req = urllib.request.Request(self._url("/api/volumes?id=non_existent_id"))
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 404)

    def test_03_api_volumes_valid_object(self):
        req = urllib.request.Request(self._url("/api/volumes?id=1"))
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "ok")
            self.assertEqual(data.get("root_id"), 1)
            self.assertIn("reconciliations", data)

    def test_04_api_budget_valid_object(self):
        req = urllib.request.Request(self._url("/api/budget?id=1"))
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "ok")
            self.assertEqual(data.get("root_id"), 1)
            self.assertIn("estimate", data)

    def test_05_api_budget_passport_html(self):
        req = urllib.request.Request(self._url("/api/budget/passport?id=1"))
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("text/html", resp.headers.get("Content-Type", ""))
            content = resp.read().decode("utf-8")
            self.assertIn("<!doctype html>", content.lower())
            self.assertIn("Паспорт и спецификация фасадов", content)

    def test_06_api_budget_export_csv(self):
        req = urllib.request.Request(self._url("/api/budget/export-csv?id=1"))
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("text/csv", resp.headers.get("Content-Type", ""))
            raw = resp.read()
            self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))  # UTF-8 BOM
            text = raw.decode("utf-8-sig")
            self.assertIn("Раздел 1", text)


if __name__ == "__main__":
    unittest.main()
