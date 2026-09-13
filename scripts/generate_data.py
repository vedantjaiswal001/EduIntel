#!/usr/bin/env python3
"""EduIntel synthetic education data generator.

Generates a realistic, fully SYNTHETIC dataset for a completed academic term.
Realism comes from a latent-variable generative model, not from hard-coded
numbers: every headline relationship the platform relies on emerges as a
statistical consequence of the process.

Latent drivers per student:
  * ability            – governs baseline achievement
  * conscientiousness  – governs attendance, submission timeliness, missing work
  * trajectory         – stable | declining | improving (a within-term slope)

Emergent relationships (verify with scripts/validate_data.py):
  * attendance %      is positively associated with assessment performance
  * a declining score/attendance trajectory precedes poor final outcomes
  * missing / late assignments are associated with higher risk
  * some topics (e.g. Dynamic Programming) are systematically harder
  * courses differ in difficulty; harder courses yield lower scores
  * negative feedback clusters around the hardest topics/courses

The prediction target used later (Phase 4) is derived from the *final grade*
(which is dominated by the final exam), while model features are computed only
from the early/mid-term window — a genuine, non-leaky early-warning task.

All output is written to data/synthetic/ as CSVs plus a manifest.json that
documents the dataset version, seed, row counts and the planted demo cases.

Usage:
    python scripts/generate_data.py --seed 42 --students 1000 --out data/synthetic
"""
from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, List

import numpy as np
import pandas as pd

try:
    from faker import Faker
except Exception:  # pragma: no cover - Faker optional at runtime
    Faker = None

DATASET_VERSION = "synthetic-v1"
TERM = "2026-S1"
TERM_START = date(2026, 1, 6)  # Monday; a completed Spring term
TERM_WEEKS = 14
SESSIONS_PER_WEEK = 2


# --------------------------------------------------------------------------- #
# Course / topic catalogue. Difficulty and one deliberately hard topic per
# hard course are planted so Topic Intelligence has meaningful signal.
# --------------------------------------------------------------------------- #
COURSE_CATALOG = [
    # id, code, title, department, difficulty, instructor
    ("C01", "CS201", "Data Structures", "Computer Science", 0.70, "Dr. A. Rao"),
    ("C02", "CS301", "Algorithms", "Computer Science", 0.80, "Dr. M. Iyer"),
    ("C03", "CS210", "Databases", "Computer Science", 0.50, "Dr. S. Khan"),
    ("C04", "CS305", "Operating Systems", "Computer Science", 0.72, "Dr. P. Nair"),
    ("C05", "CS320", "Computer Networks", "Computer Science", 0.55, "Dr. L. Menon"),
    ("C06", "CS360", "Machine Learning", "Computer Science", 0.68, "Dr. R. Gupta"),
    ("C07", "MA201", "Discrete Mathematics", "Mathematics", 0.60, "Dr. V. Desai"),
    ("C08", "CS110", "Web Development", "Computer Science", 0.40, "Dr. T. Shah"),
    ("C09", "CS340", "Software Engineering", "Computer Science", 0.45, "Dr. N. Bose"),
    ("C10", "CS410", "Theory of Computation", "Computer Science", 0.82, "Dr. K. Varma"),
]

# topic name lists per course; the last entry of a hard course is a hard topic.
COURSE_TOPICS = {
    "C01": ["Arrays", "Linked Lists", "Trees", "Graphs", "Dynamic Programming"],
    "C02": ["Sorting", "Greedy", "Divide & Conquer", "Graph Algorithms", "NP-Completeness"],
    "C03": ["Relational Model", "SQL", "Normalization", "Indexing", "Transactions"],
    "C04": ["Processes", "Scheduling", "Memory Management", "Concurrency"],
    "C05": ["OSI Model", "Routing", "TCP/IP", "Congestion Control"],
    "C06": ["Regression", "Classification", "Neural Networks", "Model Evaluation"],
    "C07": ["Logic", "Set Theory", "Combinatorics", "Graph Theory"],
    "C08": ["HTML/CSS", "JavaScript", "React", "APIs"],
    "C09": ["Requirements", "Design Patterns", "Testing", "Agile"],
    "C10": ["Automata", "Regular Languages", "Context-Free Grammars", "Turing Machines"],
}

