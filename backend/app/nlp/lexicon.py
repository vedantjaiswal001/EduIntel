"""Lexicons for rule-based feedback NLP (sentiment, issues, urgency, aspect)."""
from __future__ import annotations

from typing import Dict, List

POSITIVE_WORDS = {
    "good", "great", "excellent", "helpful", "clear", "enjoyed", "enjoy", "well",
    "useful", "easy", "love", "loved", "amazing", "organised", "organized",
    "understandable", "interesting", "fantastic", "supportive", "genuinely",
}
NEGATIVE_WORDS = {
    "bad", "poor", "difficult", "hard", "confusing", "confused", "unclear",
    "harsh", "unfair", "boring", "unreasonable", "struggled", "struggle", "tough",
    "rushed", "slow", "disorganised", "disorganized", "impossible", "terrible",
    "frustrating", "overwhelming", "crammed", "lacking",
}
# Intensifiers push severity/urgency up.
URGENCY_TERMS = {
    "extremely", "very", "unreasonable", "impossible", "urgent", "failing",
    "cannot", "never", "always", "way too", "far too", "completely",
}

# Issue category -> trigger keywords.
ISSUE_LEXICON: Dict[str, List[str]] = {
    "assignment difficulty": ["difficult", "hard", "tough", "challenging", "unreasonable"],
    "lecture pace": ["pace", "fast", "quickly", "rushed", "slow"],
    "lack of examples": ["example", "examples", "worked example", "practice"],
    "course material": ["material", "notes", "resources", "textbook"],
    "workload": ["workload", "too much", "long", "time-consuming", "crammed"],
    "grading": ["grading", "harsh", "marks", "unfair", "grade"],
    "clarity": ["confusing", "unclear", "explained clearly", "hard to follow", "follow"],
}

# Map an issue to a coarse aspect.
ISSUE_TO_ASPECT: Dict[str, str] = {
    "assignment difficulty": "assignments",
    "workload": "assignments",
    "lecture pace": "lectures",
    "clarity": "lectures",
    "lack of examples": "materials",
    "course material": "materials",
    "grading": "grading",
}
