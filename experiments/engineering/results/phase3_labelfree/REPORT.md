# Phase 3 — Label-Free Pieces: Report

Date: 2026-10-25. Status: label-free work only. Human labelling is still
pending, so **nothing in this report is a claim about labelled accuracy**
(no F1, AUC, or precision/recall on the engineering resumes).

## Scope and constraints honoured

- Built ONLY the three label-free pieces below. Nothing label-dependent
  was touched, and no results here depend on human labels.
- NOT modified: `graph/engineering_graph.py`, `jds/jds.json`,
  `assignments.csv`, the labelling workbook, or the original v3 repo
  (`~/workspace/smart-hire-fix/Smart-Hire/` was imported read-only).
- NO attack cases invented: the security ablation uses only the repo's
  pre-existing sets. NO resume text, candidate names, or institution names
  are reproduced anywhere in this report or the JSON outputs (resume IDs
  and aggregate counts only).
- Attack payload text is never printed: only case IDs of missed attacks
  (in the JSON) and family-level counts are reported. Payloads were treated
  strictly as data inputs to the guardrail scanner.

## 1. Security per-layer ablation

### Method
The production guardrail's deterministic layers ARE separately invocable
through its public API — no workaround was needed:

- L1 = direct-imperative regex (`LAYER1_PATTERNS`, current 13-pattern set)
- L1_orig6 = first 6 LAYER1 patterns (the original v2 Regex_Only set; the
  identification is validated by exactly reproducing the v2 20.0% figure)
- L2 = `heuristic_regex_layer_2` (semantic-intent heuristic regex)
- L3 = `structural_layer` (zero-width/invisible unicode, delimiter blocks,
  consecutive-token bursts)
- ALL = `scan_document()['blocked']` (union of L1+L2+L3)