# Topics that are deliberately hard (high difficulty) to create weak-topic signal.
HARD_TOPICS = {
    ("C01", "Dynamic Programming"): 0.90,
    ("C01", "Graphs"): 0.78,
    ("C02", "NP-Completeness"): 0.88,
    ("C02", "Graph Algorithms"): 0.80,
    ("C10", "Turing Machines"): 0.86,
}

PROGRAMS = ["B.Tech CSE", "B.Tech IT", "B.Sc CS", "M.Tech CSE"]

# Assessment schedule per course: (kind, week, sequence, weight, topic_index)
# topic_index = -1 means "spans multiple topics" (midterm/final).
# Weights: the final exam is 50% of the grade and is UNSEEN at prediction time
# (excluded from the feature window). This caps achievable predictive accuracy
# at a realistic level and keeps the early-warning task genuinely hard.
SCHEDULE = [
    ("quiz", 3, 1, 0.04, 0),
    ("assignment", 4, 2, 0.08, 0),
    ("quiz", 6, 3, 0.04, 1),
    ("assignment", 8, 4, 0.08, 1),
    ("exam", 9, 5, 0.14, -1),   # midterm, spans early topics
    ("quiz", 10, 6, 0.04, 2),
    ("assignment", 11, 7, 0.08, 3),  # maps to a hard/late topic where present
    ("exam", 14, 8, 0.50, -1),  # final, spans all topics (unseen predictor)
]
QUESTIONS_PER = {"quiz": 4, "exam_mid": 6, "exam_final": 8}

# Feedback templates keyed by sentiment; {topic}/{course} are filled in.
FEEDBACK_TEMPLATES = {
    "negative": [
        "The {topic} assignments are extremely difficult and the pace is too fast.",
        "I struggled a lot with {topic}; there were not enough worked examples.",
        "{course} moves very quickly and {topic} was never explained clearly.",
        "The workload for {topic} is unreasonable and grading feels harsh.",
        "Lectures on {topic} were confusing and hard to follow.",
        "Too much material on {topic} crammed into too little time.",
    ],
    "neutral": [
        "{topic} was okay but could use more practice problems.",
        "The {course} lectures are fine, though {topic} needs better notes.",
        "Average experience; {topic} could be paced a bit better.",
        "{course} is manageable but the {topic} assignments take long.",
    ],
    "positive": [
        "The instructor explains {topic} really well with great examples.",
        "I enjoyed {course}; the {topic} labs were genuinely helpful.",
        "Clear lectures and useful feedback made {topic} easy to grasp.",
        "{course} is well organised and {topic} was taught excellently.",
    ],
}


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


@dataclass
class Tables:
    students: List[dict] = field(default_factory=list)
    courses: List[dict] = field(default_factory=list)
    topics: List[dict] = field(default_factory=list)
    enrollments: List[dict] = field(default_factory=list)
    assessments: List[dict] = field(default_factory=list)
    questions: List[dict] = field(default_factory=list)
    assessment_results: List[dict] = field(default_factory=list)
    question_results: List[dict] = field(default_factory=list)
    attendance: List[dict] = field(default_factory=list)
    mastery: List[dict] = field(default_factory=list)
    feedback: List[dict] = field(default_factory=list)


def week_datetime(week: int) -> datetime:
    d = TERM_START + timedelta(days=(week - 1) * 7)
    return datetime(d.year, d.month, d.day, 10, 0, 0)


