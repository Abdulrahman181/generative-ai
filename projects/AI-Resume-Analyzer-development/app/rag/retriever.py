"""Retriever — Day 2 RAG over the project knowledge base."""

from __future__ import annotations

from huggingface_hub import InferenceClient

from app.core import HF_RAG_MODEL, HF_TOKEN
from app.rag.knowledge_base import DocumentChunk, KnowledgeBase, get_knowledge_base


class Retriever:
    """Search the KnowledgeBase and format context / answers."""

    def __init__(self, knowledge_base: KnowledgeBase | None = None) -> None:
        self._kb = knowledge_base or get_knowledge_base()
        self._client = InferenceClient(token=HF_TOKEN) if HF_TOKEN else None

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        category: str | None = None,
        mode: str = "hybrid",
    ) -> list[DocumentChunk]:
        return self._kb.search(query, top_k=top_k, category=category, mode=mode)

    def retrieve_as_context(
        self,
        query: str,
        top_k: int = 3,
        category: str | None = None,
        mode: str = "hybrid",
    ) -> str:
        chunks = self.retrieve(query, top_k=top_k, category=category, mode=mode)
        if not chunks:
            return "No relevant knowledge base documents found."
        parts = []
        for i, c in enumerate(chunks, 1):
            label = c.title or c.source or f"chunk-{i}"
            cat = f" ({c.category})" if c.category else ""
            parts.append(f"[{i}] {label}{cat}\n{c.content}")
        return "\n\n---\n\n".join(parts)

    def answer(
        self,
        query: str,
        top_k: int = 3,
        category: str | None = None,
        mode: str = "hybrid",
        max_tokens: int = 200,
    ) -> str:
        """Day 2 RAG: retrieve → prompt → HF chat completion."""
        chunks = self.retrieve(query, top_k=top_k, category=category, mode=mode)
        top_chunk = [c.content for c in chunks]

        prompt = (
            f"Answer the question based on the context below:\n\n"
            f"Context: {top_chunk}\n\n"
            f"Question: {query}\n"
            f"Answer:"
        )

        if not self._client:
            return self.retrieve_as_context(
                query, top_k=top_k, category=category, mode=mode
            )

        try:
            response = self._client.chat.completions.create(
                model=HF_RAG_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            if content and content.strip():
                return content.strip()
        except Exception:
            # Retrieval remains useful when an optional provider is unavailable.
            pass
        return self.retrieve_as_context(query, top_k=top_k, category=category, mode=mode)
