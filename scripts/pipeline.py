"""Run the whole project in order. Launch it through Crucible:

    igny run script ./scripts/pipeline.py                       # rebuild from the committed snapshot
    igny run script ./scripts/pipeline.py -- --collect          # fresh collection from live sources
    igny run script ./scripts/pipeline.py -- --snapshot 2026-10-15

Every step is started with the same Crucible interpreter that igny resolved (sys.executable) and with
'-s', so the user's personal site-packages can never leak in. The snapshot date is fixed once at the
start, so all steps of one run read and write the same dated files even across midnight.
"""
import argparse
import datetime
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE.parent / "data" / "raw"
COLLECT = ["collect_published_lists.py", "collect_wikipedia_articles.py", "collect_vendor_sites.py",
           "collect_public_repositories.py", "collect_documentation.py", "collect_vendor_origin.py"]
PROCESS = ["clean_data.py", "deduplicate_data.py", "validate_dataset.py", "run_analysis.py"]


def latest_snapshot():
    dates = sorted(p.stem.rsplit("_", 1)[-1] for p in RAW.glob("published_list_*.json"))
    return dates[-1] if dates else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--collect", action="store_true", help="collect fresh data from the live sources first")
    ap.add_argument("--snapshot", help="snapshot date to process (default: newest in data/raw)")
    a = ap.parse_args()
    date = datetime.date.today().isoformat() if a.collect else (a.snapshot or latest_snapshot())
    if not date:
        sys.exit("No snapshot in data/raw; run with --collect")
    env = dict(os.environ, EDA_SNAPSHOT_DATE=date, PYTHONNOUSERSITE="1")
    steps = ["check_environment.py"] + (COLLECT if a.collect else []) + PROCESS
    print("snapshot %s | steps: %s" % (date, ", ".join(steps)))
    for s in steps:
        print("\n=== %s" % s, flush=True)
        r = subprocess.run([sys.executable, "-s", str(HERE / s)], env=env)
        if r.returncode != 0:
            sys.exit("step %s failed (exit %d)" % (s, r.returncode))
    print("\npipeline finished for snapshot %s" % date)


if __name__ == "__main__":
    main()