def build_catalog(t: Tables) -> Dict[str, dict]:
    """Create courses + topics; return topic difficulty lookup by topic_id."""
    topic_diff: Dict[str, dict] = {}
    for cid, code, title, dept, diff, instr in COURSE_CATALOG:
        t.courses.append(
            dict(
                id=cid, code=code, title=title, department=dept,
                instructor_name=instr, credits=int(np.random.choice([3, 4])),
                term=TERM, difficulty=diff,
            )
        )
        for seq, name in enumerate(COURSE_TOPICS[cid]):
            tid = f"{cid}-T{seq + 1:02d}"
            tdiff = HARD_TOPICS.get((cid, name), round(0.35 + 0.35 * np.random.rand(), 2))
            t.topics.append(
                dict(id=tid, course_id=cid, name=name, sequence=seq + 1, difficulty=tdiff)
            )
            topic_diff[tid] = dict(course_id=cid, difficulty=tdiff, name=name, seq=seq)
    return topic_diff


def make_students(t: Tables, n: int, rng: np.random.Generator, faker) -> pd.DataFrame:
    rows = []
    for i in range(1, n + 1):
        sid = f"S{i:04d}"
        ability = float(rng.normal(0, 1))
        consc = float(rng.normal(0, 1))
        # trajectory: most stable, with declining/improving minorities
        traj = rng.choice(["stable", "declining", "improving"], p=[0.6, 0.22, 0.18])
        prev_gpa = float(np.clip(6.6 + 1.15 * ability + rng.normal(0, 0.6), 0, 10))
        name = faker.name() if faker else f"Student {i}"
        rows.append(
            dict(
                id=sid, name=name, email=f"{sid.lower()}@eduintel.example",
                program=str(rng.choice(PROGRAMS, p=[0.5, 0.25, 0.15, 0.10])),
                enrollment_year=int(rng.choice([2022, 2023, 2024, 2025])),
                prev_gpa=round(prev_gpa, 2), is_synthetic=True,
                _ability=ability, _consc=consc, _traj=traj,
            )
        )
    df = pd.DataFrame(rows)
    # public table (without latent helper columns)
    t.students = df.drop(columns=[c for c in df.columns if c.startswith("_")]).to_dict("records")
    return df


def traj_score_offset(traj: str, week: int, rng: np.random.Generator) -> float:
    frac = week / TERM_WEEKS
    if traj == "declining":
        return 12.0 - 34.0 * frac + rng.normal(0, 2)
    if traj == "improving":
        return -18.0 + 34.0 * frac + rng.normal(0, 2)
    return rng.normal(0, 2)


def traj_att_offset(traj: str, week: int) -> float:
    frac = week / TERM_WEEKS
    if traj == "declining":
        return 0.9 - 1.9 * frac
    if traj == "improving":
        return -0.9 + 1.7 * frac
    return 0.0