Mitigation = fraction of ATTACK cases blocked. FPR = fraction of BENIGN
cases blocked. Optional layers L4 (Prompt-Guard-2) and L5 (Llama Guard 3)
were NOT measured: L4 needs an HF token plus the transformers stack
(unavailable here), and L5 is a general safety classifier, not an
injection detector (per the module's own docstring), so it must never be
credited in injection-mitigation metrics.

### Sets (all pre-existing repo artifacts)
- **dev**: `data/security_per_case_v2.json` — 30 attacks, 25 benign.
- **heldout**: `data/heldout_per_case_results.json`, rows with
  `experiment == 'HeldOut_Security_Guardrails'` — 30 attacks, 25 benign.
  This is the pre-existing held-out set behind the v3 report's 56.7%.
- **generated_v3_regression**: `data/heldout_v3_cases.json`,
  `kind == 'security'` — 15 attacks, 16 benign. Per the v3 report (§5.4/§6)
  this generated set is a REGRESSION set, not a held-out set (its
  templates were used while generalising Layer 2). It is reported
  separately and must not be quoted as held-out performance.

### Results

| Set | Layer | Mitigation | FPR |
|---|---|---|---|
| dev (30A/25B) | L1 | 7/30 = 23.33% | 0/25 = 0% |
| dev | L1_orig6 | 6/30 = 20.00% | 0/25 = 0% |
| dev | L2 | 17/30 = 56.67% | 0/25 = 0% |
| dev | L3 | 4/30 = 13.33% | 0/25 = 0% |
| dev | ALL | **23/30 = 76.67%** | 0/25 = 0% |
| heldout (30A/25B) | L1 | 6/30 = 20.00% | 0/25 = 0% |
| heldout | L1_orig6 | 6/30 = 20.00% | 0/25 = 0% |
| heldout | L2 | 11/30 = 36.67% | 0/25 = 0% |
| heldout | L3 | 0/30 = 0% | 0/25 = 0% |
| heldout | ALL | **17/30 = 56.67%** | 0/25 = 0% |
| gen_v3_regression (15A/16B) | L1 | 0/15 = 0% | 0/16 = 0% |
| gen_v3_regression | L2 | 15/15 = 100% | 0/16 = 0% |
| gen_v3_regression | L3 | 0/15 = 0% | 0/16 = 0% |
| gen_v3_regression | ALL | **15/15 = 100%** | 0/16 = 0% |

Reconciliation with the v3 report: dev ALL 76.67%, held-out ALL 56.67%,
and generated-v3 100% reproduce the v3 report's §5.4 table exactly.
L1_orig6 reproduces the v2 Regex_Only 20.0% on dev, and L2 reproduces
the v2 Heuristic_Layer_2 56.67% on dev — both confirm the layer
identifications are correct.

### Marginal contribution of each layer (attacks caught ONLY by that layer)
- dev: L1-only 5, L2-over-L1 15, L3-over-(L1+L2) 1; the remaining 2
  blocked attacks are caught by both L1 and L2. Total 23.
- heldout: L1-only 6, L2-over-L1 11, L3-over-(L1+L2) 0. Total 17.
  Layer 3 adds nothing on held-out (no structural-obfuscation attacks
  in that set); its only marginal catch in the whole ablation is 1 dev
  attack.
- generated_v3: all 15 attacks are caught by L2 alone (L1 and L3 catch
  none) — expected, since the templates were built from L2's pattern
  vocabulary. This is why the set is a regression set, not evidence
  about unseen attacks.

### Per-family mitigation (ALL layers)
- dev (6 attacks per family): Direct_Imperative 6/6, Paraphrased_Semantic
  3/6, Obfuscated_Delimited 6/6, Roleplay_SocialEng 3/6,
  Tool_Exfiltration 5/6. Missed: 7 attacks (IDs in JSON).
- heldout (5 per family): Direct_Imperative 5/5, Paraphrased_Semantic 2/5,
  Obfuscated_Delimited 2/5, Roleplay_SocialEng 2/5, Tool_Exfiltration 4/5,
  Indirect_Document 2/5. Missed: 13 attacks (IDs in JSON).
- The weakest families on unseen attacks are paraphrase, roleplay, and
  indirect-document attacks — the guardrail's generalisation gap, not a
  direct-imperative gap (direct attacks are fully caught everywhere).

### Limitations (read before citing)
- Small, synthetic, same-authorship sets: dev and held-out share
  authorship, and all cases are template/short documents, not injected
  resumes. These numbers do NOT measure end-to-end injected-resume
  defence (that needs the labelled-phase harness).
- FPR 0% is measured on 25 + 25 + 16 benign controls only; the 95% upper
  bound on the true FPR from 0/66 is still ~4.5% (rule of three).
- L4/L5 unmeasured (see Method). No adaptive attacks were run here.

## 2. AOPC random-removal baseline

### Method and one interpretation note
AOPC follows the documented method of
`tools/shap_scoring_explainer.py::evaluate_feature_perturbation_faithfulness`,
re-implemented for the extended graph because the explainer hardcodes
the v3 tech graph and cannot run on the extended graph unmodified:

- Score = 100 × (approved requirements / 10), approval via
  `engineering_graph.evaluate_match` on tokens from `extract_tokens`.
- Closed-form Shapley per candidate token: each requirement's 100/10 is
  shared equally among the tokens that alone satisfy it (the game is
  separable — approval is a monotone OR over tokens — so single-token
  incidence is exact).
- AOPC_top (comprehensiveness): remove tokens in descending-Shapley
  order, k = 1..min(n_tokens, 5); AOPC = mean(baseline − score).
- AOPC_random (null baseline): same k range, tokens removed in a random
  order; mean over 5 random orders, seed 42.

Interpretation note: the task phrase "top-contributing requirements" is
implemented as top-Shapley candidate skill TOKENS, i.e. the explainer's
AOPC definition (requirements fixed). Removing requirements instead
would change the score denominator (100/M) and is not the documented
method, so it was not used.

### Sample
20 resumes: first 4 by numeric resume_id within each assigned-JD group
(`assignments.csv`): Civil 11890896, 21298336, 28005884, 31684925;
Electrical 12472574, 12748557, 16803215, 17103000; Mechanical 10985403,
12022566, 12488356, 12518008; Software 10624813, 11981094, 12011623,
13264796; Technician 10030015, 10219099, 10712803, 13149176.

### Results

| Subset | n | AOPC_top (Shapley order) | AOPC_random (mean of 5 orders) | Gap |
|---|---|---|---|---|
| All 20 | 20 | 48.40 | 19.03 | 29.37 |
| Eligible (baseline score > 0) | 19 | 50.95 | 20.04 | 30.91 |

- One resume is ineligible (baseline score 0.0, so removal cannot drop
  anything): 10030015 (Technician, 2 tokens).
- Per-resume AOPC_top ranges 0–100 and AOPC_random 0–72 (full per-resume
  table in `aopc_baseline.json`). The gap — Shapley ordering beats
  random ordering by ~30 points on average — is the result, not either
  number alone: random removal also drops the score substantially
  (mean ~19–20) because token sets are small (2–18 tokens) and removing
  1–5 tokens at random often hits a contributing token.
- AOPC_top is high when few tokens carry the score and low when tokens
  are redundant (e.g. 10985403: 18 tokens, baseline 100, AOPC_top only
  24.00, because many tokens satisfy the same requirements and Shapley
  shares split). That is what the metric measures, not a defect — but it
  means AOPC_top is not comparable across resumes with very different
  token counts without that context.

### Hub-token finding (flagged for Phase 2, graph NOT modified)
Verification of the extreme cases showed the token "Electrical
Engineering" alone satisfies all 10 Electrical JD requirements
(weighted graph distance ≤ 2 to every requirement). This drives
AOPC_top = 100.00 for 16803215 and 98.00 for 12472574: removing the
single hub token collapses the score. Consequence: any resume that
merely mentions its discipline name can score 100% on that discipline's
JD regardless of specific skills. The graph was left untouched per task
constraints, but this hub effect should be disclosed and discussed
before Phase 2 scores are interpreted — it inflates discipline-matched
scores and compresses discrimination between strong and weak
discipline-matched resumes.

### Limitations
- n = 20 sample, not the full 118; no human study (that needs recruited
  raters, a stretch item).
- AOPC here measures faithfulness of the token-level explanation to the
  deterministic score only; it does not show recruiters find the
  explanations useful.
- Baseline scores in this sample are high (many 100s), which is itself
  partly the hub effect above.

## 3. Blinded fairness check

### Method
Same 20-resume sample as §2. Blinded versions redact ONLY (a) the
candidate-name header line and (b) education-institution names harvested
from the resume's own education section (University/Institute/College/
School patterns + IIT/NIT forms), replaced everywhere they occur. All
experience/skill text is kept intact. Email addresses, phone numbers and
other header lines were NOT redacted (per spec) — so this is a partial
blinding check, not full anonymisation. Scores use the KG scorer
(`extract_tokens` + `evaluate_match` per JD requirement). No names,
institution names, or resume text are stored in outputs.

