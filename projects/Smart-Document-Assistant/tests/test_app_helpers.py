"""Focused tests for application helpers that do not load ML artifacts."""

from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import app


class AppHelperTests(unittest.TestCase):
    def test_relative_environment_path_is_rooted_at_repository(self) -> None:
        with patch.dict(os.environ, {"FAISS_INDEX_DIR": "tmp/index"}, clear=False):
            self.assertEqual(
                app._path_from_env("FAISS_INDEX_DIR", app.DEFAULT_INDEX_DIR),
                app.PROJECT_ROOT / "tmp/index",
            )

    def test_positive_integer_environment_setting(self) -> None:
        with patch.dict(os.environ, {"TEST_LIMIT": "7"}, clear=False):
            self.assertEqual(app._positive_int_env("TEST_LIMIT", 1), 7)
        with patch.dict(os.environ, {"TEST_LIMIT": "0"}, clear=False):
            with self.assertRaises(ValueError):
                app._positive_int_env("TEST_LIMIT", 1)

    def test_format_response_handles_empty_and_incomplete_metadata(self) -> None:
        self.assertEqual(app.format_response("", []), app.NOT_FOUND_MESSAGE)
        docs = [
            SimpleNamespace(metadata={"source": "paper.pdf", "page": 2}),
            SimpleNamespace(metadata={"source": "paper.pdf", "page": 2}),
            SimpleNamespace(metadata={}),
            SimpleNamespace(),
        ]
        rendered = app.format_response("Grounded answer", docs)
        self.assertIn("- paper.pdf (Page 2)", rendered)
        self.assertIn("- Unknown source (Page N/A)", rendered)
        self.assertEqual(rendered.count("paper.pdf"), 1)


if __name__ == "__main__":
    unittest.main()
