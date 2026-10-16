# Agent work log - what was done to this project, and why

For your reference: a chronological record of every change made by the AI coding agent (Claude Code) on
**2026-10-15**, the reasons, and what was verified. Read it with `docs/teacher.md` (how to explain it) and
`docs/panel_cheatsheet.md` (one-page summary for the day).

---

## 1. Starting point: assessment of the existing repository

Read: `docs/problem_statement.pdf`, `docs/Igny_CLI_User_Guide_Ignytion_A4.pdf`, every script, data file and doc.

| # | Problem found in the original work | Why it mattered (requirement) |
|---|---|---|
| 1 | No Crucible workspace: no `crucible.toml` / `crucible.lock`, no `eda-data` env, no tools installed | Objectives 1, 2, 7; deliverable 1; acceptance 1 |
| 2 | `run_all.sh` used `igny run -- python …` - not valid igny syntax (correct: `igny run script ./x.py`) and bash-only on Windows | "every script runs through igny" |
| 3 | Committed dataset = **5 open-source tools**, no commercial, no regions, no release dates, imported from a hand-made CSV (`source_verified=false` on all rows) | coverage requirements; "no hand-entered rows"; acceptance 2 |
| 4 | `seed_tools.json` contained hand-typed vendor / country / category / licence values that the vendor collector copied into records under the vendor URL - even when the fetch failed. Some were wrong (Siemens EDA → "Germany"; its HQ is Oregon, US) | "no made-up values; every row records where it came from" |
| 5 | Bug: `deduplicate_data.py` shared-website check looped over `rows` while it was still empty → never ran | correctness |
| 6 | `first_release_year` never collected; `releases/latest` misses tag-only projects → no release-activity plot | deliverable 5 (release activity over time) |
| 7 | Report and `requirements-notes.md` were blank templates; README said "adjust the igny syntax" | deliverables 6, 7 |
| 8 | Imported CSV duplicated; the git repository root is the whole home folder `C:/Users/prava`, not the project | hygiene; "clone the repository" |

The good parts were kept: stdlib-only collectors, polite HTTP with robots.txt, the separate
clean → dedup → validate steps, provenance file, review queue, and the fixture-test idea.

## 2. Crucible setup (objectives 1, 2, 7)

`igny` was installed but not on the Git-Bash PATH (only a `doskey` macro for cmd); the full path
`C:\Users\prava\Crucible\packages\igny_foundation_pkg_win_3.12.10.0\Python\Scripts\igny.exe` was used.

```bash
igny doctor                                   # Python OK, Git OK, Docker missing (not needed)
igny env create eda-data
igny workspace create eda-data-science --path . --env eda-data
igny catalog --view full                      # 65 tools: numpy, matplotlib, jupyterlab yes; pandas/scipy/bs4/requests no
igny tool install numpy matplotlib jupyterlab # numpy 2.5.4, matplotlib 3.11.2, jupyterlab 4.6.4 (pip family)
igny workspace lock                           # crucible.lock: 3 bindings
igny workspace sync                           # "Already bound: …" (idempotent)
```

Verified with a probe script under `igny run script` that `.py` files run on **Crucible's own Python
3.12.10** with the tools on `PYTHONPATH` and `CRUCIBLE_ENV=eda-data`.

**Isolation leak discovered:** `import scipy` also worked, from the *user* site-packages
(`%APPDATA%\Python\Python312`). Crucible's interpreter doesn't disable it. Mitigation: `pipeline.py` runs
every step with `python -s` + `PYTHONNOUSERSITE=1`; `check_environment.py` fails the run if a library
resolves outside `Crucible\tools`; `run_analysis.py` calls `drop_user_site()` before importing numpy.

## 3. Source research (objective 3)

| Candidate | Decision | Reason |
|---|---|---|
| Wikidata SPARQL (`query.wikidata.org/sparql`) | **not used** | robots.txt `Disallow: /sparql` |
| Wikipedia API (`/w/api.php`, `/api/rest_v1/`) | **not used** | disallowed for crawlers by robots.txt |
| Wikipedia article pages `/wiki/…` | **used** | allowed; lists + infoboxes are rich |
| GitHub REST API | **used** | no robots.txt; documented API; 60 req/h unauthenticated |
| Vendor product pages | **used** (via seed) | Synopsys / Cadence / Siemens pages return 200; Keysight and one Cadence page → 403 (logged, excluded) |
| Official docs pages | **used** (weak evidence) | platform/format mentions |