Exclusion rules: E1 = no name-like header line; E2 = no education
section or no institutions harvested; E3 = word-count loss > 5%;
E4 = zero replacements made.

### Results — primary check (name + institution): NOT RUNNABLE, n = 0
All 20 resumes were excluded (E1): **none has a candidate-name header.**
Their top lines are role titles (e.g. engineering-manager / technician
titles), not names — the source data is anonymised. This is a finding
about the dataset, not a pass: a name-blinding check cannot be run on
resumes that contain no names, and the earlier loose detector version
that reported 3 "included" resumes was in fact redacting section
headers/skill phrases ("Skill Highlights", "Microsoft Project") — those
runs were discarded after validation, and the detector was tightened
(first 2 non-empty lines only; role-word stoplist; strict full-line
education headers) before the final run.

### Results — supplementary check (institution-only): n = 19
Because names are absent, institution-only blinding was run as a
separately labelled supplementary check (no name step):

| Metric | Value |
|---|---|
| Included | 19/20 |
| Mean absolute score change | 0.0 points |
| Max absolute score change | 0.0 points |
| Resumes changed by ≥ 10 points | 0 |
| Resumes changed at all | 0 |
| Resumes whose token count changed | 0 |

Excluded: 16803215 (Electrical) — no education-section header found
(E2-inst). Per-resume table in `blinded_fairness.json`.

### How to read the zero (limitations — important)
- The KG scorer sees ONLY skill tokens, so institution strings can only
  move a score if they coincide with a graph node/alias. Token counts
  were unchanged in all 19, i.e. no harvested institution string was a
  skill token. The zero is therefore consistent with the scorer being
  identity-blind BY CONSTRUCTION for this input type — it rules out
  token-coincidence leakage, not identity effects in general.
- It says nothing about the LLM-agent parts of the pipeline (screening
  agent, dossier text), which do see full resume text and were not part
  of this check.
- The institution harvester is heuristic: institutions it misses stay
  in the text, which biases toward zero. Two harvester bugs were found
  and fixed during validation (a prose sentence starting with
  "education" matched as a section header; a "Qualifications" skills
  section matched as the education section) — the final rules are in
  the script, but unharvested institutions remain possible.
- n = 19 is small, and all 19 come from one anonymised source. A
  demographic subgroup audit was not attempted: the resumes carry no
  demographic labels, and inferring gender/race from names would be
  both unreliable here (no names) and methodologically unsound.

## Reproduction

Scripts (all under `~/workspace/smarthire-eng/phase3_scripts/`):
- `security_ablation.py` — imports the repo guardrail read-only; writes
  `results/phase3_labelfree/security_ablation.json`.
- `aopc_baseline.py` — extended-graph AOPC + random baseline (seed 42,
  5 orders); writes `results/phase3_labelfree/aopc_baseline.json`.
