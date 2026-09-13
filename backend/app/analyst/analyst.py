"""AI Education Analyst: grounded, cited answers.

The analyst assembles evidence (all numbers computed by the analytics layer),
then either (a) asks the LLM to *phrase* that evidence under strict rules — use
only supplied numbers, cite sources, separate facts/predictions/recommendations,
declare uncertainty — or (b) composes a deterministic extractive answer from the
same evidence when no LLM is available. Either way the figures are traceable and
never invented.
"""
from __future__ import annotations

from typing import Dict, List

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.analyst.context import AnalystContext, gather_context
from app.llm.provider import get_llm

SYSTEM = (
    "You are EduIntel's education data analyst. You will be given a QUESTION and "
    "a list of EVIDENCE items, each with a type and a source. Rules:\n"
    "1. Use ONLY numbers that appear in the evidence. Never invent or estimate "
    "figures.\n"
    "2. Clearly separate: observed facts/statistics, model predictions, retrieved "
    "document evidence, and recommendations.\n"
    "3. Cite sources in square brackets exactly as given (e.g. [Data Structures - "
    "Lecture Notes, p.5]).\n"
    "4. Distinguish association from causation; never claim a cause unless stated.\n"
    "5. If the evidence is insufficient to answer, say so explicitly rather than "
    "guessing.\n"
    "Structure the answer with short sections: Answer, Evidence, Recommended action, "
    "Confidence."
)


def _evidence_block(ctx: AnalystContext) -> str:
    lines = []
    for e in ctx.evidence:
        lines.append(f"- [{e.kind}] {e.statement} (source: {e.source})")
    if ctx.recommendations:
        lines.append("Candidate recommendations (verify before acting):")
        for r in ctx.recommendations:
            lines.append(f"  * {r}")
    lines.append(f"RAG document evidence sufficient: {ctx.rag_sufficient}")
    return "\n".join(lines) if lines else "(no evidence found)"


def answer_question(db: Session, engine: Engine, question: str) -> Dict:
    ctx = gather_context(db, engine, question)
    has_stats = any(e.kind in ("statistic", "fact", "prediction") for e in ctx.evidence)
    sufficient = has_stats or ctx.rag_sufficient

    if not sufficient:
        return {
            "question": question,
            "answer": (
                "There is insufficient evidence in the platform to answer this "
                "confidently. Try naming a specific course, topic, or student, or "
                "upload relevant course material to the knowledge base."
            ),
            "mode": "insufficient",
            "sufficient": False,
            "citations": [],
            "evidence": ctx.as_dict()["evidence"],
            "recommendations": [],
            "entities": ctx.entities,
        }

    llm = get_llm()
    mode = "extractive"
    if getattr(llm, "available", False):
        prompt = (
            f"QUESTION: {question}\n\nEVIDENCE:\n{_evidence_block(ctx)}\n\n"
            "Write the grounded answer now."
        )
        try:
            answer = llm.generate(prompt, system=SYSTEM)
            mode = "llm"
        except Exception:
            answer = _extractive_answer(ctx)
    else:
        answer = _extractive_answer(ctx)

    return {
        "question": question,
        "answer": answer,
        "mode": mode,
        "sufficient": True,
        "citations": ctx.citations,
        "evidence": ctx.as_dict()["evidence"],
        "recommendations": ctx.recommendations,
        "entities": ctx.entities,
    }


def _extractive_answer(ctx: AnalystContext) -> str:
    """Deterministic, grounded answer composed directly from evidence."""
    facts = [e for e in ctx.evidence if e.kind in ("statistic", "fact")]
    preds = [e for e in ctx.evidence if e.kind == "prediction"]
    docs = [e for e in ctx.evidence if e.kind == "document"]
    fb = [e for e in ctx.evidence if e.kind == "feedback"]

    parts: List[str] = ["Answer"]
    if facts:
        parts.append(" ".join(e.statement for e in facts[:4]))
    else:
        parts.append("Based on the available platform data:")

    if preds:
        parts.append("\nModel prediction")
        parts.extend(e.statement for e in preds)

    if fb or docs:
        parts.append("\nEvidence")
        for e in fb:
            parts.append(f"• {e.statement}")
        for e in docs:
            parts.append(f"• {e.statement}")

    if ctx.recommendations:
        parts.append("\nRecommended action (supports, not replaces, instructor judgement)")
        for r in ctx.recommendations:
            parts.append(f"• {r}")

    conf = ("Confidence: document evidence was retrieved and supports this answer."
            if ctx.rag_sufficient else
            "Confidence: based mainly on performance statistics; limited supporting "
            "document evidence was found in the knowledge base.")
    parts.append("\n" + conf)
    if ctx.citations:
        parts.append("\nSources: " + "; ".join(ctx.citations))
    return "\n".join(parts)
