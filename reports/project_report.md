# A Worldwide EDA Tool Dataset, Built on Crucible: Project Report

**Snapshot:** 2026-10-15 · **Dataset:** `data/processed/eda_tools_clean.csv` (131 tools) · **Platform:** Crucible
(`igny`, foundation package 3.12.10.0), environment `eda-data`, workspace `eda-data-science`.

## 1. Summary

We built a reproducible pipeline that collects public information about EDA tools worldwide and produces one
deduplicated row per tool, with a source URL and collection date on every row. The committed snapshot has
**131 tools** (67 commercial, 44 open-source, 7 freeware, 13 not stated) from **268 source records** across
**6 source types**. It covers **all 10 flow categories**, from high-level synthesis to sign-off, PCB and FPGA,
and vendors in North America, Europe, Asia and Oceania. Everything (environment, libraries, collection,
analysis, notebook) runs through `igny`, and the workspace is locked. A fresh-machine simulation (empty
Crucible home → `igny workspace sync` → rebuild) reproduced the dataset with 0 validation errors.

## 2. Sources and collection method

| Source type (script) | Source | Records | What it contributes |
|---|---|---|---|
| published_list (`collect_published_lists.py`) | Wikipedia: *Comparison of EDA software*, *List of HDL simulators*, *List of free electronics circuit simulators* | 90 | discovery, developer, platforms, licence, latest release, formats; category from the table's own section |
| wikipedia_article (`collect_wikipedia_articles.py`) | the tool's Wikipedia infobox | 45 | first release year, stable release, OS, licence, website, repository |
| vendor_origin (`collect_vendor_origin.py`) | the developer company's Wikipedia infobox | 66 (29 companies) | country of origin (Headquarters) |
| vendor_site (`collect_vendor_sites.py`) | official product pages (36 in the seed) | 35 | commercial IC tools absent from the lists: vendor, category, sales evidence |
| public_repository (`collect_public_repositories.py`) | GitHub REST API | 25 | SPDX licence, owner, latest release tag/date, category from repo description |
| documentation (`collect_documentation.py`) | official documentation pages | 7 | platform and format evidence (weak), headline category |

**Rules followed.** robots.txt is checked before every page, with ≥1.5 s between pages and ≥1 s between API
calls; the User-Agent identifies the project with a contact; only public pages are read. Because of
robots.txt, the Wikidata SPARQL endpoint and the Wikipedia APIs were **not** used, although they would have
been the richest structured sources (`data/metadata/source_manifest.json`). Failures are logged in
`data/raw/collection_log_2026-10-15.jsonl`. In the final snapshot: Keysight's ADS page returned 403 (bot
protection); one developer article was missing (JLCPCB, 404); four developer articles had no usable
headquarters (a person, a project, Novarm, Qorvo "Greensboro").

**Discovery seed.** Wikipedia's tables cover PCB, analog and HDL simulation well, but not the large
IC-implementation tools. `data/metadata/seed_tools.json` therefore lists 61 tool names with the URLs to read
(product page, GitHub repository, docs page, Wikipedia article). It holds **no field values**. A vendor-page
record is kept only if the page returns HTTP 200 **and** the product name appears on it.

## 3. Cleaning and deduplication

- **Normalisation** (`clean_data.py`): controlled vocabularies for category (10 flow stages), licence model,
  platforms and formats; ISO dates; years 1950 to today; URL validation. Records whose source did not return
  200 are excluded (0 in the final snapshot). Unknown values stay empty.