Finding: Wikipedia's EDA comparison tables cover PCB, analog and HDL-simulation tools but **not** the big
IC-implementation tools (synthesis, P&R, sign-off), so a discovery seed of official product pages was added.

## 4. Code written / rewritten

| File | Status | What and why |
|---|---|---|
| `scripts/htmlparse.py` | new | stdlib HTML parser: tables with rowspan/colspan, two-row headers, yes/no cell classes, infobox (balanced nesting), lead paragraph, page meta. bs4 isn't a declared Crucible tool |
| `scripts/common.py` | rewritten | schema (23 final columns), 10-value flow-ordered category vocabulary + keyword rules (rule order or position order), licence-model rules, platform/format vocabularies, country & region tables, polite HTTP with retries + percent-encoding + robots.txt |
| `scripts/collect_published_lists.py` | new | Wikipedia: Comparison of EDA software, List of HDL simulators, List of free electronics circuit simulators |
| `scripts/collect_wikipedia_articles.py` | new | tool infoboxes → first/latest release, OS, licence, website, repo; category from Type or lead sentence |
| `scripts/collect_vendor_origin.py` | new | developer company infobox "Headquarters" → country |
| `scripts/collect_vendor_sites.py` | rewritten | values now read from the page (title, og:site_name, meta description, sales evidence); kept only if HTTP 200 **and** product name on page |
| `scripts/collect_public_repositories.py` | rewritten | rate-limit aware, tags fallback, category from repo description |
| `scripts/collect_documentation.py` | rewritten | installation-context platform evidence, unambiguous formats only, headline category |
| `scripts/clean_data.py` | rewritten | vocabularies, excludes unverified sources (`excluded_records.json`) |
| `scripts/deduplicate_data.py` | rewritten | union-find over repo / Wikipedia article / name+vendor; group-level vendor check; human review decisions; per-field priority; release triple from one record; freeware rule; field-level provenance; shared-website bug fixed |
| `scripts/validate_dataset.py` | rewritten | integrity checks + coverage report vs the brief |
| `scripts/run_analysis.py` | rewritten | 8 plots (validated colour-blind-safe palette, no dual axis, deterministic PNGs), 9 CSV tables, `summary.json`, `findings.md` |
| `scripts/pipeline.py` | new | orchestrator: `igny run script ./scripts/pipeline.py [-- --collect]` |
| `scripts/check_environment.py` | new | proves Crucible isolation; lists catalog gaps |
| `notebooks/analysis.ipynb` | new | same plots via `run_analysis.main()`, row tracing, numpy cross-tab |
| `tests/test_pipeline.py` + fixtures | rewritten | offline end-to-end test + unit checks |
| `data/metadata/seed_tools.json` | rewritten | discovery-only: names + URLs, **no values** |
| `data/metadata/review_decisions.json` | new | human-confirmed merges (GHDL, Xyce) with reasons |
| `data/metadata/source_manifest.json` | rewritten | sources, fields, robots decisions |
| `README.md`, `requirements-notes.md`, `reports/project_report.md`, `.gitignore` | rewritten | exact reproduction steps, gaps, the report |
| `archive/legacy_v1/` | moved | old imported snapshot, `import_csv.py`, `run_all.sh` (kept for reference, not used) |

## 5. Bugs found and fixed during the work (good interview stories)

1. **Empty-vendor bridging (dedup):** a record with no vendor could join two tools from *different* vendors
   through union-find transitivity. Caught by the fixture test; fixed by checking all vendors in both groups.
2. **Over-eager vendor rule:** "same first word" made "Example Vendor A" ≈ "Example Vendor B" (think
   National Instruments vs National Semiconductor). Caught by the test; replaced by part-wise comparison.
3. **Name collision:** the seed linked `en.wikipedia.org/wiki/OpenROAD`, which is Actian's OpenROAD (a 4GL
   business IDE). The dedup refused to merge it with the EDA OpenROAD (different vendor), which exposed the error;
   the link was removed and documented in the seed.
4. **Category leak:** a row-level override (Logisim: digital-only) re-assigned the table-level category list,
   so every later row in that table became "simulation" (SPICE, LTspice…). Fixed with a per-row copy.
5. **Heading priority:** KiCad was filed as analog because its table's *parent* heading mentions analog
   simulation; the most specific heading now wins.
6. **Out-of-scope table:** Wikipedia's "List by developer" table is titled *List of electrical engineering
   software* (AutoCAD, FreeCAD, power-grid tools) → excluded.
