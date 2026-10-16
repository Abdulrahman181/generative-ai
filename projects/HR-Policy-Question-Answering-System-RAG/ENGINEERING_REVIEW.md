# Engineering Review — HR Policy Question Answering System (RAG)

**Repository:** `Abdulrahman181/HR-Policy-Question-Answering-System-RAG`  
**Review scope:** `app.py`, `hr-policy-question-answering-system-rag.ipynb`, `README.md`, `requirements.txt`, `.gitignore`, and repository artifacts  
**Review date:** 2026-10-13  
**Status:** Static audit and code repairs completed; end-to-end model execution was not claimed.

## Executive summary

The repository is a single-domain HR-policy RAG application, not the multi-agent HR/IT LangGraph system described by the original README. The checked-in Chroma artifact is usable as a pre-built index in principle, but the source PDFs are absent. The original notebook also depended on a machine-specific Kaggle path and contained saved outputs from a previous run.

The implementation was repaired to make paths configurable, delay the expensive LLM load, use current LangChain retriever invocation, report missing data/dependencies clearly, and avoid presenting smoke prompts as an evaluation benchmark. The notebook outputs were cleared while retaining valid empty `outputs` lists required by the notebook schema.

## Findings and repairs

### Application (`app.py`)

- **Portability:** replaced string concatenation/implicit working-directory assumptions with `Path(__file__).resolve()` and `HR_POLICY_VECTOR_DB`.
- **Missing artifact handling:** added an explicit vector-index directory check with a message explaining how to set the path or rebuild the index.
- **Dependency handling:** moved heavy LangChain, Transformers, and PyTorch imports into loader functions so missing packages produce actionable UI errors instead of an opaque import failure.
- **Resource use:** embeddings and the retriever are cached; the language model is loaded only after the user asks a question rather than on every initial app load.
- **LangChain API:** changed deprecated `get_relevant_documents` usage to `retriever.invoke(question)`.
- **Generation compatibility:** uses `torch_dtype` when loading the model, deterministic `do_sample=False`, and normalizes string/list/dict generation responses while removing common prompt echoes and control tokens.
- **Sources:** displays stable source/page labels with duplicate suppression.
- **Input behavior:** preserves the empty-question warning and returns the documented fallback answer when retrieval is empty.

### Notebook (`hr-policy-question-answering-system-rag.ipynb`)

- Replaced `/kaggle/input/hr-policy-docs-pdf` with `HR_POLICY_DATA_PATH`, defaulting to `data/hr-policy-docs-pdf`.
- Added clear `FileNotFoundError` messages for a missing PDF directory or an empty PDF directory.
- Uses recursive, sorted PDF discovery and `Path`-based paths; the Chroma persistence path is configurable through `HR_POLICY_VECTOR_DB`.
- Uses a string path when passing `persist_directory` for compatibility across Chroma versions.
- Added `torch.manual_seed(42)` and changed generation to `do_sample=False` for more repeatable smoke runs.
- Updated the stress-testing section to explicitly state that the prompts are qualitative smoke checks, not a held-out benchmark.
- Removed all saved outputs and execution counts; code-cell `outputs` arrays remain empty so the notebook remains schema-valid.
- Retained the ingestion and metadata flow; no fabricated PDF content or metrics were added.

### Dependencies and repository hygiene

- Expanded `requirements.txt` for notebook imports (`pypdf`, `langchain-community`, `langchain-huggingface`, `langchain-text-splitters`, `tqdm`, `accelerate`, and optional `bitsandbytes`) and added conservative major-version bounds.
- Added ignores for local source PDFs, generated SQLite/vector artifacts, notebook checkpoints, Ruff cache, and pytest cache. Existing tracked demo artifacts were not deleted.
- Replaced the inaccurate multi-agent README with documentation of the actual RAG flow, environment variables, setup, rebuild procedure, validation commands, and limitations.
- Added `tests/test_static_validation.py`, a dependency-free unittest suite covering Python AST parsing, notebook code-cell parsing, output cleanup, removal of the machine-specific Kaggle path, required notebook dependencies, and index presence.

## Data, split, leakage, and metrics assessment

The checked-in `chroma_hr_db/chroma.sqlite3` contains **97 embedding rows**. Its metadata lists these source names: `annualhealthcheck.pdf`, `leavepolicy.pdf`, `noticeperiod.pdf`, `officetime.pdf`, `separation.pdf`, and `travel.pdf`. No source PDF files are present in the repository.

This project builds a retrieval index; it does not train a supervised model and does not contain a train/test split, held-out questions, reference answers, or labels. Consequently:

- no leakage-safe benchmark split can be verified;
- retrieval recall, answer accuracy, groundedness, hallucination rate, and latency are not measured;
- the notebook's four stress prompts remain smoke checks only;
- the persisted index cannot be independently rebuilt or provenance-audited until the source PDFs are supplied.

