"""Knowledge-base document endpoints: upload, list, ingest."""
from __future__ import annotations

import os
import tempfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.documents import Document
from app.rag.ingest import ingest_document

router = APIRouter(prefix="/documents", tags=["documents"])


class TextIngest(BaseModel):
    title: str = Field(min_length=1)
    doc_type: str = "note"
    course_id: str | None = None
    text: str = Field(min_length=1)


def _doc_dict(d: Document) -> dict:
    return {
        "id": d.id, "title": d.title, "doc_type": d.doc_type, "course_id": d.course_id,
        "num_pages": d.num_pages, "num_chunks": d.num_chunks, "status": d.status,
        "uploaded_by": d.uploaded_by, "uploaded_at": d.uploaded_at,
        "embedding_method": (d.meta or {}).get("embedding_method"),
    }


@router.get("")
def list_documents(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(select(Document).order_by(Document.id.desc())).scalars().all()
    return [_doc_dict(d) for d in rows]


@router.get("/{document_id}")
def get_document(document_id: int, db: Session = Depends(get_db)) -> dict:
    d = db.get(Document, document_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return _doc_dict(d)


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    doc_type: str = Form("lecture"),
    course_id: str | None = Form(None),
    db: Session = Depends(get_db),
) -> dict:
    suffix = os.path.splitext(file.filename or "")[1] or ".txt"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        result = ingest_document(
            db, title=title, doc_type=doc_type, course_id=course_id,
            source_path=tmp_path, filename=file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    finally:
        os.unlink(tmp_path)
    return result


@router.post("/text")
def ingest_text(body: TextIngest, db: Session = Depends(get_db)) -> dict:
    try:
        return ingest_document(
            db, title=body.title, doc_type=body.doc_type,
            course_id=body.course_id, text=body.text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
