#!/usr/bin/env python3
"""Generate and ingest synthetic course material into the RAG knowledge base.

Creates, per course, a multi-page "Lecture Notes" document (one page per topic,
so page numbers map to topics for citations) plus a short syllabus. Content is
clearly synthetic but topic-relevant so semantic search and the AI analyst have
genuine material to retrieve and cite.

Usage: python scripts/ingest_docs.py [--fresh]
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import select  # noqa: E402

from app.core.logging import configure_logging  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.academic import Course, Topic  # noqa: E402
from app.models.documents import Document, DocumentChunk  # noqa: E402
from app.rag.ingest import ingest_document  # noqa: E402

# Topic-specific blurbs (used when available) make retrieval demos concrete.
TOPIC_BLURBS = {
    "Dynamic Programming": (
        "Dynamic programming solves problems with overlapping subproblems and optimal "
        "substructure by storing intermediate results. Key techniques are memoization "
        "(top-down recursion with a cache) and tabulation (bottom-up tables). Classic "
        "worked examples include the 0/1 knapsack, longest common subsequence, and coin "
        "change. Students often struggle to identify the recurrence relation and the "
        "correct state definition; practising state design is essential."),
    "Graphs": (
        "Graphs model relationships as vertices and edges. Core algorithms include "
        "breadth-first search, depth-first search, Dijkstra's shortest path, and "
        "topological sort. Represent graphs with adjacency lists for sparse graphs."),
    "Recursion": (
        "Recursion expresses a solution in terms of smaller instances with a base case "
        "and a recursive case. It underpins divide-and-conquer and dynamic programming."),
    "SQL": (
        "SQL queries relational data with SELECT, JOIN, WHERE, GROUP BY and aggregate "
        "functions. Understanding joins and grouping is essential for reporting."),
    "Neural Networks": (
        "Neural networks stack linear layers and nonlinear activations, trained by "
        "backpropagation and gradient descent. Watch for overfitting and use validation."),
}

GENERIC = (
    "This lecture introduces {topic} within {course}. It covers the core definitions, "
    "key concepts, and typical exam-style problems for {topic}. Worked examples and "
    "practice questions are provided. Common pitfalls and prerequisite skills for "
    "{topic} are highlighted so students can self-assess their understanding.")


def topic_note(course_title: str, topic: str) -> str:
    blurb = TOPIC_BLURBS.get(topic, GENERIC.format(topic=topic, course=course_title))
    return f"{topic}\n\n{blurb}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fresh", action="store_true", help="delete existing documents first")
    args = ap.parse_args()
    configure_logging()

    with SessionLocal() as db:
        if args.fresh:
            db.query(DocumentChunk).delete()
            db.query(Document).delete()
            db.commit()
            print("Cleared existing documents.")

        courses = db.execute(select(Course).order_by(Course.id)).scalars().all()
        total_docs = 0
        for c in courses:
            topics = db.execute(
                select(Topic).where(Topic.course_id == c.id).order_by(Topic.sequence)
            ).scalars().all()
            pages = [(i + 1, topic_note(c.title, t.name)) for i, t in enumerate(topics)]
            ingest_document(db, title=f"{c.title} - Lecture Notes", doc_type="lecture",
                            course_id=c.id, pages=pages, filename=f"{c.id}_notes.txt")
            syllabus = (
                f"Syllabus\n\n{c.title} ({c.code}) covers: "
                + ", ".join(t.name for t in topics)
                + f". Instructor: {c.instructor_name}. Assessment is by quizzes, "
                "assignments, a midterm and a final exam.")
            ingest_document(db, title=f"{c.title} - Syllabus", doc_type="syllabus",
                            course_id=c.id, text=syllabus, filename=f"{c.id}_syllabus.txt")
            total_docs += 2
        print(f"Ingested {total_docs} documents across {len(courses)} courses.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
