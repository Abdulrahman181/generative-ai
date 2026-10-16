"""Knowledge base — Day 1/2 RAG + real project KB data.

Loads `app/rag/data/knowledge_base_data.json` (319 entries across 5 categories).
Retrieval modes:
  - keyword  : token overlap (works without HF token)
  - semantic : Day 2 cosine similarity on HF embeddings (all-MiniLM-L6-v2)
  - hybrid   : merge both rankings
"""

from __future__ import annotations

import hashlib
import json
import os
import pickle
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from pypdf import PdfReader
from sklearn.metrics.pairwise import cosine_similarity

from app.core import HF_TOKEN

load_dotenv()

DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_JSON = DATA_DIR / "knowledge_base_data.json"
EMBED_CACHE = DATA_DIR / "embeddings_cache.pkl"
EMBEDDING_CACHE_VERSION = 2
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

KEYWORD_MIN_COVERAGE = 0.34
SEMANTIC_MIN_SCORE = 0.45
_USER_QUERY_MARKERS = ("what do you know about me", "tell me about my profile", "my information", "my skills", "my experience", "my education", "what skills do i have", "what experience do i have", "what education do i have")

CATEGORIES = (
    "job_description",
    "skill",
    "career_roadmap",
    "learning_resource",
    "resume_guideline",
)

client = InferenceClient(token=HF_TOKEN or os.getenv("hf_token") or None)


                                                                              

def read_pdf(file_path):
    pdf_reader = PdfReader(file_path)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() or ""
    print(f"Read {len(text)} characters from {file_path}")
    return text


def chunk_text(text, chunk_size=50):
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


def create_embeddings(text):
    embedding = client.feature_extraction(text, model=EMBEDDING_MODEL)
    vector = np.asarray(embedding, dtype=float)
    if vector.ndim != 1 or vector.size == 0:
        raise ValueError("Embedding provider returned an invalid vector.")
    return vector


                                                                              

@dataclass
class DocumentChunk:
    content: str
    source: str
    score: float = 0.0
    category: str = ""
    title: str = ""
    entry_id: int | None = None


                                                                              

def is_user_data_query(query: str) -> bool:
    normalized = str(query).lower().strip()
    return any(marker in normalized for marker in _USER_QUERY_MARKERS)