- **Derivation rules** (in `common.py`, applied to text the source states): category from keyword rules
  (rule order for list headings, first-mention order for a vendor's own summary sentence); licence model from
  the licence text (GPL/BSD/MIT… → open-source, proprietary/EULA → commercial, freeware → freeware) or from the
  page's own grouping; country from the developer's headquarters.
- **Deduplication** (`deduplicate_data.py`): union-find merges records that share a GitHub repository, a
  Wikipedia article, or a normalised name with a compatible vendor. The vendor check runs against the whole
  group, so an empty-vendor record cannot bridge two vendors. Field values follow a per-source priority, and
  the latest version and date come together from the single record reporting the most recent release.
  Result: **268 records → 131 tools**, 89 tools combining 2 to 6 sources, 17 same-source duplicates merged.
- **Human review** (`review_queue.json`, `data/metadata/review_decisions.json`): ambiguous same-name/different-vendor
  pairs are never auto-merged. Two were confirmed with written reasons: GHDL (author vs GitHub org) and Xyce
  (Sandia vs GitHub org). One open item remains: SapWin is listed as freeware by one source and open-source by another.
- **A caught error:** the seed first linked the Wikipedia article "OpenROAD", which is Actian's 4GL business
  IDE, not the EDA tool. The vendor check refused the merge, which exposed the mistake; the link was removed.
- **Validation** (`validate_dataset.py`): schema, unique ids, valid source URL + date + provenance for every
  row, vocabularies, region ↔ country, first ≤ latest release. **0 errors**; 5 warnings (tools whose sources
  state no category).

## 4. Findings

All numbers are from `outputs/` (generated by `scripts/run_analysis.py`) and describe **the collected
catalog**, not every EDA tool in existence.

**Tools per category** (`tools_by_category.png`). Simulation is the largest primary category (39), followed
by PCB design (27) and analog/mixed-signal (22). Counting secondary categories, simulation appears in 72
tools and analog/mixed-signal in 49, because most circuit and PCB tools also simulate. The implementation and
sign-off stages are small (P&R 4, timing/power sign-off 3, HLS 2 as primary) and almost entirely commercial.
The only open-source P&R is OpenROAD, with OpenSTA (no stated category) as the open-source STA.

**Commercial vs open-source** (`license_distribution.png`). 51 % commercial, 34 % open-source, 5 % freeware,
10 % not stated. Open-source is strongest in FPGA toolchains (4 of 6) and layout/physical verification;
commercial dominates PCB (19 of 27) and every sign-off tool in the dataset.

**Tools per region** (`tools_by_region.png`). 60 of 131 tools (46 %) have a documented vendor country.
Among them: North America 49 (United States 49), Europe 5 (Germany 2, United Kingdom, France, Italy),
Asia 4 (Japan 3, China 1), Oceania 2 (Australia). The US share reflects real market concentration (the
three largest EDA vendors are US-headquartered: Siemens EDA's HQ is in Oregon). It is inflated by a
measurement effect: companies have Wikipedia articles with a headquarters field, while community
open-source projects mostly don't, so open-source tools rarely get a country.

**Release activity** (`release_activity.png`). 30 tools have a documented first release year, spanning
1973 (Berkeley SPICE) to 2015, with a cluster in 1982 to 1993 (Magic, Micro-Cap, OrCAD, EAGLE, KiCad).
58 tools have a documented latest release; 36 of them released in 2024 to 2026. Open-source tools look
more active (22 of 29 since 2024) than commercial ones (9 of 21). **Caution:** open-source dates come live
from GitHub, while commercial dates mostly come from Wikipedia infoboxes, which are often stale. Part of
this gap is a source effect, not a fact about the tools.

**Platforms and formats** (`platform_support.png`, `languages_formats.png`). Among tools with documented
platforms, Windows is most common (42), driven by commercial PCB/circuit tools; open-source tools lean to
Linux/Unix/macOS. Verilog (37) is the most-mentioned design language; Gerber (26) is the most-mentioned
manufacturing format.

**Data completeness** (`data_completeness.png`). Vendor (95 %), category (96 %) and licence model (90 %)
are well covered. First release year (23 %), repository URL (23 %) and platforms (37 %) are the hardest to
find publicly, especially for commercial tools.

## 5. Known gaps in coverage

1. **Not a census.** 131 tools is a well-sourced sample. The Wikipedia lists over-represent PCB, analog and
   HDL-simulation tools. IC implementation and sign-off tools come from a 61-entry discovery seed chosen by
   the author (the choice of *which* pages to read is human; every *value* comes from the pages).
2. **Regions are thin outside North America** (Europe 5, Asia 4). Many Asian and European vendors
   (Empyrean, Primarius, Gowin, Efinix, Sigasi, Defacto) have no English Wikipedia article with a
   headquarters field, so their country stays empty. South America and Africa: none found.
3. **Category** is rule-derived and can follow marketing wording. Cadence now sells *Innovus+ Synthesis and
   Implementation*, so Innovus's primary category is synthesis, with P&R as additional. Bambu (an HLS tool)
   is primarily `fpga-toolchain` because its description mentions FPGA first. Five tools state no category.
4. **Release data**: commercial versions are often stale or missing; tag-only GitHub projects have a version
   but no date.
5. **Documentation evidence is weak** (mentions, not guarantees) and only used for platforms and formats.
6. **Variability between runs.** Bot protection (Cadence pages alternately 200/403), intermittent TLS errors
   on this network, and GitHub's 60 requests/hour limit can drop records. Every drop is logged, the
   collectors retry up to 4 times, and a `GITHUB_TOKEN` removes the GitHub limit.

## 6. Where Crucible fell short for data-science work

1. **No pandas** (nor scipy, seaborn, scikit-learn, requests or beautifulsoup4 as tools). Workaround:
   `csv` + `collections` + numpy, `urllib`, and our own `html.parser`-based `htmlparse.py`. That is more code
   for joins and group-bys than pandas would need.
2. **Hidden bundled dependencies.** `requests` and `bs4` are importable only because jupyterlab bundles them.
   They aren't in `crucible.lock`, so relying on them would be fragile; we didn't. Likewise, on a fresh
   machine `numpy` was imported from **matplotlib's bundled copy**, not from the numpy tool: PYTHONPATH order
   decides, so a pinned version can be silently shadowed (`check_environment.py` reports this).
3. **Isolation leak.** Crucible's Python does not disable the user site-packages: `import scipy` succeeded
   inside `igny run script` from `%APPDATA%\Python\Python312`. Mitigated with `python -s`,
   `PYTHONNOUSERSITE=1` and a fail-fast check.
4. **The lock is weak for reproducibility.** pip-family tools are recorded with `"checksum": null` (no hash
   pinning), transitive dependencies aren't listed, and every entry is `platform: windows-x86_64`, so
   reproducing on Linux/macOS from this lock is untested and may not be possible.
5. **CLI ergonomics.** `igny` wasn't on the Git-Bash PATH after installation (a `doskey` macro for cmd only);
   `igny --version` prints `dev` (the guide shows a release number); the brief's starter commands and the old
   `run_all.sh` form (`igny run -- python`) differ from the authoritative `igny run script`.
6. `igny doctor` flags Docker as missing. Harmless here (no docker-family tools), but noisy.

What worked well: `igny run script` reliably used Crucible's interpreter with the tools on the path and
captured a log of every run; `igny run jupyter nbconvert --execute` ran the notebook headless; `igny workspace
sync` rebuilt the environment on an empty Crucible home from the lock alone.

## 7. Reproduction

```bash
igny workspace sync                                      # environment from crucible.lock
igny run script ./scripts/check_environment.py           # isolation proof
igny run script ./scripts/pipeline.py                    # rebuild from the committed snapshot (same plots as here)
igny run script ./scripts/pipeline.py -- --collect       # fresh dataset from live sources
igny run script ./tests/test_pipeline.py                 # offline test
igny run jupyter nbconvert --to notebook --execute --inplace notebooks/analysis.ipynb
```

Two consecutive rebuilds from the committed snapshot produced byte-identical PNGs and CSV (checked with MD5).
Any row is traceable: `source_url` in the dataset plus every contributing page in `data/processed/provenance.csv`
(with the fields each page reported).
