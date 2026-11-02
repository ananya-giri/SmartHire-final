"""Phase 3 (label-free) — Blinded fairness check.

For the same 20-resume sample as aopc_baseline.py (first 4 by numeric
resume_id per JD group), build a blinded version of each resume by redacting
ONLY:
  (a) the candidate-name header line (first name-like line among the first
      6 non-empty lines; title lines such as CURRICULUM VITAE are skipped),
  (b) education-institution names harvested from the resume's own education
      section (University / Institute / College / School patterns + IIT/NIT
      forms), replaced everywhere they occur.
All experience/skill text is kept intact. Email addresses, phone numbers and
other header lines are NOT redacted (per spec) — so this is a partial
blinding check, not full anonymisation; see REPORT.md limitations.

Exclusion (resume dropped from the comparison, with reason):
  E1 no name-like header line found in the first 6 non-empty lines
  E2 no education section found, or zero institution names harvested
  E3 word-count loss after redaction > 5% (sanity: redaction must be local)
  E4 zero replacements made

Scoring: KG scorer (extract_tokens + evaluate_match per JD requirement,
score = 100 * approved / 10), clean vs blinded. No names, institution names
or resume text are written to disk — only resume IDs and numbers.
"""
import csv
import json
import re
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

TITLE_WORDS = {"curriculum", "vitae", "resume", "cv", "biodata"}
BAD_LINE_WORDS = {"resume", "curriculum", "vitae", "objective", "profile",
                  "summary", "contact", "phone", "email", "address",
                  "education", "experience", "skills", "linkedin", "career"}
# Role words: a header line containing one cannot be a person's name
# (guards against role-title headers such as "QA ENGINEERING TEAM LEAD"
# or "Mechanical Engineer" being mistaken for a name).
ROLE_WORDS = {"engineer", "engineering", "developer", "manager", "analyst",
              "technician", "lead", "consultant", "specialist", "designer",
              "supervisor", "team", "director", "coordinator"}
# Strict header match: a full short header line, NOT a prose sentence that
# merely starts with "education" (e.g. "education and prior work...").
SECTION_START = re.compile(
    r"^(education|academic qualifications|educational background|academics|"
    r"education and training|education history)\s*:?$", re.I)
# NOTE: "qualifications" alone is deliberately NOT an education header: in
# these resumes it heads a skills list, and matching it first caused the
# harvester to scan the skills section instead of the education section
# (found and fixed during validation).
NEXT_SECTION_WORDS = (
    "experience", "work experience", "employment", "professional experience",
    "skills", "technical skills", "projects", "certifications", "training",
    "achievements", "summary", "objective", "personal details", "declaration",
    "references", "hobbies", "work history", "career history")
INST_A = re.compile(
    r"\b([A-Z][A-Za-z&.'-]*(?:\s+[A-Z][A-Za-z&.'-]*){0,4}\s+"
    r"(?:University|Institute|College|School))\b")
INST_B = re.compile(r"\bUniversity of [A-Z][A-Za-z&.'-]*(?:\s+[A-Z][A-Za-z&.'-]*){0,3}")
INST_C = re.compile(r"\b(?:IIT|NIT|IIIT)\s+[A-Z][A-Za-z&.'-]*(?:\s+[A-Z][A-Za-z&.'-]*){0,2}")


def is_name_like(line):
    s = line.strip()
    if not s or any(ch.isdigit() for ch in s) or "@" in s or "http" in s.lower():
        return False
    words = s.split()
    if not (2 <= len(words) <= 4):
        return False
    low = s.lower()
    if any(w in low for w in BAD_LINE_WORDS):
        return False
    if any(w.lower().strip(".,") in ROLE_WORDS for w in words):
        return False
    if not all(re.fullmatch(r"[A-Za-z][A-Za-z.'-]*", w) for w in words):
        return False
    if all(w.lower() in TITLE_WORDS for w in words):
        return False
    return True


def find_name_header(lines):
    # A candidate-name header, if present, sits at the very top of a resume.
    # Searching deeper misfires on section headers ("Skill Highlights") and
    # skill-list items ("Microsoft Project"), so only the first 2 non-empty
    # lines (after skipping pure title lines) are considered.
    nonempty = [(i, ln) for i, ln in enumerate(lines) if ln.strip()]
    for i, ln in nonempty[:2]:
        s = ln.strip()
        if all(w.lower() in TITLE_WORDS for w in s.split()):
            continue
        if is_name_like(ln):
            return i, s
    return None, None


def harvest_institutions(lines):
    start = end = None
    for i, ln in enumerate(lines):
        s = ln.strip()
        if start is None and SECTION_START.match(s):
            start = i
            continue
        if start is not None:
            # Next-section header: short line, no sentence punctuation,
            # starting with a known section word.
            sl = s.lower()
            if (len(s) <= 40 and len(s.split()) <= 5 and not s.endswith(".")
                    and any(sl.startswith(w) for w in NEXT_SECTION_WORDS)):
                end = i
                break
    if start is None:
        return None, []
    section = "\n".join(lines[start:(end or len(lines))])
    found = set()
    for rx in (INST_A, INST_B, INST_C):
        for m in rx.finditer(section):
            name = re.sub(r"\s+", " ", m.group(0)).strip(" .,;:")
            words = name.split()
            if len(words) >= 2 and not name.lower().startswith(("the ", "of ", "and ")):
                found.add(name)
    return section, sorted(found, key=len, reverse=True)


