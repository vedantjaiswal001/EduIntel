"""Document ingestion into the pgvector-backed knowledge base."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.academic import Topic
from app.models.documents import Document, DocumentChunk
from app.rag.chunking import chunk_document, extract_text
from app.rag.embeddings import EmbeddingModel

logger = get_logger(__name__)


def _topic_vocab(db: Session, course_id: Optional[str]) -> List[str]:
    q = select(Topic.name)
    if course_id:
        q = q.where(Topic.course_id == course_id)
    return db.execute(q.distinct()).scalars().all()


def ingest_document(
    db: Session,
    *,
    title: str,
    doc_type: str,
    course_id: Optional[str] = None,
    source_path: Optional[str] = None,
    text: Optional[str] = None,
    pages: Optional[List[Tuple[int, str]]] = None,
    filename: Optional[str] = None,
    uploaded_by: Optional[str] = "instructor",
) -> dict:
    if pages is not None:
        pass
    elif source_path:
        pages = extract_text(source_path)
    elif text is not None:
        pages = [(1, text)]
    else:
        raise ValueError("Provide pages, source_path, or text")

    chunks = chunk_document(pages, topic_vocab=_topic_vocab(db, course_id))
    if not chunks:
        raise ValueError("No extractable text found in document")

    model = EmbeddingModel.get()
    embeddings = model.encode([c["content"] for c in chunks])

    doc = Document(
        course_id=course_id, title=title, doc_type=doc_type, filename=filename,
        num_pages=len(pages), num_chunks=len(chunks), status="processed",
        uploaded_by=uploaded_by, uploaded_at=datetime.utcnow(),
        meta={"embedding_method": model.method},
    )
    db.add(doc)
    db.flush()  # get doc.id

    for c, emb in zip(chunks, embeddings):
        db.add(DocumentChunk(
            document_id=doc.id, course_id=course_id, chunk_index=c["chunk_index"],
            content=c["content"], page=c["page"], section=c["section"],
            topic=c["topic"], doc_type=doc_type, token_count=c["token_count"],
            embedding=emb.tolist(),
        ))
    db.commit()
    db.refresh(doc)
    logger.info("Ingested document %s (%d chunks) via %s", title, len(chunks), model.method)
    return {"document_id": doc.id, "title": title, "chunks": len(chunks),
            "pages": len(pages), "embedding_method": model.method}
