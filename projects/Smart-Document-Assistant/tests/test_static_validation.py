"""Static repository checks that do not require heavyweight ML dependencies."""

from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StaticValidationTests(unittest.TestCase):
    def test_application_parses(self) -> None:
        ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))

    def test_notebook_is_valid_and_has_no_stale_outputs(self) -> None:
        notebook = json.loads(
            (ROOT / "chat-with-your-documents-project.ipynb").read_text(
                encoding="utf-8"
            )
        )
        self.assertGreater(len(notebook.get("cells", [])), 0)
        self.assertNotIn("widgets", notebook.get("metadata", {}))
        self.assertNotIn("kaggle", notebook.get("metadata", {}))
        self.assertNotIn("papermill", notebook.get("metadata", {}))
        for cell in notebook["cells"]:
            if cell.get("cell_type") == "code":
                ast.parse("".join(cell.get("source", [])))
                self.assertEqual(cell.get("outputs", []), [])
                self.assertIsNone(cell.get("execution_count"))

    def test_notebook_uses_portable_configuration(self) -> None:
        notebook_text = (ROOT / "chat-with-your-documents-project.ipynb").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("/kaggle/", notebook_text)
        self.assertNotIn("!pip install", notebook_text)
        self.assertNotIn("langchain.text_splitter", notebook_text)
        self.assertNotIn("langchain.prompts", notebook_text)
        self.assertIn("DATA_DIR", notebook_text)
        self.assertIn("LLM_MODEL_DIR", notebook_text)
        notebook = json.loads(notebook_text)
        code_text = "\n".join(
            "".join(cell.get("source", []))
            for cell in notebook.get("cells", [])
            if cell.get("cell_type") == "code"
        )
        self.assertIn('path.suffix.lower() == ".pdf"', code_text)

    def test_runtime_dependencies_match_imported_stack(self) -> None:
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        for package in (
            "streamlit",
            "langchain-community",
            "langchain-core",
            "langchain-text-splitters",
            "faiss-cpu",
            "sentence-transformers",
            "ctransformers",
            "pypdf",
            "jupyterlab",
        ):
            self.assertIn(package, requirements)


if __name__ == "__main__":
    unittest.main()