7. **Repeated header row** parsed as a tool ("Application and developer") → header-only body rows skipped.
8. **Unicode URL** (`/wiki/TINA–TI`) crashed urllib → URLs are percent-encoded.
9. **Escaping accident:** an automated edit turned regex `\b` into backspace characters (rules silently
   stopped matching); detected by testing the categoriser on real vendor sentences, repaired, and re-checked
   across all files.
10. **Transient TLS/DNS errors** on GitHub → up to 2 retries with backoff; remaining failures are logged.
11. Vendor pages with `og:site_name = "English"` (Zuken) → generic site names ignored.

## 6. Verification performed

- `igny run script ./tests/test_pipeline.py` → `PASS` (re-run after every change).
- Four full live collections through `igny run script ./scripts/pipeline.py -- --collect` (each exposed issues
  that were fixed), then a re-run of two collectors (see §7). `validate_dataset.py` → **0 errors**.
- `igny workspace lock` → 3 bindings; `igny workspace sync` → idempotent ("Already bound").
- Fresh-machine simulation: project copied to a temp folder and synced against an empty Crucible home
  (`CRUCIBLE_ROOT`/`IGNYTION_HOME` pointed at empty folders) - result in §7.
- All 8 plots opened and inspected for clipping/overlap (fixed: clipped title, fractional count axis).
- Notebook executed headless with `igny run jupyter nbconvert --execute` (result in §7).

## 7. Final results (committed snapshot 2026-10-15)

| Item | Result |
|---|---|
| Dataset | `data/processed/eda_tools_clean.csv`: **131 tools**, 23 columns, from **268** source records (89 tools combine 2-6 sources) |
| Licence model | commercial 67 · open-source 44 · freeware 7 · not stated 13 |
| Categories | all 10 covered (primary: simulation 39, PCB 27, analog 22, verification 10, layout/PV 8, FPGA 6, synthesis 5, P&R 4, sign-off 3, HLS 2) |
| Regions | North America 49 · Europe 5 · Asia 4 · Oceania 2 (60 tools with a documented vendor country) |
| Validation | 0 errors, 5 warnings (tools whose sources state no category) |
| Collection failures (logged) | Keysight page 403; JLCPCB article 404; 4 developer articles without a usable HQ |
| Review queue | 1 open item (SapWin freeware vs open-source); 2 resolved decisions (GHDL, Xyce) |
| Lock | `crucible.lock`: numpy 2.5.4, matplotlib 3.11.2, jupyterlab 4.6.4 (env `eda-data`) |
| Fresh-machine test | empty `CRUCIBLE_ROOT`/`IGNYTION_HOME` → `igny workspace sync` created the env and installed all 3 tools → `check_environment` OK → rebuild: 0 errors |
| Determinism | two rebuilds → identical MD5 for all 8 PNGs and the CSV; the notebook produced the same plots |
| Notebook | `igny run jupyter nbconvert --execute`: 0 errors, 8 plots embedded, numpy loaded from Crucible |
| Tests | `igny run script ./tests/test_pipeline.py` → PASS |

How the final snapshot was produced: a full live run (`pipeline.py -- --collect`). The vendor-site and GitHub
collectors were then re-run once, the same day, after retries were raised from 2 to 4, because this network
produced intermittent TLS errors (`SSLV3_ALERT_BAD_RECORD_MAC`). Each source has its own snapshot file, so
re-running one collector replaces only that source's file. The collection log describes the final files.

Additional bug found by the fresh-machine test: `check_environment.py` assumed tools live under
`...\Crucible\tools`; with a relocated `CRUCIBLE_ROOT` it wrongly failed. It now reads `CRUCIBLE_ROOT`. The same test
revealed the numpy-from-matplotlib's-bundle shadowing finding (report §6).

## 8. What is left for you to do

1. **Create a git repository for the project folder** (the current repo root is your whole home folder):
   ```bash
   cd "C:\Users\prava\Downloads\global-eda-tools-explorer (2)\global-eda-tools-explorer"
   git init
   git add .
   git commit -m "Global EDA tools dataset on Crucible"
   ```
   Commit `crucible.toml` and `crucible.lock` **together** (the brief requires it). Then push to GitHub/GitLab.
2. Optional: set `GITHUB_TOKEN` (never commit it) and re-collect to fill the few repos skipped by rate limits.
3. Optional: review `data/processed/review_queue.json` and add decisions to `data/metadata/review_decisions.json`.
4. Rehearse with `docs/teacher.md` and `docs/panel_cheatsheet.md`; run the demo script yourself at least twice.
5. Read every script once yourself. Be ready to say honestly how the project was built, including the use of an AI assistant
   if you are asked.
