# Engineering Review — Smart Document Assistant

## Scope

Reviewed every tracked Python, notebook, README, dependency, and ignore file in
`Abdulrahman181/Smart-Document-Assistant`. The repository contains `app.py`, one
Jupyter notebook, `README.md`, `requirements.txt`, `.gitignore`, and a tracked
`Data` text file. `Data` contains only the Kaggle URL
`https://www.kaggle.com/datasets/harshsinghal/nlp-and-llm-related-arxiv-papers`; it
is not a local dataset.

## Findings and fixes

### Critical/runtime issues fixed

1. **Application startup was not portable or diagnosable.** The original app
   loaded a relative FAISS directory and model at import time, so a missing
   artifact caused an opaque crash. It also used a Kaggle/Hugging Face-style
   model reference without declaring or validating a local model file.
   `app.py` now has a `main()` entry point, resolves relative paths from the
   repository, supports environment-variable overrides, lazily loads resources,
   validates `index.faiss`, `index.pkl`, and the GGUF model file, and displays a
   clear setup message when artifacts are absent.
2. **Dependency/import mismatch.** The original app imported
   `langchain_community` and `langchain_classic` while `requirements.txt` did
   not provide those packages and declared `llama-cpp-python` even though the
   code used CTransformers. Requirements now include the actual LangChain split
   packages, `ctransformers`, the text splitter package, and bounded compatible
   version ranges.
3. **Brittle source rendering.** Source metadata was accessed with a mandatory
   dictionary key and sources were emitted in arbitrary set order. Rendering
   now tolerates missing metadata and sorts de-duplicated source references.
4. **Notebook had environment-specific paths and stale execution state.** The
   notebook used `/kaggle/input/...`, installed packages inline, had captured
   install/model errors and outputs, and traversed files in unspecified order.
   It now uses `DATA_DIR`, `MAX_FILES`, `FAISS_INDEX_DIR`, and model environment
   variables, sorts PDF paths, checks for a real directory and PDFs, records
   relative source names, and has all old outputs/execution state removed.
5. **Generated artifacts were not fully ignored.** `.gitignore` now covers
   generated FAISS directories, local data, Python caches, pytest caches, and
   notebook checkpoints while retaining the tracked dataset-link file.

### Data splitting, leakage, reproducibility, and metrics

- This project is a retrieval-and-generation application, not a supervised
  training pipeline. There are no labels, fitted parameters, train/test split,
  or benchmark question set in the repository; therefore no fabricated split,
  accuracy, or quality result was added.
- Ingestion uses deterministic sorted PDF traversal and a bounded `MAX_FILES`
  setting. The retrieval index contains all ingested chunks, as expected for a
  serving index. There is currently no source-disjoint evaluation set, so
  leakage-safe benchmark performance cannot be established.
- The notebook's original context-overlap calculation was only a token/string
  overlap diagnostic and is not an accuracy, factuality, or groundedness
  metric. The README explicitly documents this limitation and recommends a
  fixed, source-disjoint question set with retrieval and answer-groundedness
  metrics reported separately.

## Files changed

- `app.py` — portable configuration, lazy loading, validation, robust response
  formatting, and guarded Streamlit entry point.
- `chat-with-your-documents-project.ipynb` — portable ingestion paths,
  deterministic traversal, missing-data/model messages, and output cleanup.
- `requirements.txt` — corrected runtime dependency declarations and ranges.
- `.gitignore` — generated artifacts and cache rules.
- `README.md` — setup, artifact contract, configuration, validation commands,
  and limitations.
- `tests/test_static_validation.py` — dependency-free AST, notebook hygiene,
  portability, and dependency consistency checks.

## Validation performed

- `python3 -m unittest discover -s tests -v` — **4 tests passed**.
- `python3 -m compileall -q app.py tests` — **passed**.
- `ruff check app.py chat-with-your-documents-project.ipynb tests` — **passed**.
- Notebook JSON parsing and AST parsing for every code cell — **passed**.
- Notebook output audit — **no captured outputs; no executed code cells**.
- `git diff --check` — **passed**.

