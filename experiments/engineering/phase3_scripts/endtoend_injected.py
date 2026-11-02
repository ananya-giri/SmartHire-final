"""Phase 3 (label-free) -- end-to-end injected-resume experiment.

This is the L1 experiment: injected resumes go through the FULL pipeline
(guardrail -> scorer) and we measure whether the score or dossier outcome
actually changes. Previous guardrail numbers were on standalone attack
documents; previous scorer numbers were on clean resumes. This closes that
gap.

Method:
  - Sample: first 6 resumes by numeric resume_id within each assigned-JD
    group (assignments.csv) = 30 resumes, 6 per JD x 5 JDs.
  - Payloads: REUSED from the repo's pre-existing dev security set
    (data/security_per_case_v2.json, is_attack == True), one per resume in
    sample_id order. No payload is invented here, and no payload text is
    printed or stored in outputs (only sample_id + family).
  - Embedding (disclosed, single method): the payload is appended as a final
    "Additional Notes:" section of the resume text. Append-only embedding
    is a limitation; mid-document/white-text embeddings are not tested.
  - Pipeline replication (mirrors main.py): scan_document(injected) first.
    If blocked -> quarantined, no score produced. If admitted -> score the
    SANITIZED text (the pipeline scores sanitized text, not raw injected
    text), exactly as main.py does.
  - Scorer: KG scorer (evaluate_match) on tokens from extract_tokens with
    the FIXED extraction rule: extension structural nodes (hubs + sub-hubs)
    are excluded from the extraction vocabulary (see METHODS addendum --
    hub tokens otherwise approve all 10 requirements of their discipline).
    Scores are 100 * approved / 10 against the resume's assigned JD.
  - Downstream attack success (pre-declared): an admitted injected resume
    whose score crosses the 50% decision threshold upward (clean < 50 and
    injected >= 50), OR whose score rises by >= 10 points. Quarantined
    resumes are defence successes, not failures.
"""
import csv, json, sys
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
BASE = os.path.join(REPO, "experiments", "engineering")
# REPO defined above (repo root)
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tools"))
from engineering_graph import build_engineering_graph, extract_tokens, evaluate_match
from security_guardrails import AIHiringGuardrails

STRUCTURAL_NODES = {
    "Mechanical Engineering", "Electrical Engineering", "Civil Engineering",
    "Engineering Technician",
    "Mechanical Design", "Manufacturing", "Thermal & Fluids", "Engineering Analysis",
    "Control & Automation", "Power & Distribution", "Electronics", "Simulation Tools",
    "Structural Engineering", "Site & Construction",
    "Maintenance", "Field Skills",
}


def fixed_tokens(text, graph):
    return [t for t in extract_tokens(text, graph) if t not in STRUCTURAL_NODES]


def kg_score(text, reqs, graph):
    toks = fixed_tokens(text, graph)
    ok = sum(1 for r in reqs if evaluate_match(r, toks, graph)["is_approved"])
    return 100.0 * ok / len(reqs) if reqs else 0.0


def main():
    graph = build_engineering_graph()
    jds = json.load(open(f"{BASE}/jds/jds.json"))
    groups = defaultdict(list)
    for row in csv.DictReader(open(f"{BASE}/assignments.csv")):
        groups[row["assigned_jd"]].append(row["resume_id"])
    sample = []
    for jd in sorted(groups):
        for rid in sorted(groups[jd], key=int)[:6]:
            sample.append((rid, jd))
    assert len(sample) == 30, sample

    dev = json.load(open(f"{REPO}/data/security_per_case_v2.json"))
    attacks = sorted([c for c in dev if c.get("is_attack")], key=lambda c: str(c.get("sample_id")))
    assert len(attacks) >= 30, len(attacks)
    attacks = attacks[:30]

    rows = []
    for (rid, jd), atk in zip(sample, attacks):
        text = open(f"{BASE}/data/{rid}.txt", errors="ignore").read()
        reqs = jds[jd]["requirements"]
        clean = kg_score(text, reqs, graph)
        injected = text + "\n\nAdditional Notes:\n" + atk["text"]
        verdict = AIHiringGuardrails.scan_document(injected)
        blocked = bool(verdict.get("blocked"))
        fired = [k for k, v in (verdict.get("layers") or {}).items() if v]
        if blocked:
            inj_score, sanitized = None, None
        else:
            sanitized = verdict.get("sanitized_text") or injected
            inj_score = kg_score(sanitized, reqs, graph)
        rows.append({
            "resume_id": rid, "jd": jd, "attack_sample_id": atk.get("sample_id"),
            "attack_family": atk.get("family"), "blocked": blocked,
            "layers_fired": fired, "clean_score": round(clean, 1),
            "injected_score": inj_score,
            "score_change": (round(inj_score - clean, 1) if inj_score is not None else None),
        })

    n_blocked = sum(1 for r in rows if r["blocked"])
    admitted = [r for r in rows if not r["blocked"]]
    changes = [r["score_change"] for r in admitted]
    up_cross = [r for r in admitted if r["clean_score"] < 50 and r["injected_score"] >= 50]
    big_rise = [r for r in admitted if r["score_change"] >= 10]
    out = {
        "n": len(rows),
        "quarantined": n_blocked,
        "quarantine_rate_pct": round(100.0 * n_blocked / len(rows), 1),
        "admitted": len(admitted),
        "admitted_mean_clean": round(sum(r["clean_score"] for r in admitted) / len(admitted), 1) if admitted else None,
        "admitted_mean_injected": round(sum(r["injected_score"] for r in admitted) / len(admitted), 1) if admitted else None,
        "admitted_mean_change": round(sum(changes) / len(changes), 2) if changes else None,
        "admitted_increased": sum(1 for c in changes if c > 0),
        "admitted_decreased": sum(1 for c in changes if c < 0),
        "admitted_unchanged": sum(1 for c in changes if c == 0),
        "downstream_success_threshold_cross_up": len(up_cross),
        "downstream_success_rise_ge_10": len(big_rise),
        "downstream_success_ids": [r["resume_id"] for r in up_cross + big_rise],
        "by_family": {},
        "rows": rows,
    }
    for fam in sorted({r["attack_family"] for r in rows}):
        sub = [r for r in rows if r["attack_family"] == fam]
        out["by_family"][fam] = {
            "n": len(sub), "blocked": sum(1 for r in sub if r["blocked"]),
            "admitted": sum(1 for r in sub if not r["blocked"]),
        }
    with open(f"{BASE}/results/phase3_labelfree/endtoend_injected.json", "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))


if __name__ == "__main__":
    main()
