"""Streamlit UI for answering questions against the persisted HR policy index.

The raw PDFs used to build ``chroma_hr_db`` are not part of this repository.  The
index is therefore treated as a pre-built artifact; rebuild it from the notebook
when the source documents are available.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import streamlit as st
from rag_utils import FALLBACK_ANSWER, build_prompt, extract_answer, format_source_label

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CHROMA_PATH = BASE_DIR / "chroma_hr_db"
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_LLM_MODEL = "microsoft/Phi-3-mini-4k-instruct"
MAX_QUESTION_CHARS = 1_000


def configured_path(env_name: str, default: Path) -> Path:
    """Return an expanded, absolute path from an environment variable."""

    value = os.getenv(env_name)
    return Path(value).expanduser().resolve() if value else default


@st.cache_resource
def load_embeddings(model_name: str):
    """Load the embedding model only once per Streamlit process."""

    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError as exc:
        raise RuntimeError(
            "Embedding dependencies are missing. Install requirements.txt first."
        ) from exc
    return HuggingFaceEmbeddings(model_name=model_name)


@st.cache_resource
def load_retriever(chroma_path: str, embedding_model: str):
    """Open the persisted Chroma index and expose a stable top-k retriever."""

    path = Path(chroma_path)
    if not path.is_dir():
        raise FileNotFoundError(
            f"Vector database not found at {path}. Set HR_POLICY_VECTOR_DB "
            "or build the index with the notebook."
        )
    try:
        from langchain_chroma import Chroma
    except ImportError as exc:
        raise RuntimeError(
            "Chroma dependencies are missing. Install requirements.txt first."
        ) from exc
    embeddings = load_embeddings(embedding_model)
    vectorstore = Chroma(
        persist_directory=str(path),
        embedding_function=embeddings,
    )
    return vectorstore.as_retriever(search_kwargs={"k": 3})


@st.cache_resource
def load_llm(model_id: str):
    """Load a deterministic local text-generation model on first use."""

    try:
        import torch
        from langchain_huggingface import HuggingFacePipeline
        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
    except ImportError as exc:
        raise RuntimeError(
            "LLM dependencies are missing. Install requirements.txt first."
        ) from exc

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model_kwargs: dict[str, Any] = {"device_map": "auto"}
    if torch.cuda.is_available():
        supports_bfloat16 = getattr(torch.cuda, "is_bf16_supported", lambda: False)()
        model_kwargs["torch_dtype"] = (
            torch.bfloat16 if supports_bfloat16 else torch.float16
        )
    else:
        # CPU inference is supported for functional checks, but large models can
        # be impractical. The message is kept in the UI rather than guessing.
        model_kwargs["torch_dtype"] = torch.float32
    model = AutoModelForCausalLM.from_pretrained(model_id, **model_kwargs)
    model.eval()
    generation_pipeline = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=512,
        do_sample=False,
        return_full_text=False,
    )
    return HuggingFacePipeline(pipeline=generation_pipeline)


st.set_page_config(page_title="HR Policy Question Answering System", layout="wide")
st.title("HR Policy Assistant")
st.caption("Answers are grounded in the persisted HR policy vector index.")

question = st.text_input("Enter your HR policy question", max_chars=MAX_QUESTION_CHARS)
chroma_path = configured_path("HR_POLICY_VECTOR_DB", DEFAULT_CHROMA_PATH)
embedding_model = os.getenv("HR_POLICY_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
llm_model = os.getenv("HR_POLICY_LLM_MODEL", DEFAULT_LLM_MODEL)

try:
    retriever = load_retriever(str(chroma_path), embedding_model)
except (FileNotFoundError, RuntimeError, OSError, ValueError) as exc:
    st.error(str(exc))
    st.stop()

if st.button("Ask"):
    question = question.strip()
    if not question:
        st.warning("Please enter a question.")
    else:
        with st.spinner("Searching the HR policies..."):
            documents = retriever.invoke(question)
        if not documents:
            st.info(FALLBACK_ANSWER)
        else:
            context = "\n\n".join(doc.page_content for doc in documents)
            prompt = build_prompt(context, question)
            try:
                with st.spinner("Generating answer..."):
                    llm = load_llm(llm_model)
                    response = llm.invoke(prompt)
            except (RuntimeError, OSError, ValueError, TypeError) as exc:
                st.error(f"Unable to load or run the language model: {exc}")
            else:
                st.subheader("Answer")
                st.write(extract_answer(response, prompt))
                st.subheader("Sources")
                seen_sources: set[str] = set()
                for doc in documents:
                    label = format_source_label(doc.metadata)
                    if label not in seen_sources:
                        st.write(label)
                        seen_sources.add(label)
