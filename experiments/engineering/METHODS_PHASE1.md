# SmartHire Engineering Experiment — Phase 1 Methods Record
Date: 25 October 2026. Status: Phase 1 complete. Phase 2 gated on human labels.

## 1. Data
- 118 engineering resume PDFs uploaded by the user on 2026-10-25 (numeric
  filenames, e.g. 10030015.pdf). All 118 extracted cleanly with pdftotext
  (median 786 words, min 157, max 2579, zero empty). Extracted texts stored in
  `data/` (working copies; original PDFs untouched in `~/workspace/user/files/`).
- Kaggle dataset name/link: STILL NEEDED from the user (required for the
  reproducibility statement; the PDFs themselves do not carry it).

## 2. Resume-to-JD assignment (independent of the system under evaluation)
- Method: title-led scoring in `assign_roles.py`. A discipline-specific title
  phrase scores 5 for its role; each distinctive skill term scores 1; a generic
  engineering title (design/project/quality/test/production/...) adds 2 to the
  role already leading on skills. Assignment uses stated titles and skills
  ONLY — never the KG scorer — so assignment cannot leak the system's own
  judgement into the ground truth.
- Result: Mechanical 45, Technician 32, Electrical 19, Software 16, Civil 6
  (total 118). Flags: 81 OK, 37 REVIEW (margin < 3 or top score < 5).
- Known imperfection, handled by design: 8 Technician-assigned resumes also
  carry a discipline engineer title, and 5 Technician assignments have margin
  < 3. The labelling sheet asks the rater to confirm every assignment
  ("Confirm assignment" column); analysis will use CORRECTED assignments and
  report the correction count. REVIEW rows are not excluded.
- Civil is small (n = 6). It is kept as a fifth JD for completeness, but its
  per-JD metrics will be reported as descriptive only; the headline results
  are pooled across JDs, and per-JD reporting emphasises groups with n >= 10.

## 3. Knowledge-graph extension (the ontology work)
- The original v3 graph (`tools/knowledge_graph_tool.py`) is UNTOUCHED:
  70 nodes / 74 edges, weights 67x1, 3x2, 1x3, 2x4, 1x5 (verified on import).
- New module `graph/engineering_graph.py` imports `build_tech_graph()` and
  ADDS 4 clusters: Mechanical (29 nodes: hub + Design/Manufacturing/
  Thermal & Fluids/Analysis sub-hubs), Electrical (22), Civil (16),
  Technician (16), plus 6 heavy bridges (Mech-Elec 4, Elec-Tech 2,
  Mech-Tech 2, Civil-Mech 4, Mech-Backend 5, Elec-DevOps 4).
- Extended graph verified: 153 nodes, 159 edges, weights 146x1, 5x2, 1x3,
  5x4, 2x5. Original 70 nodes preserved (asserted).
- Sub-hub design choice (documented, deliberate): transfer stays WITHIN a
  sub-discipline (siblings via their sub-hub = distance 2, TRANSFERABLE).
  Cross-sub-discipline paths are >= 3 by construction and do NOT approve.
  This is stricter than a flat hub design and mirrors v3's own stack-local
  edges (e.g. JavaScript-React).
- Aliases added (engineering only, conservative true synonyms): solid works,
  auto cad, computer-aided design -> CAD, cadd, finite element analysis ->
  FEA, staad pro, rcc -> Reinforced Concrete, programmable logic controller
  -> PLC, supervisory control and data acquisition -> SCADA, preventative
  maintenance, repair -> Equipment Repair, trouble shooting, diagnostic ->
  Diagnostics, html -> HTML5, css -> CSS3.
- Validation: (a) the parameterised matcher reproduces v3's
  `evaluate_skill_match` exactly on 15/15 test pairs over the ORIGINAL graph;
  (b) 10/11 engineering spot checks pass; the one "failure" was a wrong test
  expectation, corrected: HTML vs CSS is distance 4 in the ORIGINAL v3 graph
  (both are weight-2 spokes off Frontend), so GAP is faithful v3 behaviour,
  not an extension bug.
- KNOWN v3 PROPERTY, disclosed, with a pre-registered sensitivity check:
  hub/sub-hub nodes are themselves extractable tokens (e.g. a resume saying
  "manufacturing" extracts the "Manufacturing" token, which approves "CNC" at
  distance 1). This mirrors v3 exactly (a resume saying "backend" extracts
  "Backend", approving "Python" at distance 1). The main experiment keeps
  v3-faithful behaviour for comparability; Phase 2 will re-score with hub
  tokens EXCLUDED from extraction and report whether conclusions change.

## 4. Job descriptions (final)
- 5 JDs x 10 requirements in `jds/jds.json` and `jds/JDs_FINAL.md`.
  Requirements chosen by frequency within the assigned group plus standard
  posting practice; JDs were NOT fitted to individual resumes.
- Software JD uses the ORIGINAL v3 tech graph only (no new software nodes):
  Python, Java, JavaScript, SQL, Git, Docker, REST, AWS, HTML, CSS
  (HTML/CSS canonicalised to HTML5/CSS3 by aliases).
- Civil JD caveat: the group is site/concrete-focused (STAAD/ETABS 0/6), so
  the JD is a standard site/structural posting and several Civil resumes are
  expected to score low. That is legitimate negative signal, not a defect.

## 5. Extraction audit (L5 progress, from reading the v3 code)
- Skill extraction in the v3 pipeline is DETERMINISTIC, not LLM-based:
  `extract_candidate_skill_tokens` matches graph nodes + aliases (+ a small
  hardcoded tech token list) with word boundaries. The LLM agents only
  NARRATE the deterministic Graph_ATS score, which they are instructed to
  reproduce verbatim. The paper's methods must state this precisely (it
  resolves the "black box" concern in the scorer's favour).
