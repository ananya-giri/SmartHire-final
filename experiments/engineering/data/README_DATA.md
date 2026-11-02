# Resume texts — how to populate this directory

This directory is intentionally empty in the repository: the 118 resume
texts are third-party Kaggle data and are not redistributed here.

To reproduce the experiment, extract text from the 118 resume PDFs
(the set the dataset holder uploaded; IDs are in `../assignments.csv`)
into this directory, one file per resume named `<resume_id>.txt`:

```bash
for f in *.pdf; do pdftotext -layout "$f" "data/${f%.pdf}.txt"; done
```

Expected result: 118 `.txt` files, median ~786 words, none empty.
Scripts in `../phase3_scripts/` read from this directory. The Kaggle
dataset name/link is still to be recorded for the reproducibility
statement (see `../ENGINEERING_STATUS.md`).
