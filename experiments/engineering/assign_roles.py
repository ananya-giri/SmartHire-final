"""Assign each of the 118 engineering resumes to its nearest JD role (v2).

Method (transparent, title-led, NOT using the KG scorer -- assignment must be
independent of the system under evaluation):
  - A discipline-specific title phrase scores 5 for that role.
  - Each distinctive skill term scores 1 for its role.
  - A generic engineering title (design/project/quality/test/production/...)
    adds 2 to whichever role already leads on skills (it confirms the person
    is an engineer; the discipline comes from their skills).
  - Flags: OK (top >= 5 and margin >= 3), REVIEW (assigned but margin < 3 or
    top < 5 -- user confirms assignment on the labeling sheet),
    OUTLIER (no engineering signal at all -- candidate for documented exclusion).
Outputs: assignments.csv, assignment_summary.json, group_skill_freq.json
"""
import glob, os, re, json, csv
from collections import Counter

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.dirname(os.path.abspath(__file__))

TITLES = {
    "Mechanical": ["mechanical engineer", "mechanical engineering"],
    "Electrical": ["electrical engineer", "electrical engineering", "electronics engineer"],
    "Civil": ["civil engineer", "civil engineering", "structural engineer",
              "site engineer", "construction engineer"],
    "Software": ["software engineer", "software developer", "java developer",
                 "python developer", "web developer", "dotnet developer",
                 ".net developer", "application developer", "programmer",
                 "data analyst", "data scientist"],
    "Technician": ["engineering technician", "field service technician",
                   "maintenance technician", "service technician",
                   "repair technician", "test technician", "field technician"],
}
GENERIC_TITLES = ["design engineer", "project engineer", "quality engineer",
                  "test engineer", "production engineer", "maintenance engineer",
                  "automation engineer", "process engineer", "manufacturing engineer",
                  "industrial engineer", "systems engineer", "field engineer",
                  "product engineer", "reliability engineer"]
SKILLS = {
    "Mechanical": ["solidworks", "catia", "ansys", "autocad", "cnc", "thermodynamics",
                   "fluid mechanics", "gd&t", "hvac", "manufacturing processes",
                   "tolerance analysis", "lathe", "milling", "casting", "welding",
                   "finite element", "fea", "cad", "cam", "lean manufacturing",
                   "six sigma", "production planning", "machine design",
                   "process improvement", "material selection"],
    "Electrical": ["plc", "scada", "embedded systems", "control systems",
                   "power distribution", "circuit design", "matlab", "simulink",
                   "vlsi", "power systems", "electrical maintenance", "instrumentation",
                   "transformer", "motor control", "automation", "panel wiring",
                   "electrical design"],
    "Civil": ["staad", "etabs", "surveying", "estimation", "structural analysis",
              "building construction", "quantity estimation", "concrete",
              "reinforced concrete", "site execution", "bar bending",
              "land surveying", "structural design"],
    "Software": ["python", "java", "javascript", "react", "sql", "rest api",
                 "node.js", "html", "css", "git", "docker", "aws", "machine learning",
                 "data structures", "algorithms", "c++", "spring boot", "django",
                 "unit testing", "debugging"],
    "Technician": ["troubleshooting", "equipment maintenance", "repair",
                   "calibration", "preventive maintenance", "safety compliance",
                   "schematics", "hand tools", "diagnostic", "installation",
                   "testing equipment", "equipment repair", "field service",
                   "maintenance procedures"],
}

def wb(term, text):
    return bool(re.search(r"(?i)(?:\b|_)" + re.escape(term) + r"(?:\b|_)", text))

rows = []
for path in sorted(glob.glob(os.path.join(DATA, "*.txt"))):
    rid = os.path.basename(path)[:-4]
    text = open(path, errors="ignore").read()
    scores = {}
    for role in TITLES:
        hits_t = [t for t in TITLES[role] if wb(t, text)]
        hits_s = [t for t in SKILLS[role] if wb(t, text)]
        scores[role] = 5 * len(hits_t) + len(hits_s)
    if any(wb(t, text) for t in GENERIC_TITLES):
        lead = max(scores, key=scores.get)
        if scores[lead] > 0:
            scores[lead] += 2
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    top_role, top_score = ranked[0]
    second_score = ranked[1][1]
    margin = top_score - second_score
    eng_signal = bool(re.search(r"(?i)\bengineer(ing)?\b|\btechnician\b", text))
    if top_score < 3 and not eng_signal:
        flag, assigned = "OUTLIER", ""
    elif top_score >= 5 and margin >= 3:
        flag, assigned = "OK", top_role
    else:
        flag, assigned = "REVIEW", top_role
    rows.append({"resume_id": rid, "assigned_jd": assigned,
                 "scores": scores, "margin": margin, "flag": flag})

with open(os.path.join(OUT, "assignments.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["resume_id", "assigned_jd", "mech", "elec", "civil", "soft",
                "technician", "margin", "flag"])
    for r in rows:
        s = r["scores"]
        w.writerow([r["resume_id"], r["assigned_jd"], s["Mechanical"],
                    s["Electrical"], s["Civil"], s["Software"], s["Technician"],
                    r["margin"], r["flag"]])

summary = Counter(r["assigned_jd"] or "OUTLIER" for r in rows)
flags = Counter(r["flag"] for r in rows)
print("assigned counts:", dict(summary))
print("flags:", dict(flags))
for r in rows:
    if r["flag"] == "OUTLIER":
        print(f"  OUTLIER {r['resume_id']}: {r['scores']}")

freq = {}
for role in TITLES:
    members = [r for r in rows if r["assigned_jd"] == role]
    texts = [open(os.path.join(DATA, r["resume_id"] + ".txt"), errors="ignore").read()
             for r in members]
    c = Counter()
    for term in set(SKILLS[role]):
        c[term] = sum(1 for t in texts if wb(term, t))
    freq[role] = {"n": len(members), "skill_files": dict(c.most_common())}
with open(os.path.join(OUT, "group_skill_freq.json"), "w") as f:
    json.dump(freq, f, indent=1)
print(json.dumps(freq, indent=1))