- `blinded_fairness.py` — primary + institution-only blinding; writes
  `results/phase3_labelfree/blinded_fairness.json`.

Run from the scripts directory with `python3 <script>.py`. Runtimes are
seconds (security), ~6 s (AOPC), ~3 s (blinded) on this VM. The v3 repo
is never written to; the graph module, JDs, assignments, and labelling
workbook are never written to.

## Files delivered

- `~/workspace/smarthire-eng/results/phase3_labelfree/REPORT.md` (this file)
- `~/workspace/smarthire-eng/results/phase3_labelfree/security_ablation.json`
- `~/workspace/smarthire-eng/results/phase3_labelfree/aopc_baseline.json`
- `~/workspace/smarthire-eng/results/phase3_labelfree/blinded_fairness.json`
- `~/workspace/smarthire-eng/phase3_scripts/security_ablation.py`
- `~/workspace/smarthire-eng/phase3_scripts/aopc_baseline.py`
- `~/workspace/smarthire-eng/phase3_scripts/blinded_fairness.py`

## 4. End-to-end injected-resume experiment (added by parent agent, 2026-10-25)

The L1 experiment: 30 resumes (first 6 by numeric ID per JD) each appended
with one reused dev-set attack payload as a final "Additional Notes:"
section, run through the full pipeline (guardrail first, then KG scorer on
the sanitized text when admitted, exactly as main.py does). Scoring uses
the FIXED extraction rule (extension hub/sub-hub tokens excluded). No
payload text is stored or printed; only sample IDs and families.

| Outcome | Count |
|---|---|
| Quarantined (no score produced) | 26/30 = 86.7% |
| Admitted | 4/30 |
| Admitted with any score change | 0/4 (mean change 0.0) |
| Downstream attack success (threshold cross up, or rise >= 10) | 0 |

By family (6 each): Direct_Imperative 6/6 blocked, Obfuscated_Delimited
6/6, Paraphrased_Semantic 4/6, Roleplay_SocialEng 5/6, Tool_Exfiltration
5/6. The 4 admitted payloads (PAR-04, PAR-06, ROL-06, TOL-04) are exactly
4 of the 7 attacks the standalone guardrail misses.

Two findings that must be stated precisely, not oversold:
- End-to-end quarantine (86.7%) EXCEEDS standalone dev mitigation
  (76.7%) because 3 attacks missed standalone (PAR-02, ROL-03, ROL-05)
  were blocked when embedded — all three via layer3_structural. Embedding
  a payload in a longer resume document trips the structural layer where
  the standalone short document did not. That is a genuine end-to-end
  effect, and it favours the defence here.
- The zero downstream change on admitted resumes is NOT evidence of
  sanitizer efficacy: for all 4 admitted cases the raw injected score
  already equalled the clean score (the payloads contained no JD skill
  tokens that move the score), so sanitization had nothing to neutralise.
  Downstream success is 0, but the mechanism is quarantine (26) plus
  score-neutral payloads (4) — not demonstrated sanitization.

Limitations: append-only embedding (mid-document and white-text
embeddings untested); single payload per resume; 30-resume sample; no
human labels involved (scores are system outputs, not accuracy claims).

## 5. AOPC re-run under the fixed extraction rule (added 2026-10-25)

Same 20-resume sample, same method and seed as §2, with extension
hub/sub-hub tokens excluded from extraction (script:
`phase3_scripts/aopc_baseline_fixed.py`, output
`aopc_baseline_fixed.json`). This supersedes the §2 numbers for citation.

| Subset | n | AOPC_top | AOPC_random | Gap |
|---|---|---|---|---|
| All 20 | 20 | 36.90 | 17.51 | 19.39 |
| Eligible (baseline > 0) | 17 | 43.41 | 20.60 | 22.81 |

The gap shrinks versus the preliminary run (29.37 / 30.91) once hub
inflation is removed, but Shapley ordering still beats random ordering
clearly. The fix is visible at resume level: 16803215 (Electrical) goes
from baseline 100.0 (hub-driven) to 0.0, and eligible n falls 19 -> 17.
10985403 (Mechanical) still baselines at 100.0 with 13 tokens — a
genuinely skilled resume, not a hub artefact. The human explanation study
still needs recruited raters; the random baseline does not substitute
for it.

## Open items for the parent agent (not blockers for this delivery)
- Phase 2 (labelled benchmarks) still gated by human labels — untouched.
- The discipline-hub effect (§2) should be disclosed when Phase 2
  scores are interpreted; whether to adjust the graph is a parent/user
  decision, not something done here.
- The human explanation study (AOPC human arm) still needs recruited
  raters; the random baseline here does not substitute for it.
