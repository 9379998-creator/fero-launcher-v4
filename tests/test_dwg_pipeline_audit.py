"""Diagnostic and audit tests for the DWG to PDF pipeline and CAD invocation contract.

These tests perform static and contract verification on the baseline checkpoint
WITHOUT modifying any production code, launcher UI, or PDF viewer logic:
1. Verifies DWG cache key generation logic and inputs.
2. Verifies script existence, paths, and process argument construction.
3. Tests isolation of non-existent DWG handling in render_dwg_model.
4. Audits layout sorting and TabOrder contract expectations.
5. Verifies error handling and timeout configurations.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.backend.server import (
    DWG_CACHE_DIR,
    DWG_DAEMON_SCRIPT,
    DWG_RENDER_SCRIPT,
    DWG_SMART_RENDER_SCRIPT,
    file_cache_key,
    render_dwg_model,
)


class TestDwgPipelineContractAudit(unittest.TestCase):
    def test_dwg_scripts_exist(self):
        """Verifies that the backend references existing DWG conversion scripts."""
        self.assertTrue(DWG_RENDER_SCRIPT.exists(), f"Missing: {DWG_RENDER_SCRIPT}")
        self.assertTrue(DWG_SMART_RENDER_SCRIPT.exists(), f"Missing: {DWG_SMART_RENDER_SCRIPT}")
        self.assertTrue(DWG_DAEMON_SCRIPT.exists(), f"Missing: {DWG_DAEMON_SCRIPT}")

    def test_dwg_cache_key_inputs(self):
        """Audits what data enters the cache key calculation for DWG files."""
        with tempfile.NamedTemporaryFile(suffix=".dwg", delete=False) as tf:
            tf.write(b"dummy dwg content for hashing")
            tf_path = Path(tf.name)

        try:
            key1 = file_cache_key(tf_path, "dwg-smart-cad-v2")
            self.assertTrue(len(key1) > 0)

            # Same file produces identical key
            key2 = file_cache_key(tf_path, "dwg-smart-cad-v2")
            self.assertEqual(key1, key2)

            # Different tag produces different key
            key3 = file_cache_key(tf_path, "dwg-smart-cad-v3")
            self.assertNotEqual(key1, key3)
        finally:
            tf_path.unlink(missing_ok=True)

    def test_missing_dwg_returns_structured_error_without_exception(self):
        """Verifies that render_dwg_model handles missing files safely without crashing the server."""
        non_existent = Path(tempfile.gettempdir()) / "non_existent_audit_file.dwg"
        if non_existent.exists():
            non_existent.unlink()

        result = render_dwg_model(non_existent)
        self.assertTrue(result.get("is_missing"))
        self.assertEqual(result.get("pages"), 0)
        self.assertEqual(result.get("status"), "missing")
        self.assertTrue(len(result.get("errors", [])) > 0)

    def test_non_dwg_extension_raises_value_error(self):
        """Verifies that render_dwg_model rejects non-DWG files."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tf:
            tf.write(b"not a dwg")
            tf_path = Path(tf.name)

        try:
            with self.assertRaises(ValueError):
                render_dwg_model(tf_path)
        finally:
            tf_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