def simulate(
    t: Tables, students: pd.DataFrame, topic_diff: Dict[str, dict],
    rng: np.random.Generator,
) -> None:
    course_by_id = {c["id"]: c for c in t.courses}
    topics_by_course: Dict[str, List[str]] = {}
    for tp in t.topics:
        topics_by_course.setdefault(tp["course_id"], []).append(tp["id"])

    # Assessment + question catalogue is shared across students; create once.
    assessment_meta: Dict[str, List[dict]] = {}
    q_id = 1
    for cid in course_by_id:
        ctopics = topics_by_course[cid]
        metas = []
        for kind, week, seq, weight, tidx in SCHEDULE:
            aid = f"{cid}-A{seq:02d}"
            if tidx == -1:
                primary_topic = None
                span = ctopics if seq == 8 else ctopics[: max(2, len(ctopics) // 2)]
            else:
                primary_topic = ctopics[min(tidx, len(ctopics) - 1)]
                span = [primary_topic]
            t.assessments.append(
                dict(
                    id=aid, course_id=cid, topic_id=primary_topic, kind=kind,
                    title=f"{kind.title()} {seq}", sequence=seq,
                    max_score=100.0, weight=weight,
                    assessment_date=week_datetime(week),
                    due_date=week_datetime(week) + timedelta(days=5) if kind == "assignment" else None,
                )
            )
            # questions for quizzes & exams
            qids: List[tuple] = []
            if kind == "quiz":
                nq = QUESTIONS_PER["quiz"]
                qtopics = [primary_topic] * nq
            elif kind == "exam":
                nq = QUESTIONS_PER["exam_final" if seq == 8 else "exam_mid"]
                qtopics = [span[k % len(span)] for k in range(nq)]
            else:
                nq = 0
                qtopics = []
            for k in range(nq):
                tp = qtopics[k]
                t.questions.append(
                    dict(id=q_id, assessment_id=aid, topic_id=tp, number=k + 1,
                         max_points=1.0, difficulty=topic_diff[tp]["difficulty"]))
                qids.append((q_id, tp))
                q_id += 1
            metas.append(dict(aid=aid, kind=kind, week=week, seq=seq, weight=weight,
                              primary_topic=primary_topic, span=span, qids=qids))
        assessment_meta[cid] = metas

    # Each student enrols in 4-6 courses.
    n_courses = len(course_by_id)
    all_course_ids = list(course_by_id.keys())
    for _, s in students.iterrows():
        ability, consc, traj = s["_ability"], s["_consc"], s["_traj"]
        k = int(rng.integers(4, min(6, n_courses) + 1))
        chosen = list(rng.choice(all_course_ids, size=k, replace=False))
        # per-student per-topic latent mastery fraction (0..1)
        for cid in chosen:
            course = course_by_id[cid]
            cdiff = course["difficulty"]
            t.enrollments.append(
                dict(student_id=s["id"], course_id=cid, term=TERM, status="active",
                     enrolled_on=TERM_START.isoformat(), final_grade=None)
            )
            # ---- attendance (weekly) ----
            present_by_week = {}
            for w in range(1, TERM_WEEKS + 1):
                # +1.0 intercept centres mean attendance near 0.72 (matching the
                # 0.7 baseline the score model assumes).
                eng = sigmoid(1.0 + 1.1 * consc - 1.3 * (cdiff - 0.5) + traj_att_offset(traj, w)
                              + rng.normal(0, 0.25))
                for sess in range(SESSIONS_PER_WEEK):
                    dt = week_datetime(w) + timedelta(days=sess * 3)
                    r = rng.random()
                    status = "present" if r < eng else ("late" if r < eng + 0.08 else "absent")
                    t.attendance.append(dict(student_id=s["id"], course_id=cid,
                                             session_date=dt, week=w, status=status))
                    present_by_week.setdefault(w, []).append(1 if status != "absent" else 0)
            cum_att = {}
            seen = []
            for w in range(1, TERM_WEEKS + 1):
                seen.extend(present_by_week[w])
                cum_att[w] = float(np.mean(seen))

            # ---- assessments ----
            weighted_sum, weight_total = 0.0, 0.0
            for m in assessment_meta[cid]:
                w = m["week"]
                att_so_far = cum_att[w]
                # missing only applies to assignments
                is_missing = False
                delay_hours = None
                if m["kind"] == "assignment":
                    miss_p = sigmoid(-1.5 * consc + (0.9 if traj == "declining" else 0)
                                     + 1.4 * (cdiff - 0.5) - 2.1)
                    is_missing = bool(rng.random() < miss_p)
                    if not is_missing:
                        base_delay = 30 * sigmoid(-consc) + (18 if traj == "declining" else 0)
                        delay_hours = float(max(0.0, rng.normal(base_delay - 12, 20)))

                if is_missing:
                    pct = 0.0
                    submitted_at = None
                else:
                    # topic difficulty: primary topic, or mean of spanned topics
                    if m["primary_topic"]:
                        tdiff = topic_diff[m["primary_topic"]]["difficulty"]
                    else:
                        tdiff = float(np.mean([topic_diff[tp]["difficulty"] for tp in m["span"]]))
                    # Final exam carries large independent noise: it is a heavily
                    # weighted, unseen component, so early features cannot fully
                    # determine the outcome (realistic, non-trivial ML task).
                    extra_noise = 18 if m["seq"] == 8 else 6
                    # Intercept tuned so most students pass and HIGH risk is a
                    # realistic minority (~15-20%) — the meaningful positive class.
                    base = (78 + 15 * ability - 24 * (cdiff - 0.5) - 20 * (tdiff - 0.5)
                            + 13 * (att_so_far - 0.7) + 5 * (s["prev_gpa"] - 6.5)
                            + traj_score_offset(traj, w, rng) + rng.normal(0, extra_noise))
                    pct = float(np.clip(base, 0, 100))
                    submitted_at = week_datetime(w) + timedelta(hours=(delay_hours or 0))
                    # question-level results for quizzes/exams
                    for (qid, tp) in m["qids"]:
                        tp_diff = topic_diff[tp]["difficulty"]
                        frac = np.clip(pct / 100.0 - 0.15 * (tp_diff - 0.5) + rng.normal(0, 0.08), 0.02, 0.99)
                        correct = bool(rng.random() < frac)
                        t.question_results.append(dict(
                            student_id=s["id"], question_id=qid, topic_id=tp,
                            points=1.0 if correct else 0.0, max_points=1.0, correct=correct))

                t.assessment_results.append(dict(
                    student_id=s["id"], assessment_id=m["aid"], score=round(pct, 2),
                    max_score=100.0, percentage=round(pct, 2), is_missing=is_missing,
                    submitted_at=submitted_at,
                    submission_delay_hours=round(delay_hours, 1) if delay_hours is not None else None,
                ))
                weighted_sum += pct * m["weight"]
                weight_total += m["weight"]

            final_grade = round(weighted_sum / weight_total, 2)
            t.enrollments[-1]["final_grade"] = final_grade


def build_mastery(t: Tables) -> None:
    """Derive student_topic_mastery from question_results (real aggregation)."""
    if not t.question_results:
        return
    qr = pd.DataFrame(t.question_results)
    # course lookup per topic
    topic_course = {tp["id"]: tp["course_id"] for tp in t.topics}
    grp = qr.groupby(["student_id", "topic_id"]).agg(
        mastery=("points", "mean"), n=("points", "size")).reset_index()
    for _, r in grp.iterrows():
        t.mastery.append(dict(
            student_id=r["student_id"], topic_id=r["topic_id"],
            course_id=topic_course.get(r["topic_id"], None),
            mastery=round(float(r["mastery"]), 4), assessments_count=int(r["n"])))


def generate_feedback(t: Tables, students: pd.DataFrame, topic_diff, rng, manifest) -> None:
    """Feedback text tied to real course/topic difficulty; ~1.1 per enrollment.

    Sentiment probability depends on the difficulty of a sampled topic, so
    negative feedback clusters around genuinely hard topics/courses.
    """
    course_by_id = {c["id"]: c for c in t.courses}
    topics_by_course: Dict[str, List[dict]] = {}
    for tp in t.topics:
        topics_by_course.setdefault(tp["course_id"], []).append(tp)
    enroll = pd.DataFrame(t.enrollments)
    neg_cluster = 0

    def emit(cid: str, student_id: str) -> None:
        nonlocal neg_cluster
        course = course_by_id[cid]
        tp = topics_by_course[cid][int(rng.integers(0, len(topics_by_course[cid])))]
        tdiff = tp["difficulty"]
        # harder topic / course => more likely negative (drives the clusters)
        p_neg = np.clip(0.15 + 0.6 * (tdiff - 0.4) + 0.3 * (course["difficulty"] - 0.5), 0.05, 0.85)
        p_pos = np.clip(0.55 - 0.5 * (tdiff - 0.4) - 0.2 * (course["difficulty"] - 0.5), 0.05, 0.8)
        p_neu = max(0.05, 1 - p_neg - p_pos)
        s = p_neg + p_pos + p_neu
        sentiment = rng.choice(["negative", "neutral", "positive"],
                               p=[p_neg / s, p_neu / s, p_pos / s])
        text = str(rng.choice(FEEDBACK_TEMPLATES[sentiment])).format(
            topic=tp["name"], course=course["title"])
        if sentiment == "negative":
            neg_cluster += 1
        rating = {"negative": rng.integers(1, 3), "neutral": 3,
                  "positive": rng.integers(4, 6)}[sentiment]
        t.feedback.append(dict(
            student_id=student_id, course_id=cid,
            instructor_name=course["instructor_name"], text=text, rating=float(rating),
            submitted_at=week_datetime(int(rng.integers(5, TERM_WEEKS + 1))),
        ))

    for _, e in enroll.iterrows():
        if rng.random() > 0.90:  # ~90% of enrollments leave feedback
            continue
        emit(e["course_id"], e["student_id"])
        if rng.random() < 0.25:  # some leave a second comment on another aspect
            emit(e["course_id"], e["student_id"])
    manifest["negative_feedback_count"] = neg_cluster


def inject_anomaly(t: Tables, manifest: dict, rng: np.random.Generator) -> None:
    """Plant a clear course-level anomaly: one assessment scores far below norm."""
    target_course, target_seq = "C03", 6  # Databases (moderate variance), Quiz 3
    aid = f"{target_course}-A{target_seq:02d}"
    shift = 36.0
    n = 0
    for r in t.assessment_results:
        if r["assessment_id"] == aid and not r["is_missing"]:
            r["score"] = round(max(0.0, r["score"] - shift), 2)
            r["percentage"] = r["score"]
            n += 1
    manifest["anomaly"] = dict(
        assessment_id=aid, course_id=target_course,
        description=f"{aid} scores shifted down ~{shift} points to create a "
                    "course-level performance anomaly for detection demos.",
        affected_rows=n,
    )


def tag_demo_cases(students: pd.DataFrame, enroll: pd.DataFrame, manifest: dict) -> None:
    """Record clear demo archetypes (by final outcome + trajectory) in manifest."""
    fin = enroll.groupby("student_id")["final_grade"].mean().rename("avg_final")
    df = students.merge(fin, left_on="id", right_index=True, how="left")
    high = df[df["avg_final"] < 50].sort_values("avg_final").head(8)["id"].tolist()
    declining = df[(df["_traj"] == "declining") & (df["avg_final"] < 62)].head(6)["id"].tolist()
    improving = df[df["_traj"] == "improving"].head(6)["id"].tolist()
    manifest["demo_cases"] = dict(
        high_risk_students=high, declining_students=declining, improving_students=improving)


def write_outputs(t: Tables, out_dir: str, manifest: dict) -> None:
    os.makedirs(out_dir, exist_ok=True)
    frames = {
        "students": t.students, "courses": t.courses, "topics": t.topics,
        "enrollments": t.enrollments, "assessments": t.assessments,
        "questions": t.questions, "assessment_results": t.assessment_results,
        "question_results": t.question_results, "attendance": t.attendance,
        "student_topic_mastery": t.mastery, "feedback": t.feedback,
    }
    counts = {}
    for name, rows in frames.items():
        df = pd.DataFrame(rows)
        df.to_csv(os.path.join(out_dir, f"{name}.csv"), index=False)
        counts[name] = len(df)
    manifest["row_counts"] = counts
    with open(os.path.join(out_dir, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2, default=str)
    return counts


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate EduIntel synthetic dataset")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--students", type=int, default=1000)
    ap.add_argument("--out", type=str, default="data/synthetic")
    args = ap.parse_args()

    np.random.seed(args.seed)
    rng = np.random.default_rng(args.seed)
    faker = None
    if Faker is not None:
        faker = Faker()
        Faker.seed(args.seed)

    t = Tables()
    manifest = dict(dataset_version=DATASET_VERSION, seed=args.seed, term=TERM,
                    term_start=TERM_START.isoformat(), term_weeks=TERM_WEEKS,
                    generated_at=datetime.utcnow().isoformat(), synthetic=True)

    topic_diff = build_catalog(t)
    students = make_students(t, args.students, rng, faker)
    simulate(t, students, topic_diff, rng)
    build_mastery(t)
    generate_feedback(t, students, topic_diff, rng, manifest)
    inject_anomaly(t, manifest, rng)

    enroll = pd.DataFrame(t.enrollments)
    tag_demo_cases(students, enroll, manifest)
    counts = write_outputs(t, args.out, manifest)

    print(json.dumps({"dataset_version": DATASET_VERSION, "seed": args.seed,
                       "row_counts": counts, "out": args.out}, indent=2))


if __name__ == "__main__":
    main()
