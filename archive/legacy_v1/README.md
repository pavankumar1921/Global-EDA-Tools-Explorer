# Legacy v1 (archived 2026-10-15, not used by the pipeline)

The first version of the project. Kept for reference only; nothing here feeds the current dataset.

- `data_raw/` - the 2026-10-14 snapshot. It was **imported from a hand-assembled CSV**
  (`imported/…starter_dataset.csv`, 6 tools) with `scripts/import_csv.py`, not collected live, so every
  row had `source_verified=false`. The problem statement forbids hand-entered rows, so it was retired.
  (A byte-identical duplicate copy of the CSV, created by running the importer twice, was removed.)
- `scripts/import_csv.py` - the importer for that CSV.
- `run_all.sh` - used `igny run -- python …`, which is not valid igny syntax. The correct form is
  `igny run script ./scripts/<file>.py`; see `scripts/pipeline.py` and the README.