class KnowledgeBase:
    """Handles JSON KB data + Day 2 embed/search."""

    def __init__(self) -> None:
        self.entries: list[dict] = []
                                                                            
        self.embeddings: list[dict] = []

                                                                               

    def load_json(
        self,
        path: str | Path | None = None,
        categories: list[str] | None = None,
    ) -> int:
        """Load knowledge_entries from knowledge_base_data.json."""
        json_path = Path(path) if path else DEFAULT_JSON
        if not json_path.is_file():
            print(f"[KB] JSON not found: {json_path}")
            return 0

        data = json.loads(json_path.read_text(encoding="utf-8"))
        raw = data.get("knowledge_entries", []) if isinstance(data, dict) else data
        if not isinstance(raw, list):
            raw = []
        self.entries.clear()
        self.embeddings.clear()
        count = 0
        for item in raw:
            if not isinstance(item, dict):
                continue
            cat = item.get("category", "")
            if categories and cat not in categories:
                continue
            content = self._normalize_content(item.get("content", ""))
            if not content.strip():
                continue
            self.entries.append({
                "id": item.get("id"),
                "category": cat,
                "title": item.get("title") or "",
                "subcategory": item.get("subcategory") or "",
                "content": content,
                "keywords": item.get("keywords") or "",
                "source": item.get("source") or json_path.name,
            })
            count += 1
        print(f"[KB] Loaded {count} entries from {json_path.name}")
        return count

    def load_text(self, text: str, source: str = "inline", chunk_size: int = 50) -> None:
        """Day 2: chunk + embed raw text (needs HF token)."""
        chunks = chunk_text(text, chunk_size=chunk_size)
        for chunk in chunks:
            row = {
                "chunk": chunk,
                "source": source,
                "category": "inline",
                "title": source,
                "entry_id": None,
            }
            if HF_TOKEN:
                row["embedding"] = create_embeddings(chunk)
            else:
                row["embedding"] = None
            self.embeddings.append(row)
            self.entries.append({
                "id": None,
                "category": "inline",
                "title": source,
                "subcategory": "",
                "content": chunk,
                "keywords": "",
                "source": source,
            })

    def load_pdf(self, file_path: str | Path, chunk_size: int = 50) -> None:
        path = Path(file_path)
        text = read_pdf(str(path))
        self.load_text(text, source=path.name, chunk_size=chunk_size)

    def load_directory(self, path: Path, chunk_size: int = 50) -> int:
        count = 0
        if not path.is_dir():
            return 0
        for file in sorted(path.rglob("*")):
            if file.suffix.lower() == ".pdf":
                self.load_pdf(file, chunk_size=chunk_size)
                count += 1
            elif file.suffix.lower() in (".txt", ".md"):
                text = file.read_text(encoding="utf-8", errors="ignore")
                self.load_text(text, source=file.name, chunk_size=chunk_size)
                count += 1
        return count

                                                                               

    def _content_fingerprint(self, max_chars: int = 800) -> str:
        payload = [
            {
                "id": entry.get("id"),
                "category": entry.get("category"),
                "title": entry.get("title"),
                "content": entry.get("content", "")[:max_chars],
                "source": entry.get("source"),
            }
            for entry in self.entries
        ]
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

    def build_embeddings(self, force: bool = False, max_chars: int = 800) -> int:
        """Embed each KB entry once; cache only when content and model metadata match."""
        if not HF_TOKEN:
            print("[KB] No HF_TOKEN — semantic embeddings unavailable.")
            return 0

        if not force and self._load_embed_cache(max_chars=max_chars):
            return len(self.embeddings)

        self.embeddings = []
        for entry in self.entries:
            text = f"{entry['title']}\n{entry['content']}"[:max_chars]
            emb = create_embeddings(text)
            self.embeddings.append({
                "chunk": entry["content"],
                "embedding": emb,
                "source": entry["source"],
                "category": entry["category"],
                "title": entry["title"],
                "entry_id": entry["id"],
            })
        self._save_embed_cache(max_chars=max_chars)
        print(f"[KB] Built {len(self.embeddings)} embeddings")
        return len(self.embeddings)

    def _load_embed_cache(self, max_chars: int = 800) -> bool:
        if not EMBED_CACHE.is_file() or not self.entries:
            return False
        try:
            cached = pickle.loads(EMBED_CACHE.read_bytes())
            if not isinstance(cached, dict):
                return False
            expected = {
                "version": EMBEDDING_CACHE_VERSION,
                "model": EMBEDDING_MODEL,
                "knowledge_base_hash": self._content_fingerprint(max_chars=max_chars),
            }
            metadata = cached.get("metadata")
            embeddings = cached.get("embeddings")
            if metadata != expected or not isinstance(embeddings, list) or len(embeddings) != len(self.entries):
                return False
            for item in embeddings:
                vector = np.asarray(item.get("embedding"), dtype=float)
                if vector.ndim != 1 or vector.size == 0:
                    return False
            self.embeddings = embeddings
            print(f"[KB] Loaded {len(self.embeddings)} embeddings from cache")
            return True
        except Exception as e:
            print(f"[KB] Cache load failed: {e}")
            return False

    def _save_embed_cache(self, max_chars: int = 800) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "metadata": {
                "version": EMBEDDING_CACHE_VERSION,
                "model": EMBEDDING_MODEL,
                "knowledge_base_hash": self._content_fingerprint(max_chars=max_chars),
            },
            "embeddings": self.embeddings,
        }
        EMBED_CACHE.write_bytes(pickle.dumps(payload))

                                                                               

    def search(
        self,
        query: str,
        top_k: int = 3,
        category: str | None = None,
        mode: str = "hybrid",
    ) -> list[DocumentChunk]:
        """Search KB. mode: keyword | semantic | hybrid."""
        if not self.entries and not self.embeddings:
            return []

        mode = (mode or "hybrid").lower()
        if mode == "semantic":
            return self._semantic_search(query, top_k=top_k, category=category)
        if mode == "keyword":
            return self._keyword_search(query, top_k=top_k, category=category)

                
        kw = self._keyword_search(query, top_k=top_k * 3, category=category)
        if HF_TOKEN:
            sem = self._semantic_search(query, top_k=top_k * 3, category=category)
            return self._rrf_merge(kw, sem, top_k=top_k) if sem else kw[:top_k]
        return kw[:top_k]

    def _keyword_search(
        self, query: str, top_k: int = 3, category: str | None = None
    ) -> list[DocumentChunk]:
        tokens = set(self._tokenize(query))
        if not tokens:
            return []

        scored: list[DocumentChunk] = []
        for entry in self.entries:
            if category and entry["category"] != category:
                continue
            title_tokens = set(self._tokenize(entry["title"]))
            content_tokens = set(self._tokenize(f"{entry['content']} {entry['keywords']}"))
            matched = tokens & (title_tokens | content_tokens)
            title_hit = tokens & title_tokens
            if not matched:
                continue
            coverage = len(matched) / len(tokens)
            if coverage < KEYWORD_MIN_COVERAGE:
                continue
            if len(tokens) == 1 and not title_hit and len(matched) < 2:
                continue
            score = coverage * 2.0 + (len(title_hit) / len(tokens)) * 1.5
            scored.append(DocumentChunk(
                content=entry["content"],
                source=entry["source"],
                score=round(score, 4),
                category=entry["category"],
                title=entry["title"],
                entry_id=entry["id"],
            ))

        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:top_k]

    def _semantic_search(
        self, query: str, top_k: int = 3, category: str | None = None
    ) -> list[DocumentChunk]:
        if not self.embeddings:
            if self.entries and HF_TOKEN:
                self.build_embeddings()
            else:
                return []

        query_embedding = create_embeddings(query)
        scores = []
        for chunk in self.embeddings:
            if category and chunk.get("category") != category:
                continue
            emb = chunk.get("embedding")
            if emb is None:
                continue
            score = cosine_similarity(
                query_embedding.reshape(1, -1),
                np.array(emb).reshape(1, -1),
            )[0][0]
            if score < SEMANTIC_MIN_SCORE:
                continue
            scores.append({
                "chunk": chunk["chunk"],
                "source": chunk["source"],
                "category": chunk.get("category", ""),
                "title": chunk.get("title", ""),
                "entry_id": chunk.get("entry_id"),
                "score": float(score),
            })

        scores.sort(key=lambda x: x["score"], reverse=True)
        return [
            DocumentChunk(
                content=item["chunk"],
                source=item["source"],
                score=item["score"],
                category=item["category"],
                title=item["title"],
                entry_id=item["entry_id"],
            )
            for item in scores[:top_k]
        ]

    @staticmethod
    def _rrf_merge(
        kw: list[DocumentChunk], sem: list[DocumentChunk], top_k: int = 3, k_rrf: int = 60
    ) -> list[DocumentChunk]:
        scores: dict[str, float] = {}
        by_key: dict[str, DocumentChunk] = {}

        def key(c: DocumentChunk) -> str:
            return f"{c.entry_id}:{c.title}:{c.content[:80]}"

        for rank, chunk in enumerate(kw):
            k = key(chunk)
            scores[k] = scores.get(k, 0.0) + 1.0 / (k_rrf + rank + 1)
            by_key[k] = chunk
        for rank, chunk in enumerate(sem):
            k = key(chunk)
            scores[k] = scores.get(k, 0.0) + 1.0 / (k_rrf + rank + 1)
            by_key[k] = chunk

        merged = sorted(by_key.values(), key=lambda c: scores[key(c)], reverse=True)
        for c in merged:
            c.score = scores[key(c)]
        return merged[:top_k]

    def stats(self) -> dict:
        by_cat: dict[str, int] = {}
        for e in self.entries:
            by_cat[e["category"]] = by_cat.get(e["category"], 0) + 1
        return {
            "total_entries": len(self.entries),
            "embeddings": len(self.embeddings),
            "semantic_ready": bool(self.embeddings),
            "by_category": by_cat,
        }

    @staticmethod
    def _tokenize(query: str) -> list[str]:
        stop = {
            "a", "an", "the", "and", "or", "of", "for", "to", "in", "on", "at", "by",
            "is", "are", "was", "were", "be", "what", "how", "should", "can", "do",
            "my", "your", "i", "me", "with", "from", "about",
        }
        raw = re.findall(r"[a-z0-9][a-z0-9+\-#.]{1,}", query.lower())
        return [t for t in dict.fromkeys(raw) if t not in stop and len(t) >= 2]

    @staticmethod
    def _normalize_content(content: str) -> str:
        """Flatten JSON-string job blobs into readable text."""
        if not content:
            return ""
        if isinstance(content, dict):
            return KnowledgeBase._normalize_content(json.dumps(content))
        text = str(content).strip()
        if text.startswith("{") and text.endswith("}"):
            try:
                obj = json.loads(text)
                parts = []
                for key in (
                    "title", "description", "department", "level",
                    "experience_years", "education",
                ):
                    if obj.get(key):
                        parts.append(f"{key}: {obj[key]}")
                for key in (
                    "responsibilities", "required_skills", "preferred_skills",
                    "soft_skills", "certifications",
                ):
                    val = obj.get(key)
                    if isinstance(val, list) and val:
                        parts.append(f"{key}: {', '.join(str(v) for v in val)}")
                return "\n".join(parts) if parts else text
            except json.JSONDecodeError:
                return text
        return text


                                                                              

_default_kb: KnowledgeBase | None = None


def get_knowledge_base(
    categories: list[str] | None = None,
    build_semantic: bool = False,
) -> KnowledgeBase:
    """Return shared KnowledgeBase loaded from app/rag/data JSON."""
    global _default_kb
    if _default_kb is None or not _default_kb.entries:
        kb = KnowledgeBase()
        # Keep one complete cache. Category filtering belongs to search, not
        # cache construction; otherwise the first request narrows later ones.
        kb.load_json()
        if build_semantic and HF_TOKEN:
            kb.build_embeddings()
        _default_kb = kb
    elif build_semantic and HF_TOKEN and not _default_kb.embeddings:
        _default_kb.build_embeddings()
    return _default_kb


def reset_knowledge_base() -> None:
    global _default_kb
    _default_kb = None