- Remaining L5 measurements for Phase 2: (a) screening-agent score
  preservation compliance (dossier score vs Graph_ATS -- measurable only if
  the agent path can run here; it needs the CrewAI/Gemini stack and possibly
  the user's API key, to be checked at Phase 2); (b) extraction accuracy
  against a silver-standard skill set derived from resumes' own Skills
  sections (disclosed as silver, not gold).

## 6. Labelling protocol (the ground truth)
- File: `labeling/SmartHire_Engineering_Labeling_Sheet.xlsx` (also copied to
  `~/workspace/your_files/` for delivery).
- One tab per JD (118 rows total) + README + Rubric + Second_Rater (30 rows,
  stratified systematic sample: Mech 12, Tech 8, Elec 5, Soft 3, Civil 2) +
  Summary (formula-driven counts).
- Rule: for each requirement mark Y iff the resume EVIDENCES it (used in a
  job/project/coursework with context; a bare skills-list keyword does NOT
  count). Evidence count and Qualified are FORMULAS: Qualified = Y iff
  evidence >= 7 of 10. Human judgement lives in the requirement marks; the
  label follows the rubric mechanically. An Override/notes column records
  any exception the rater argues for; overrides are reported, not hidden.
- Second rater fills evidence count + qualified for the 30 sample rows
  WITHOUT seeing the first rater's marks, for Cohen's kappa.
- Return format: the same file, tabs/rows unchanged. Analysis reads it as-is.

## 7. What Phase 2 will do (once labels arrive)
- Score all 118 against their (corrected) JD with all scorers (exact, alias,
  TF-IDF, KG) at the pre-declared 50% threshold; pooled + per-JD F1/AUC with
  Wilson/bootstrap CIs and McNemar KG-vs-baseline tests.
- UNMAPPED rate on all 118 resumes and on JD requirements; d in {1,2,3}
  sensitivity sweep; hub-token-exclusion sensitivity re-score.
- Redesigned ablation table (structural-zero arms reframed as controls;
  guardrail on/off measured on injected resumes in Phase 3, not on clean data).

## 8. Phase 3 label-free addendum (2026-10-25; full report in results/phase3_labelfree/REPORT.md)
- Security per-layer ablation (repo's pre-existing sets only): dev (30A/25B)
  L1 7/30, L2 17/30, L3 4/30, ALL 23/30 (76.7%), FPR 0/25; held-out L1 6/30,
  L2 11/30, L3 0/30, ALL 17/30 (56.7%), FPR 0/25. Reproduces the v3 report
  exactly, plus the new decomposition: L2 carries the system; L3 adds only
  1 dev attack and nothing held-out; weakest unseen families are paraphrase,
  roleplay and indirect-document. Generated-v3 set 15/15 via L2 alone is a
  regression set, not held-out. L4/L5 unmeasured (HF token unavailable;
  L5 is not an injection detector).
- AOPC random baseline (n=20, 4 per JD), RE-RUN under the fixed extraction
  rule (supersedes the preliminary 48.40 vs 19.03): AOPC_top 36.90 vs
  AOPC_random 17.51 (gap 19.39) on all 20; eligible n=17: 43.41 vs 20.60
  (gap 22.81). Resume 16803215 (Electrical) falls from baseline 100.0
  (hub-driven) to 0.0 under the fix.
- End-to-end injected-resume experiment (30 resumes, reused dev payloads,
  appended "Additional Notes:" section, full guardrail -> scorer pipeline,
  fixed extraction): 26/30 quarantined (86.7%), 4 admitted, 0 downstream
  successes, 0 score change on admitted. Quarantine exceeds standalone
  dev mitigation (76.7%) because 3 standalone-missed attacks were blocked
  when embedded, all via layer3_structural. The 4 admitted payloads were
  score-neutral even unscored, so zero change is NOT sanitizer efficacy.
  Full numbers in results/phase3_labelfree/REPORT.md §§4-5 and
  endtoend_injected.json.
- DISCIPLINE-HUB EFFECT (verified by the parent agent, not just the
  subagent): the token "Electrical Engineering" alone approves 10/10
  Electrical JD requirements, and likewise for Mechanical, Civil and
  Technician hubs (hub -> sub-hub -> skill = distance 2). Any resume
  merely stating its degree discipline would score 100% on that
  discipline's JD. Sub-hub tokens inflate too ("Manufacturing" approves
  "CNC" at distance 1). FIX DECISION (pre-registered before Phase 2
  scoring): primary Phase 2 scoring EXCLUDES structural nodes (extension
  hubs and sub-hubs) from the extraction vocabulary -- they structure the
  graph but are not skills. v3-faithful scoring (hubs extractable) is
  reported as a sensitivity analysis quantifying the inflation. The graph
  itself is NOT changed; the fix is in the harness extraction rule. Human
  labels are unaffected (they judge evidence, not tokens).
- Fairness: primary name+institution blinding NOT RUNNABLE (n=0) -- the
  resumes are anonymised and carry no candidate-name headers (the
  subagent's loose first detector, which reported 3 inclusions by
  redacting section headers, was caught and discarded on validation).
  Institution-only supplementary check (n=19): mean/max score change 0.0.
  Read narrowly as "no token-coincidence leakage", NOT as fairness proof:
  the KG scorer sees only skill tokens, and LLM-agent identity effects
  are untestable on this anonymised data -- a stated paper limitation.

## 9. Open items needing the user
- Completed labelling sheet (the Phase 2 gate).
- Kaggle dataset name/link for the reproducibility statement.
- A second rater for the 30-row sample (stretch item).
- 15-20 raters for the human explanation study (Phase 3 stretch item).
- Optional: a small user-authored held-out attack set (Phase 3 stretch item).
