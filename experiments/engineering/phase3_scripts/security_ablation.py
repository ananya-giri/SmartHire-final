"""Phase 3 (label-free) — Security per-layer ablation.

Runs the production guardrail's deterministic layers separately on the repo's
EXISTING security sets only. No attack cases are invented here.

Layers (from security_guardrails.py, imported read-only, never modified):
  L1        = _any_match(LAYER1_PATTERNS, text) — current 13-pattern set
  L1_orig6  = first 6 LAYER1 patterns (the original v2 Regex_Only set;
              identification validated by reproducing the v2 6/30 result)
  L2        = heuristic_regex_layer_2(text)
  L3        = structural_layer(text)
  ALL       = scan_document(text)['blocked']  (union of L1+L2+L3)

Sets (all pre-existing repo artifacts; nothing generated here):
  dev      = Smart-Hire/data/security_per_case_v2.json (55: 30 attacks, 25 benign)
  heldout  = Smart-Hire/data/heldout_per_case_results.json, rows with
             experiment == 'HeldOut_Security_Guardrails' (the pre-existing
             held-out set behind the v3 report's 56.7% figure)
  gen_v3   = Smart-Hire/data/heldout_v3_cases.json, kind == 'security' only.
             NOTE: per RESEARCH_REPORT_V3_FINAL.md §5.4/§6 this generated set
             is a REGRESSION set, not a held-out set (its templates were used
             while generalising Layer 2), so it is reported separately and
             must not be quoted as held-out performance.

Mitigation = fraction of ATTACK cases blocked. FPR = fraction of BENIGN
cases blocked. Payload text is never printed: only case IDs and counts are
reported (payloads are data inputs to the scanner, never instructions).
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
BASE = os.path.join(REPO, "experiments", "engineering")
OUT = os.path.join(BASE, "results", "phase3_labelfree")
sys.path.insert(0, REPO)
from security_guardrails import (  # noqa: E402  (read-only import)
    LAYER1_PATTERNS, _any_match, heuristic_regex_layer_2,
    structural_layer, AIHiringGuardrails,
)

L1_ORIG6 = LAYER1_PATTERNS[:6]


def is_attack(v):
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() == "true"


def layer_hits(text):
    t = text or ""
    return {
        "L1": _any_match(LAYER1_PATTERNS, t.lower()),
        "L1_orig6": _any_match(L1_ORIG6, t.lower()),
        "L2": heuristic_regex_layer_2(t),
        "L3": structural_layer(t),
        "ALL": AIHiringGuardrails.scan_document(t)["blocked"],
    }


def evaluate(cases, id_key, text_key, attack_key, family_key):
    layers = ["L1", "L1_orig6", "L2", "L3", "ALL"]
    per_layer = {l: {"tp": 0, "fp": 0, "n_attack": 0, "n_benign": 0} for l in layers}
    per_family = defaultdict(lambda: {l: 0 for l in layers})
    family_n = Counter()
    missed = defaultdict(list)  # layer -> case IDs of attacks NOT blocked
    for c in cases:
        atk = is_attack(c[attack_key])
        fam = c.get(family_key, "unknown")
        hits = layer_hits(c[text_key])
        for l in layers:
            if atk:
                per_layer[l]["n_attack"] += 1
                if hits[l]:
                    per_layer[l]["tp"] += 1
                else:
                    missed[l].append(c[id_key])
            else:
                per_layer[l]["n_benign"] += 1
                if hits[l]:
                    per_layer[l]["fp"] += 1
        if atk:
            family_n[fam] += 1
            for l in layers:
                if hits[l]:
                    per_family[fam][l] += 1
    # Always emit every layer key, even when a layer missed nothing.
    for l in layers:
        missed.setdefault(l, [])
    return per_layer, dict(family_n), dict(per_family), dict(missed)


def main():
    dev = json.load(open(f"{REPO}/data/security_per_case_v2.json"))
    held_rows = json.load(open(f"{REPO}/data/heldout_per_case_results.json"))
    held = [{"case_id": c.get("case_id", f"HELD-{i}"), "text": c["text"],
             "is_attack": str(c["is_attack"]) == "True",
             "family": c.get("family", "heldout")}
            for i, c in enumerate(held_rows)
            if c.get("experiment") == "HeldOut_Security_Guardrails"]
    v3 = json.load(open(f"{REPO}/data/heldout_v3_cases.json"))["cases"]
    gen_v3 = [c for c in v3 if c.get("kind") == "security"]

    out = {}
    for name, cases, idk, atk, fam in [
        ("dev", dev, "sample_id", "is_attack", "family"),
        ("heldout", held, "case_id", "is_attack", "family"),
        ("generated_v3_regression", gen_v3, "case_id", "is_attack", "family"),
    ]:
        pl, fn, pf, missed = evaluate(cases, idk, "text", atk, fam)
        out[name] = {
            "n_cases": len(cases),
            "n_attack": sum(1 for c in cases if is_attack(c[atk])),
            "n_benign": sum(1 for c in cases if not is_attack(c[atk])),
            "per_layer": {
                l: {
                    "mitigation": f"{v['tp']}/{v['n_attack']}",
                    "mitigation_pct": round(100.0 * v["tp"] / v["n_attack"], 2) if v["n_attack"] else None,
                    "fpr": f"{v['fp']}/{v['n_benign']}",
                    "fpr_pct": round(100.0 * v["fp"] / v["n_benign"], 2) if v["n_benign"] else None,
                }
                for l, v in pl.items()
            },
            "per_family_attacks": fn,
            "per_family_blocked": pf,
            "missed_attack_ids": missed,
        }
        print(f"== {name}: {out[name]['n_cases']} cases "
              f"({out[name]['n_attack']} attacks, {out[name]['n_benign']} benign)")
        for l, v in out[name]["per_layer"].items():
            print(f"   {l}: mitigation {v['mitigation']} ({v['mitigation_pct']}%)  "
                  f"FPR {v['fpr']} ({v['fpr_pct']}%)")

    json.dump(out, open(os.path.join(OUT, "security_ablation.json"), "w"), indent=1)
    print("wrote security_ablation.json")


if __name__ == "__main__":
    main()