These limitations are documented rather than filled with invented data or results.

## Validation performed

All of the following completed successfully in the sandbox:

```text
python3 -m unittest discover -s tests -p 'test_*.py' -v
Ran 8 tests ... OK

ruff check .
All checks passed!

python3 -m compileall -q app.py rag_utils.py tests
completed successfully

git diff --check
completed successfully
```

The static suite also parses each notebook code cell after removing IPython `!` installation magics. The notebook has 18 cells, zero saved outputs, and no `/kaggle/input/` path after repair.

## Not run / remaining release blockers

A full Streamlit-to-model run was **not** claimed. The current sandbox lacks at least `streamlit` and `langchain_chroma` from the application runtime, while model downloads plus GPU/CPU capacity were not exercised. The missing source PDFs also prevent a reproducible rebuild. Install `requirements.txt`, provide the PDFs, and run the documented commands before treating this as a production evaluation.

Other remaining risks are normal for a small RAG demo: fixed `k=3`, no reranker, no citation verification, no formal prompt-injection defense, no authentication, and no automated answer-quality gate. The prompt's context-only instruction is a mitigation, not a guarantee.

## Files changed

- `.gitignore`
- `README.md`
- `app.py`
- `rag_utils.py`
- `hr-policy-question-answering-system-rag.ipynb`
- `requirements.txt`
- `tests/test_static_validation.py`
- `ENGINEERING_REVIEW.md`

A local-only Git commit is created after this report; no changes are pushed to GitHub.

## Second Senior Review

**Review date:** 2026-10-15
**Scope:** all tracked files, notebook cells and metadata, Python/configuration/tests/README, Git history and diff, and the checked-in Chroma artifact.

### Findings and repairs

- **Missing declared runtime dependency (fixed):** both `app.py` and the notebook import `langchain_huggingface`, but `requirements.txt` did not declare `langchain-huggingface`. It is now pinned to a conservative major-version range.
- **Unsafe/fragile generation handling (fixed):** answer extraction could split on any occurrence of the prompt and source labels exposed absolute paths. New dependency-free `rag_utils.py` removes only a true prompt prefix, handles common response shapes, applies the documented fallback for empty output, and renders only a filename plus page label.
- **Prompt-boundary weakness (fixed):** retrieved text is now explicitly delimited as quoted reference data and instructions inside it are rejected in both the app and notebook prompts. This is a mitigation, not a formal prompt-injection defense.
- **GPU compatibility (fixed):** app model loading no longer assumes every CUDA device supports bfloat16; it falls back to float16. The notebook's 4-bit path is opt-in and reports a clear CUDA requirement instead of failing on ordinary CPU execution.
- **Notebook state and portability (fixed):** removed execution-history metadata, notebook-level Kaggle/Papermill metadata, stale Kaggle framing, and all saved outputs; code cells retain schema-valid empty outputs and null execution counts. The vector path is configurable through `HR_POLICY_VECTOR_DB` and defaults to `chroma_hr_db` when run from the repository root.
- **Validation coverage (improved):** tests now cover response normalization, prompt-boundary construction, path-safe citations, code-cell state, the required Hugging Face integration, and basic Chroma SQLite collection/embedding presence. No source data, labels, metrics, or end-to-end claims were invented.
- **UI error boundary (improved):** Chroma `ValueError` configuration/schema failures are shown as Streamlit errors rather than uncaught startup tracebacks; input is bounded to 1,000 characters and stripped before retrieval.

### Second-review validation

```text
python3 -m unittest discover -s tests -p 'test_*.py' -v   # 8 tests, OK
ruff check app.py rag_utils.py tests                       # All checks passed
python3 -m compileall -q app.py rag_utils.py tests         # completed
notebook AST/schema/state validation                       # passed; 18 cells, zero outputs
git diff --check                                           # completed
```

The runtime Streamlit/Chroma/model path was not executed because this sandbox does not provide the complete installed dependency stack and model downloads/GPU capacity were not exercised. The tracked index was inspected with SQLite: one collection and 97 embedding rows are present, with six source filenames in metadata. This confirms basic artifact structure only; it does not establish index provenance or answer quality.

### Remaining risks after the second review

- Source PDFs remain absent, so ingestion provenance, rebuild equivalence, leakage-safe evaluation, and policy-content auditing cannot be verified.
- There is no held-out question/reference-answer set, retrieval threshold, reranker, citation verification, groundedness check, latency budget, authentication, or automated answer-quality gate.
- Local model downloads and the checked-in Chroma artifact remain sensitive to upstream library/model compatibility; a clean environment install and a real smoke run are still release prerequisites.
- The prompt boundary reduces, but cannot eliminate, prompt injection and hallucination risk. The app still uses fixed `k=3` retrieval without a calibrated relevance threshold.
