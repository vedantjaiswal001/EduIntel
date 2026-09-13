#!/usr/bin/env python3
"""Validate that the synthetic dataset actually contains the intended
statistical relationships. This is the Phase-2 verification step: it fails
loudly if the generator stops producing meaningful signal.

Run: python scripts/validate_data.py --data data/synthetic
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd


def pearson(x, y) -> float:
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 3:
        return float("nan")
    return float(np.corrcoef(x[m], y[m])[0, 1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/synthetic")
    args = ap.parse_args()
    D = args.data

    def load(name):
        return pd.read_csv(os.path.join(D, f"{name}.csv"))

    students = load("students")
    courses = load("courses")
    topics = load("topics")
    enroll = load("enrollments")
    assessments = load("assessments")
    results = load("assessment_results")
    attendance = load("attendance")
    mastery = load("student_topic_mastery")
    feedback = load("feedback")

    checks = []

    def check(name, passed, detail):
        checks.append((name, bool(passed), detail))

    # 1) attendance % vs mean assessment score (per student-course)
    att = attendance.copy()
    att["present"] = (att["status"] != "absent").astype(int)
    att_sc = att.groupby(["student_id", "course_id"])["present"].mean().rename("att_pct")
    ares = results.merge(assessments[["id", "course_id"]], left_on="assessment_id", right_on="id")
    perf = ares.groupby(["student_id", "course_id"])["percentage"].mean().rename("mean_pct")
    j = pd.concat([att_sc, perf], axis=1).dropna()
    r_att = pearson(j["att_pct"], j["mean_pct"])
    check("attendance→performance (r>0.2)", r_att > 0.2, f"pearson r = {r_att:.3f}")

    # 2) course difficulty vs mean course score (negative)
    cmean = ares.groupby("course_id")["percentage"].mean()
    cdiff = courses.set_index("id")["difficulty"]
    cc = pd.concat([cdiff, cmean], axis=1).dropna()
    r_cd = pearson(cc["difficulty"], cc["percentage"])
    check("course difficulty→lower scores (r<-0.4)", r_cd < -0.4, f"pearson r = {r_cd:.3f}")

    # 3) topic difficulty vs topic mastery (negative)
    tmean = mastery.groupby("topic_id")["mastery"].mean()
    tdiff = topics.set_index("id")["difficulty"]
    tt = pd.concat([tdiff, tmean], axis=1).dropna()
    r_td = pearson(tt["difficulty"], tt["mastery"])
    check("topic difficulty→lower mastery (r<-0.4)", r_td < -0.4, f"pearson r = {r_td:.3f}")

    # 4) Dynamic Programming is among the weakest topics in C01
    c01 = topics[topics["course_id"] == "C01"].merge(
        tmean.rename("m"), left_on="id", right_index=True)
    c01 = c01.sort_values("m")
    dp_rank = list(c01["name"]).index("Dynamic Programming") if "Dynamic Programming" in list(c01["name"]) else -1
    check("Dynamic Programming is weakest topic in C01", dp_rank == 0,
          f"C01 mastery order: {list(c01['name'])}")

    # 5) missing assignments vs final grade (negative)
    miss = results[results["is_missing"] == True].groupby("student_id").size().rename("n_missing")  # noqa: E712
    fin = enroll.groupby("student_id")["final_grade"].mean().rename("avg_final")
    mm = pd.concat([fin, miss], axis=1).fillna({"n_missing": 0})
    r_miss = pearson(mm["n_missing"], mm["avg_final"])
    check("missing assignments→lower final (r<-0.2)", r_miss < -0.2, f"pearson r = {r_miss:.3f}")

    # 6) early score slope vs final grade (declining trajectory → lower final).
    #    Uses quizzes/midterm only (assignments carry missing-work noise) over the
    #    feature window (excludes the final), computed per student-course then
    #    averaged — the same way the Phase-4 `score_slope` feature is built.
    ares2 = ares.merge(assessments[["id", "sequence", "kind"]], left_on="assessment_id",
                       right_on="id", suffixes=("", "_a"))
    early = ares2[(ares2["sequence"] <= 6) & (ares2["kind"].isin(["quiz", "exam"]))]

    def slope(g):
        g = g.sort_values("sequence")
        if g["sequence"].nunique() < 3:
            return np.nan
        return np.polyfit(g["sequence"], g["percentage"], 1)[0]

    sc_slope = early.groupby(["student_id", "course_id"]).apply(
        slope, include_groups=False).rename("slope")
    sl = sc_slope.groupby("student_id").mean().rename("early_slope")
    ss = pd.concat([fin, sl], axis=1).dropna()
    r_sl = pearson(ss["early_slope"], ss["avg_final"])
    check("early score slope→final grade (r>0.15)", r_sl > 0.15, f"pearson r = {r_sl:.3f}")

    # 7) planted anomaly: read the target assessment from the manifest.
    with open(os.path.join(D, "manifest.json")) as fh:
        manifest = json.load(fh)
    anom_id = manifest["anomaly"]["assessment_id"]
    anom_course = manifest["anomaly"]["course_id"]
    cA = ares[(ares["course_id"] == anom_course) & (~ares["is_missing"])]
    # Within-student drop: each student's anomaly score minus their mean on the
    # course's other assessments. This removes ability variance (how Phase 3
    # detects an assessment-level anomaly).
    anom_scores = cA[cA["assessment_id"] == anom_id].set_index("student_id")["percentage"]
    other_mean = cA[cA["assessment_id"] != anom_id].groupby("student_id")["percentage"].mean()
    delta = (anom_scores - other_mean).dropna()
    z = float(delta.mean() / delta.std())
    check(f"anomaly {anom_id} within-student drop >2.5 SD", z < -2.5,
          f"z-score = {z:.2f}, mean drop = {delta.mean():.1f} pts")

    # 8) negative feedback fraction higher for hard topics
    #    (approximate: negative-rating share by course vs course difficulty)
    feedback["neg"] = (feedback["rating"] <= 2).astype(int)
    fneg = feedback.groupby("course_id")["neg"].mean()
    ff = pd.concat([cdiff, fneg], axis=1).dropna()
    r_fb = pearson(ff["difficulty"], ff["neg"])
    check("harder courses→more negative feedback (r>0.3)", r_fb > 0.3, f"pearson r = {r_fb:.3f}")

    # target class balance
    avg = enroll.groupby("student_id")["final_grade"].mean()
    labels = pd.cut(avg, [-1, 50, 65, 200], labels=["HIGH", "MEDIUM", "LOW"])
    dist = labels.value_counts().to_dict()
    check("all three risk classes present", len(dist) == 3 and min(dist.values()) >= 20,
          f"class distribution = {dist}")

    print("\n=== Phase 2 data validation ===")
    all_ok = True
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name:48s} {detail}")
        all_ok = all_ok and ok
    print("===============================")
    print("RESULT:", "ALL CHECKS PASSED" if all_ok else "SOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
