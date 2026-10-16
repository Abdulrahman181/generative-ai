# HR Policy Question Answering System (RAG)

This repository contains a **single-domain Retrieval-Augmented Generation (RAG)** application for questions about HR policy documents. It is not a LangGraph multi-agent or HR/IT routing system; the runnable UI is `app.py` and the reproducible indexing workflow is the notebook.

## What is included

- `app.py`: Streamlit UI that retrieves the top three Chroma documents and asks a local Hugging Face text-generation model to answer only from that context.
- `rag_utils.py`: dependency-free answer normalization, source-label sanitization, and prompt-boundary helpers used by the app and tests.
- `hr-policy-question-answering-system-rag.ipynb`: PDF ingestion, cleaning, chunking, embedding, Chroma persistence, and optional LLM demonstration.
- `chroma_hr_db/`: a checked-in pre-built Chroma artifact. Its metadata reports 97 stored chunks and sources such as `officetime.pdf`.
- `tests/test_static_validation.py`: dependency-free static checks for Python and notebook structure.

## Important data limitation

The source PDF files are **not present in this repository**. The included vector index can be opened by the application, but the PDFs are required to reproduce or audit ingestion and to rebuild the index. Do not interpret the checked-in index as a benchmark dataset or as proof of answer quality.

Place source PDFs under `data/hr-policy-docs-pdf/`, or set `HR_POLICY_DATA_PATH` when adapting the notebook. If the directory is missing, the notebook raises a clear `FileNotFoundError` instead of silently indexing an empty corpus.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The embedding model and the configured language model are downloaded by Hugging Face on first use. GPU inference is recommended for the default Phi-3 model; CPU execution is supported by the app but may be impractical for a multi-billion-parameter model. The notebook's optional 4-bit path additionally uses `bitsandbytes` and `accelerate` and is disabled unless `HR_POLICY_ENABLE_LLM=1` is set.

## Run the application

```bash
streamlit run app.py
```

The default index path is the repository's `chroma_hr_db/`. Override it without editing code:

```bash
HR_POLICY_VECTOR_DB=/absolute/path/to/chroma_hr_db streamlit run app.py
```

Optional model overrides are `HR_POLICY_EMBEDDING_MODEL` and `HR_POLICY_LLM_MODEL`. The application loads embeddings and Chroma at startup, but delays the expensive LLM load until the first question. Missing dependencies, a missing index, and model errors are shown as actionable UI messages.

## Rebuild the index

1. Add the source PDFs under `data/hr-policy-docs-pdf/` (or configure `HR_POLICY_DATA_PATH`).
2. Run the notebook from the repository root through the embedding/vector-store cells. The LLM and smoke-test cells are optional; set `HR_POLICY_ENABLE_LLM=1` only when a suitable CUDA environment and model downloads are available.
3. Set `HR_POLICY_VECTOR_DB` to the newly generated index when launching the app.

The notebook stores relative/portable paths, normalizes PDF metadata, and preserves source/page metadata. It does not implement a supervised train/test split: this is a retrieval index, not a trained predictive model. The included stress prompts are smoke checks only; no accuracy, recall, groundedness, or latency metrics are claimed.

## Validation

Run the lightweight checks that do not import heavyweight ML libraries:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
ruff check app.py tests
python -m compileall -q app.py tests
```

A full end-to-end run requires the dependencies, Hugging Face model downloads, and the source/index artifacts. Those conditions are intentionally not claimed by static validation alone. The checks validate the persisted Chroma SQLite schema/count at a basic integrity level; they do not prove that the missing source PDFs match the checked-in index.

## Security and reproducibility notes

- The prompt instructs the model to answer only from retrieved context, but this is not a formal prompt-injection defense or a quality guarantee.
- Retrieval uses a fixed `k=3`; no held-out evaluation set is included, so leakage and generalization metrics cannot be measured from this repository.
- Generated PDFs, local data, and newly rebuilt Chroma files are ignored by `.gitignore`; the original checked-in index remains tracked for the demo.

## Author

**Abdul Rahman Ahmed**
