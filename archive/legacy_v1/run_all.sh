#!/usr/bin/env bash
# Run the whole pipeline. Every python call goes through the Crucible runner.
# RUN is the runner prefix from your problem statement (default below is a placeholder):
#   RUN="igny run --" ./run_all.sh
set -euo pipefail
RUN="${RUN:-igny run --}"
cd "$(dirname "$0")"

$RUN python scripts/collect_vendor_sites.py
$RUN python scripts/collect_public_repositories.py
$RUN python scripts/collect_documentation.py
$RUN python scripts/clean_data.py
$RUN python scripts/deduplicate_data.py
$RUN python scripts/validate_dataset.py
$RUN python scripts/run_analysis.py
