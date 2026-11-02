"""Phase 3 (label-free) — AOPC with random-removal null baseline.

Method (documented method of tools/shap_scoring_explainer.py,
evaluate_feature_perturbation_faithfulness, re-implemented for the extended
graph because the explainer hardcodes the v3 tech graph and cannot run on
the extended graph unmodified):
  * Score = 100 * (approved requirements / M), approval via
    engineering_graph.evaluate_match on tokens from extract_tokens.
  * Closed-form Shapley per candidate token: each requirement's 100/M is
    shared equally among the tokens that alone satisfy it (separable game;
    approval is monotone OR over tokens, so single-token incidence is exact).
  * AOPC comprehensiveness: remove tokens in descending-Shapley order,
    k = 1..min(n_tokens, 5); AOPC = mean(baseline - score after removal).
  * AOPC random (null baseline): same k range, tokens removed in a random
    order; mean over 5 random orders, seed 42.

Interpretation note: AOPC here follows the explainer's definition — removal
of top-contributing candidate skill TOKENS with requirements fixed. Removing
requirements instead would change the score denominator (100/M) and is not
the documented method, so it is not used.

Sample: first 4 resumes by numeric resume_id within each assigned-JD group
(assignments.csv) = 20 resumes, 4 per JD x 5 JDs.
"""
import csv
import json
import random
import sys
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
BASE = os.path.join(REPO, "experiments", "engineering")
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tools"))
from engineering_graph import (  # noqa: E402
    build_engineering_graph, extract_tokens, evaluate_match,
)

OUT = f"{BASE}/results/phase3_labelfree"


def score(tokens, reqs, graph):
    if not reqs:
        return 0.0
    ok = sum(1 for r in reqs if evaluate_match(r, tokens, graph)["is_approved"])
    return 100.0 * ok / len(reqs)


def shapley(tokens, reqs, graph):
    """Closed-form Shapley per token (see module docstring)."""
    m = len(reqs)
    phi = {t: 0.0 for t in tokens}
    for r in reqs:
        sat = [t for t in tokens if evaluate_match(r, [t], graph)["is_approved"]]
        if sat:
            share = (100.0 / m) / len(sat)
            for t in sat:
                phi[t] += share
    return phi


def aopc_for_order(tokens, order, reqs, graph, baseline):
    k_max = min(len(tokens), 5)
    drops = []
    for k in range(1, k_max + 1):
        removed = set(order[:k])
        drops.append(baseline - score([t for t in tokens if t not in removed], reqs, graph))
    return (sum(drops) / len(drops)) if drops else 0.0, drops


def main():
    graph = build_engineering_graph()
    jds = json.load(open(f"{BASE}/jds/jds.json"))
    groups = defaultdict(list)
    for row in csv.DictReader(open(f"{BASE}/assignments.csv")):
        groups[row["assigned_jd"]].append(row["resume_id"])
    sample = []  # (resume_id, jd)
    for jd in sorted(groups):
        for rid in sorted(groups[jd], key=int)[:4]:
            sample.append((rid, jd))
    assert len(sample) == 20, sample

    rng = random.Random(42)
    rows = []
    for rid, jd in sample:
        text = open(f"{BASE}/data/{rid}.txt").read()
        tokens = extract_tokens(text, graph)
        reqs = jds[jd]["requirements"]
        base = score(tokens, reqs, graph)
        phi = shapley(tokens, reqs, graph)
        desc = sorted(tokens, key=lambda t: (-phi[t], t))
        aopc_top, drops_top = aopc_for_order(tokens, desc, reqs, graph, base)
        rand_aopcs, rand_drops = [], []
        for _ in range(5):
            order = tokens[:]
            rng.shuffle(order)
            a, d = aopc_for_order(tokens, order, reqs, graph, base)
            rand_aopcs.append(a)
            rand_drops.append(d)
        aopc_rand = sum(rand_aopcs) / len(rand_aopcs)
        rows.append({
            "resume_id": rid, "jd": jd, "n_tokens": len(tokens),
            "baseline_score": round(base, 4),
            "k_evaluated": min(len(tokens), 5),
            "n_positive_shapley_tokens": sum(1 for v in phi.values() if v > 0),
            "aopc_top_shapley": round(aopc_top, 4),
            "top_drops": [round(d, 2) for d in drops_top],
            "aopc_random_mean5": round(aopc_rand, 4),
            "random_order_aopcs": [round(a, 4) for a in rand_aopcs],
            "gap_top_minus_random": round(aopc_top - aopc_rand, 4),
        })
        print(f"{rid} [{jd}] base={base:.1f} tokens={len(tokens)} "
              f"AOPC_top={aopc_top:.2f} AOPC_rand={aopc_rand:.2f}")

    def mean(key, subset):
        vals = [r[key] for r in subset]
        return round(sum(vals) / len(vals), 4) if vals else None

    eligible = [r for r in rows if r["baseline_score"] > 0]
    summary = {
        "n": len(rows),
        "n_eligible_baseline_gt_0": len(eligible),
        "mean_aopc_top_all20": mean("aopc_top_shapley", rows),
        "mean_aopc_random_all20": mean("aopc_random_mean5", rows),
        "gap_all20": round(mean("aopc_top_shapley", rows) - mean("aopc_random_mean5", rows), 4),
        "mean_aopc_top_eligible": mean("aopc_top_shapley", eligible),
        "mean_aopc_random_eligible": mean("aopc_random_mean5", eligible),
        "gap_eligible": round(mean("aopc_top_shapley", eligible) - mean("aopc_random_mean5", eligible), 4),
    }
    print(json.dumps(summary, indent=1))
    json.dump({"sample": [f"{r['resume_id']}:{r['jd']}" for r in rows],
               "rows": rows, "summary": summary},
              open(f"{OUT}/aopc_baseline.json", "w"), indent=1)
    print("wrote aopc_baseline.json")


if __name__ == "__main__":
    main()