## Execution caveat

A complete RAG execution was intentionally not claimed. The sandbox does not
have Streamlit, LangChain, FAISS, Sentence-Transformers, or CTransformers
installed, and the repository does not contain PDFs, a generated FAISS index,
or GGUF weights. The static checks validate syntax, structure, portability, and
repository hygiene only; install `requirements.txt` and provide the documented
artifacts before running ingestion or the Streamlit app.

## Second Senior Review

### Scope and residual defects found

The second pass re-inspected every tracked file, the complete notebook JSON and
code cells, the Git history/diff, dependency declarations, tests, and generated
repository state. It found no fabricated data, metrics, credentials, or tracked
model/data artifacts. The following real residual issues were fixed:

1. **Configuration-sensitive resource caches were stale.** The Streamlit cache
   keys did not include embedding device, model type, token limit, or context
   length even though those values came from environment variables. Loader
   signatures now receive these settings explicitly, so changing configuration
   cannot silently reuse an incompatible resource.
2. **Invalid configuration failed late or silently.** Positive-integer parsing
   now rejects malformed or non-positive token/context settings. Model filenames
   must be plain filenames inside the configured model directory, preventing
   accidental path traversal and making the artifact contract explicit.
3. **Interactive inference could terminate the UI session.** Per-question chain
   failures are now converted to a visible assistant error message while setup
   failures remain diagnosable in the UI.
4. **Source formatting assumed complete LangChain metadata.** Empty answers and
   documents with missing/`None` metadata are handled safely; duplicate source
   references remain deterministic and de-duplicated.
5. **Notebook ingestion missed uppercase extensions and accepted bad limits.**
   PDF discovery is case-insensitive and sorted by relative path, `MAX_FILES`
   and model limits are validated, and empty post-cleaning corpora fail with an
   explicit message instead of reaching FAISS with invalid input.
6. **Notebook imports and paths were not aligned with the declared stack.**
   Notebook code now uses `langchain_core.prompts` and
   `langchain_text_splitters`, resolves relative paths through `PROJECT_ROOT`,
   validates model filenames, and creates the output directory explicitly.
7. **Dependency ranges allowed unreviewed API drift and notebook execution was
   undocumented.** LangChain packages are bounded to the reviewed 0.3 API line,
   CTransformers is bounded below 0.3, and `jupyterlab` is declared.
8. **Stale notebook metadata remained.** Widget state and Kaggle/Papermill
   execution metadata were removed in addition to clearing outputs and execution
   counts. The notebook now contains only portable kernel/language metadata.

### Second-review validation

- `python3 -m unittest discover -s tests -v` — **7 tests passed**.
- `python3 -m compileall -q app.py tests` — **passed**.
- `ruff check app.py tests` — **passed**.
- Notebook JSON parsing and AST parsing for every code cell — **passed**.
- Notebook output/execution/metadata audit — **no outputs, no execution counts,
  no widgets/Kaggle/Papermill state**.
- `git diff --check` — **passed**.
- A full RAG run was **not claimed**: the repository still has no PDFs, FAISS
  index, embedding cache, or GGUF weights, and the current environment lacks
  `langchain-community`, FAISS, and CTransformers. The installed package set was
  inspected for import compatibility where available.

### Remaining risks

- `FAISS.load_local(..., allow_dangerous_deserialization=True)` remains required
  by the LangChain API and must only be used with a trusted, project-generated
  index; there is no cryptographic artifact provenance check.
- There is still no fixed, source-disjoint benchmark or human-labeled evaluation
  set, so retrieval quality, answer groundedness, and leakage-safe metrics remain
  unmeasured. The notebook overlap value is explicitly only a token-overlap
  diagnostic.
- Native/large runtime dependencies and model weights were not installed or
  executed in this review; platform-specific CTransformers/FAISS installation and
  model-format compatibility require validation in the target deployment.
