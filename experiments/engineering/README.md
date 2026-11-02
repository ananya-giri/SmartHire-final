# SmartHire AI — Engineering Extension Experiment

This directory holds the multi-role engineering experiment built on top of
the v3 SmartHire codebase (repo root). It is an EXTENSION: no file in the
repo root was modified to create it. The original v3 code is imported
read-only; the only new production-code file is
`tools/engineering_graph.py`.

## What is here

| Path | Contents |
|---|---|
| `tools/engineering_graph.py` (repo root) | Engineering KG extension: Mechanical / Electrical / Civil / Technician clusters added to the v3 tech graph (153 nodes / 159 edges total). Same matching rule as v3 (binary approval, distance <= 2). |
| `jds/jds.json`, `jds/JDs_FINAL.md` | 5 final JDs x 10 requirements (Mechanical, Electrical, Civil, Software, Technician), grounded in resume-group frequencies. |
| `assignments.csv` | All 118 resumes assigned to their nearest JD by stated title + distinctive skills (title-led, never the KG scorer). Flags: 81 OK, 37 REVIEW. |
| `labeling/SmartHire_Engineering_Labeling_Sheet.xlsx` | Human-labelling workbook: one tab per JD (118 rows), rubric, 30-row second-rater sample, formula-driven Summary. Labels are the ground truth for Phase 2. |
| `assign_roles.py` | The assignment script (reproducibility). |
| `phase3_scripts/` | Label-free Phase 3 runners: per-layer security ablation, AOPC + random baseline (original + fixed-extraction re-run), blinded fairness check, end-to-end injected-resume experiment. |
| `results/phase3_labelfree/` | REPORT.md + JSON outputs for all label-free Phase 3 pieces. |
| `METHODS_PHASE1.md` | Full methods record (assignment, graph, JDs, labelling protocol, extraction audit, hub-effect fix decision). |
| `data/` | EMPTY BY DESIGN (see below). |

## Resume texts are NOT in this repo

The 118 resume texts are third-party Kaggle data and are deliberately not
redistributed here. To reproduce the experiment, place the extracted texts
(`<resume_id>.txt`, one per resume, IDs from `assignments.csv`) in `data/`
and read `data/README_DATA.md` for the extraction command. All scripts
read texts from `data/`; nothing else needs the texts.

## The fixed extraction rule (important)

Primary scoring EXCLUDES structural graph nodes (extension hubs and
sub-hubs) from the extraction vocabulary: they structure the graph but
are not skills. Without this rule, a resume merely stating its degree
discipline ("Electrical Engineering") approves all 10 requirements of
that discipline's JD (hub -> sub-hub -> skill = distance 2). The
v3-faithful rule (hubs extractable) is reported as a sensitivity
analysis. See METHODS_PHASE1.md §8 and results/phase3_labelfree/REPORT.md
§§4-5. The graph itself is unchanged; the rule lives in the scoring
harness (`phase3_scripts/`, `STRUCTURAL_NODES` sets).

## How to run (label-free pieces; need `data/` populated + deps)

```bash
pip install networkx scikit-learn
cd experiments/engineering/phase3_scripts
python3 security_ablation.py     # per-layer guardrail ablation (repo data/)
python3 aopc_baseline_fixed.py   # AOPC + random baseline, fixed extraction
python3 blinded_fairness.py      # institution-only blinding check
python3 endtoend_injected.py     # injected resumes through guardrail -> scorer
```

Phase 2 (labelled benchmarks: F1/AUC with CIs, McNemar, UNMAPPED rate,
d-sensitivity, hub sensitivity) runs only once the completed labelling
workbook is returned. See ENGINEERING_STATUS.md.

## Status

See ENGINEERING_STATUS.md. In one line: Phases 1 + 3 (label-free) done;
Phase 2 gated on human labels; Phase 4 (paper revision pack) follows
Phase 2. No accuracy claims on the engineering resumes exist yet, and
none should be quoted until Phase 2 runs.