def blind(text):
    lines = text.split("\n")
    name_idx, name = find_name_header(lines)
    if name is None:
        return None, "E1", 0, 0
    _, institutions = harvest_institutions(lines)
    if not institutions:
        return None, "E2", 0, 0
    out = lines[:]
    out[name_idx] = "[NAME]"
    joined = "\n".join(out)
    n_repl = 1
    # full-name occurrences elsewhere (same name string, not extra content)
    joined, n1 = re.subn(rf"(?i)\b{re.escape(name)}\b", "[NAME]", joined)
    n_repl += n1
    for inst in institutions:
        joined, n2 = re.subn(rf"(?i)\b{re.escape(inst)}\b", "[INSTITUTION]", joined)
        n_repl += n2
    w0, w1 = len(text.split()), len(joined.split())
    if w0 and (w0 - w1) / w0 > 0.05:
        return None, "E3", 0, 0
    if n_repl <= 1:
        return None, "E4", 0, 0
    return joined, None, n_repl, len(institutions)


def blind_institutions_only(text):
    """Supplementary variant: redact institution names only (no name step).
    Used because this resume sample carries no candidate-name headers at
    all (anonymised source data, role-title headers), which makes the
    primary name+institution check vacuous; institution blinding is still
    a meaningful, separately reported check."""
    lines = text.split("\n")
    _, institutions = harvest_institutions(lines)
    if not institutions:
        return None, 0
    joined = text
    n_repl = 0
    for inst in institutions:
        joined, n2 = re.subn(rf"(?i)\b{re.escape(inst)}\b", "[INSTITUTION]", joined)
        n_repl += n2
    if n_repl == 0:
        return None, 0
    return joined, len(institutions)


def kg_score(text, reqs, graph):
    toks = extract_tokens(text, graph)
    ok = sum(1 for r in reqs if evaluate_match(r, toks, graph)["is_approved"])
    return 100.0 * ok / len(reqs), len(toks)


def main():
    graph = build_engineering_graph()
    jds = json.load(open(f"{BASE}/jds/jds.json"))
    groups = defaultdict(list)
    for row in csv.DictReader(open(f"{BASE}/assignments.csv")):
        groups[row["assigned_jd"]].append(row["resume_id"])
    sample = []
    for jd in sorted(groups):
        for rid in sorted(groups[jd], key=int)[:4]:
            sample.append((rid, jd))
    assert len(sample) == 20

    rows, excluded = [], []
    inst_rows, inst_excluded = [], []
    for rid, jd in sample:
        text = open(f"{BASE}/data/{rid}.txt").read()
        reqs = jds[jd]["requirements"]
        blinded, reason, n_repl, n_inst = blind(text)
        if blinded is None:
            excluded.append({"resume_id": rid, "jd": jd, "reason": reason})
            print(f"{rid} [{jd}] PRIMARY EXCLUDED {reason}")
        else:
            s_clean, nt_clean = kg_score(text, reqs, graph)
            s_blind, nt_blind = kg_score(blinded, reqs, graph)
            rows.append({
                "resume_id": rid, "jd": jd,
                "score_clean": round(s_clean, 2), "score_blinded": round(s_blind, 2),
                "delta": round(s_blind - s_clean, 2), "abs_delta": round(abs(s_blind - s_clean), 2),
                "tokens_clean": nt_clean, "tokens_blinded": nt_blind,
                "n_institutions_harvested": n_inst, "n_replacements": n_repl,
            })
            print(f"{rid} [{jd}] PRIMARY clean={s_clean:.0f} blinded={s_blind:.0f} "
                  f"delta={s_blind - s_clean:+.0f} tokens {nt_clean}->{nt_blind}")
        # Supplementary institution-only blinding (no name step).
        blinded2, n_inst2 = blind_institutions_only(text)
        if blinded2 is None:
            inst_excluded.append({"resume_id": rid, "jd": jd,
                                  "reason": "E2-inst: no institutions harvested"})
        else:
            s_clean, nt_clean = kg_score(text, reqs, graph)
            s_blind, nt_blind = kg_score(blinded2, reqs, graph)
            inst_rows.append({
                "resume_id": rid, "jd": jd,
                "score_clean": round(s_clean, 2), "score_blinded": round(s_blind, 2),
                "delta": round(s_blind - s_clean, 2), "abs_delta": round(abs(s_blind - s_clean), 2),
                "tokens_clean": nt_clean, "tokens_blinded": nt_blind,
                "n_institutions_harvested": n_inst2,
            })
            print(f"{rid} [{jd}] INST-ONLY clean={s_clean:.0f} blinded={s_blind:.0f} "
                  f"delta={s_blind - s_clean:+.0f} tokens {nt_clean}->{nt_blind}")

    def summarise(rs):
        deltas = [r["abs_delta"] for r in rs]
        return {
            "n_included": len(rs),
            "mean_abs_delta": round(sum(deltas) / len(deltas), 4) if deltas else None,
            "max_abs_delta": max(deltas) if deltas else None,
            "n_delta_ge_10": sum(1 for d in deltas if d >= 10),
            "n_delta_nonzero": sum(1 for d in deltas if d > 0),
            "n_token_count_changed": sum(1 for r in rs if r["tokens_clean"] != r["tokens_blinded"]),
        }

    summary = {"n_sample": 20, "primary": summarise(rows),
               "primary_excluded": excluded,
               "institution_only": summarise(inst_rows),
               "institution_only_excluded": inst_excluded}
    print(json.dumps(summary, indent=1))
    json.dump({"primary_rows": rows, "institution_only_rows": inst_rows,
               "summary": summary},
              open(f"{OUT}/blinded_fairness.json", "w"), indent=1)
    print("wrote blinded_fairness.json")


if __name__ == "__main__":
    main()
