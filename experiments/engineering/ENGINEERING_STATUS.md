# Engineering Experiment — Status

Date: 25 October 2026.

## Done
- Phase 1: 118 engineering resumes profiled and assigned to 5 JDs
  (Mechanical 45, Technician 32, Electrical 19, Software 16, Civil 6);
  knowledge-graph extension built and verified (153 nodes / 159 edges;
  original v3 graph untouched); 5 final JDs; human-labelling workbook
  delivered (118 rows + 30-row second-rater sample).
- Phase 3 (label-free): per-layer security ablation (dev ALL 23/30,
  held-out ALL 17/30, FPR 0); end-to-end injected-resume experiment
  (26/30 quarantined, 0 downstream successes); AOPC + random baseline
  re-run under the fixed extraction rule (36.90 vs 17.51, gap 19.39);
  blinded fairness check (primary not runnable — anonymised data, n=0;
  institution-only n=19, zero change).
- Discipline-hub effect found, verified, and fixed by rule (structural
  nodes excluded from extraction in primary scoring; v3-faithful scoring
  kept as sensitivity).

## Gated / pending (in order)
1. Human labels — the completed labelling workbook. Gates Phase 2.
   (Owner: dataset holder.)
2. Kaggle dataset name/link — needed for the reproducibility statement.
3. Second rater (30 rows) for Cohen's kappa; 15–20 raters for the human
   explanation study (stretch items).
4. Phase 2: labelled benchmarks (F1/AUC with Wilson/bootstrap CIs,
   McNemar KG-vs-baseline, UNMAPPED rate, d in {1,2,3} sweep, hub
   sensitivity, per-JD + pooled reporting).
5. Phase 4: paper revision pack (tables, methods text, reproducibility
   statement, claim guardrails).

## Must not be claimed yet
- No F1, AUC, precision, or recall on the engineering resumes.
- No "KG beats baselines" claim on this dataset.
- AOPC numbers are explanation-faithfulness on n=20, not accuracy.
- Security numbers are standalone + appended-embedding end-to-end
  results on synthetic/reused payloads, not real-world guarantees.
- Fairness: no fairness pass is claimed; the anonymised data cannot
  support a name-based check, and LLM-agent identity effects are
  untested here.
