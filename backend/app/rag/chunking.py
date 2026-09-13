"""Document extraction, cleaning, and metadata-aware chunking."""
from __future__ import annotations

import os
import re
from typing import List, Optional, Tuple

_WS = re.compile(r"[ \t]+")
_MULTINL = re.compile(r"\n{3,}")
_HEADING = re.compile(r"^(#{1,6}\s+.*|[A-Z][A-Za-z0-9 ,&/-]{2,60})$")


def extract_text(path: str) -> List[Tuple[int, str]]:
    """Return [(page_number, text)]. Supports .pdf, .txt, .md."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return _extract_pdf(path)
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        return [(1, fh.read())]


def _extract_pdf(path: str) -> List[Tuple[int, str]]:
    from pypdf import PdfReader

    reader = PdfReader(path)
    out = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            out.append((i, page.extract_text() or ""))
        except Exception:
            out.append((i, ""))
    return out


def clean(text: str) -> str:
    text = text.replace("\r", "\n")
    text = _WS.sub(" ", text)
    text = _MULTINL.sub("\n\n", text)
    return text.strip()


def _detect_section(block: str) -> Optional[str]:
    for line in block.splitlines():
        line = line.strip()
        if not line:
            continue
        if _HEADING.match(line):
            return line.lstrip("# ").strip()[:120]
        return line[:120]
    return None


def chunk_document(
    pages: List[Tuple[int, str]],
    *,
    max_words: int = 180,
    overlap: int = 40,
    topic_vocab: Optional[List[str]] = None,
) -> List[dict]:
    """Split pages into overlapping word-window chunks with metadata."""
    topic_vocab = topic_vocab or []
    chunks: List[dict] = []
    idx = 0
    for page_no, raw in pages:
        text = clean(raw)
        if not text:
            continue
        section = _detect_section(text)
        words = text.split()
        step = max(1, max_words - overlap)
        for start in range(0, len(words), step):
            window = words[start:start + max_words]
            if len(window) < 20 and start != 0:
                break
            content = " ".join(window)
            low = content.lower()
            topic = next((t for t in topic_vocab if t.lower() in low), None)
            chunks.append({
                "chunk_index": idx,
                "content": content,
                "page": page_no,
                "section": section,
                "topic": topic,
                "token_count": len(window),
            })
            idx += 1
            if start + max_words >= len(words):
                break
    return chunks
