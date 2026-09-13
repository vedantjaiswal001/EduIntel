"""Semantic search over document chunks with metadata filtering + reranking."""
from __future__ import annotations

import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.documents import Document, DocumentChunk
from app.rag.embeddings import EmbeddingModel

_TOK = re.compile(r"[a-zA-Z][a-zA-Z0-9'-]+")
_STOP = {
    "the", "is", "a", "an", "of", "to", "in", "on", "for", "and", "or", "what",
    "why", "how", "are", "do", "does", "this", "that", "with", "at", "by", "be",
    "as", "it", "its", "we", "our", "you", "your", "can", "will", "which", "who",
    "students", "student", "course", "topic", "performing", "poorly", "about",
    "please", "explain", "tell", "me", "show", "find", "material",
}


def _content_tokens(text: str) -> set:
    return {t for t in _TOK.findall(text.lower()) if len(t) > 2 and t not in _STOP}


def _keyword_overlap(query: str, text: str) -> float:
    q = _content_tokens(query)
    d = _content_tokens(text)
    if not q:
        return 0.0
    return len(q & d) / len(q)


def semantic_search(
    db: Session,
    query: str,
    *,
    course_id: Optional[str] = None,
    topic: Optional[str] = None,
    doc_type: Optional[str] = None,
    top_k: int = None,
    min_similarity: float = None,
    rerank: bool = True,
) -> dict:
    top_k = top_k or settings.RAG_TOP_K
    min_similarity = settings.RAG_MIN_SIMILARITY if min_similarity is None else min_similarity

    model = EmbeddingModel.get()
    qvec = model.encode_one(query).tolist()

    # Fetch a wider candidate set for reranking, then trim. A larger pool lets
    # keyword reranking recover relevant chunks when embeddings are weak (e.g.
    # the offline hashing fallback); harmless with true semantic embeddings.
    candidate_k = max(top_k * 3, 30) if rerank else top_k
    dist = DocumentChunk.embedding.cosine_distance(qvec).label("distance")
    stmt = select(DocumentChunk, dist)
    if course_id:
        stmt = stmt.where(DocumentChunk.course_id == course_id)
    if topic:
        stmt = stmt.where(DocumentChunk.topic == topic)
    if doc_type:
        stmt = stmt.where(DocumentChunk.doc_type == doc_type)
    stmt = stmt.order_by(dist).limit(candidate_k)

    rows = db.execute(stmt).all()
    results = []
    doc_titles: dict = {}
    for chunk, distance in rows:
        sim = 1.0 - float(distance)
        if chunk.document_id not in doc_titles:
            d = db.get(Document, chunk.document_id)
            doc_titles[chunk.document_id] = d.title if d else "Unknown"
        title = doc_titles[chunk.document_id]
        score = sim
        if rerank:
            score = 0.75 * sim + 0.25 * _keyword_overlap(query, chunk.content)
        results.append({
            "chunk_id": chunk.id,
            "document_id": chunk.document_id,
            "document_title": title,
            "page": chunk.page,
            "section": chunk.section,
            "topic": chunk.topic,
            "doc_type": chunk.doc_type,
            "content": chunk.content,
            "similarity": round(sim, 4),
            "score": round(score, 4),
            "citation": f"[{title}, p.{chunk.page}]",
        })

    if rerank:
        results.sort(key=lambda r: r["score"], reverse=True)
    results = results[:top_k]

    best = max((r["similarity"] for r in results), default=0.0)
    is_hashing = model.method.startswith("hashing")
    # Cosine magnitudes differ by embedding space; the offline hashing fallback
    # produces compressed, collision-prone similarities, so its floor is lower
    # and it additionally requires genuine lexical overlap on the top result to
    # avoid spurious "sufficient" verdicts. True semantic embeddings use the
    # standard cosine floor alone.
    effective_min = 0.12 if is_hashing else min_similarity
    top_overlap = max((_keyword_overlap(query, r["content"]) for r in results), default=0.0)
    sufficient = best >= effective_min and len(results) > 0
    if is_hashing:
        sufficient = sufficient and top_overlap > 0.0
    return {
        "query": query,
        "results": results,
        "count": len(results),
        "best_similarity": round(best, 4),
        "sufficient": sufficient,
        "min_similarity": effective_min,
        "reranked": rerank,
        "embedding_method": model.method,
    }
