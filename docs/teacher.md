# teacher.md - how to understand, explain and defend this project in your panel

This is your study guide. Read it top to bottom once, then use the **cheat sheet**
(`docs/panel_cheatsheet.md`) on the day. Numbers quoted here come from the committed snapshot
(`outputs/findings.md`). If you re-collect, re-read that file, because the numbers will change.

> **Golden rule for the panel:** you will be judged less on *what* the code does than on whether you can
> explain *why* each decision was made, what its limits are, and what you would do next.
> Every "why" in this file is something a panelist can ask.

---

## 0. The 30-second pitch (memorise this)

> "EDA tool information is scattered across vendor sites, open-source repos and community lists. I built a
> reproducible data-science pipeline that collects it from public sources worldwide and produces one clean,
> deduplicated row per tool: commercial, open-source and freeware, across the whole chip-design flow from
> high-level synthesis to sign-off, plus PCB and FPGA, with vendors from North America, Europe and Asia.
> Every row is traceable to the URL it came from and the date it was collected, and nothing is hand-typed or
> guessed. The whole project runs *entirely* on Crucible: the environment is created with `igny`, every library
> is installed with `igny tool install`, every script runs with `igny run script`, and the workspace is locked,
> so anyone can clone it, run `igny workspace sync`, and get the same result."

## 0.1 The 2-minute version (structure: problem → approach → result → limits)

1. **Problem:** no single structured view of the global EDA landscape. Brief: build it, run it all on Crucible.
2. **Approach:** six collectors (one per source type) → dated raw snapshot → clean → deduplicate → validate
   → analyse. Provenance on every row; robots.txt and rate limits respected.
3. **Result:** 131 tools from 268 source records (67 commercial / 44 open-source / 7 freeware), all 10 flow
   categories, vendors on 4 continents; a provenance table; 8 plots + notebook; a report; a fixture test; a lock
   file that rebuilt everything on an empty machine.
4. **Honest limits:** Wikipedia is our main structured source, so commercial IC tools needed a discovery seed of
   product pages; country is known only when the vendor has a Wikipedia article; pandas is not in the Crucible
   catalog; GitHub allows 60 unauthenticated calls per hour.

---

## 1. What to learn - prioritised

| Priority | Topic | Why the panel cares | Section |
|---|---|---|---|
| **P0 - must** | The chip design flow and what each EDA category does | the subject of the dataset | §2 |
| **P0** | Crucible / `igny`: environment, workspace, install, run, lock, sync | the platform the brief is about | §3 |
| **P0** | Provenance, "no made-up values", how every field is derived | the brief's core data rule | §5, §7 |
| **P0** | Deduplication / entity resolution (union-find, merge keys, conflicts) | the hardest data-engineering part | §5.4 |
| **P1 - should** | Web collection ethics: robots.txt, rate limits, User-Agent, HTTP codes, REST APIs | brief's constraint | §4 |
| **P1** | HTML parsing (tables, rowspan/colspan, infoboxes) with the stdlib | why no BeautifulSoup | §4.4 |
| **P1** | Data-quality concepts: schema, controlled vocabularies, normalisation, completeness, validation | general DS rigour | §5 |
| **P1** | Chart choice and why each plot looks the way it does | "present findings with plots" | §6 |
| **P2 - nice** | Reproducibility theory: lock files, deterministic outputs, immutable snapshots | shows maturity | §3.4, §5.1 |
| **P2** | Python stdlib modules used (`urllib`, `html.parser`, `re`, `csv`, `json`, `subprocess`, `argparse`) | code questions | §8 |
| **P2** | What you would do next (Wikidata dump, more sources, ML classification, dashboard) | vision questions | §10 |

Suggested study plan: **Day 1** §2-§3 + run the demo yourself. **Day 2** §4-§5 + read the code with this
file open. **Day 3** §6-§9 + rehearse the Q&A out loud twice, then the demo twice.

---

## 2. Domain: EDA and the chip-design flow (P0)

**EDA (Electronic Design Automation)** = the software used to design, simulate, verify and manufacture-prepare
integrated circuits (ICs), FPGAs and printed circuit boards (PCBs). A modern chip cannot be designed by hand;
it has billions of transistors.

### 2.1 The digital IC flow, front end → back end (know this order cold)

| Stage | What happens | Example tools (commercial / open-source) | Our category |
|---|---|---|---|
| High-level synthesis (HLS) | C/C++/SystemC → RTL automatically | Cadence Stratus, Siemens Catapult / Bambu | `high-level-synthesis` |
| RTL design | Engineer writes hardware in an HDL (Verilog, SystemVerilog, VHDL) | editors, linters (Verible, Sigasi) | - |
| Simulation | Run the RTL with a testbench to check behaviour | Synopsys VCS, Cadence Xcelium, Siemens Questa / Verilator, Icarus, GHDL | `simulation` |
| Verification | Prove/check correctness: formal, equivalence, coverage, UVM | Cadence Jasper, Synopsys VC Formal, Formality / SymbiYosys, cocotb | `verification` |
| Logic synthesis | RTL → gate-level netlist using a standard-cell library (Liberty `.lib`) | Synopsys Design Compiler, Cadence Genus / Yosys | `synthesis` |
| Place & route (physical design) | Floorplan, place cells, clock tree, route wires (LEF/DEF) | Cadence Innovus, Synopsys IC Compiler II / Fusion Compiler, Siemens Aprisa / OpenROAD | `place-and-route` |
| Timing / power sign-off | Static timing analysis (STA), IR drop, EM: "will it meet frequency?" | Synopsys PrimeTime, Cadence Tempus, RedHawk-SC / OpenSTA | `timing-signoff` |
| Physical verification | DRC (design rules) and LVS (layout matches schematic) | Siemens Calibre, Cadence Pegasus, Synopsys IC Validator / Magic, KLayout, Netgen | `layout-physical-verification` |
| Tape-out | Final layout as **GDSII/OASIS** to the foundry | - | - |

**Analog / mixed-signal (AMS):** transistor-level design: schematic → SPICE simulation → custom layout.
Tools: Cadence Virtuoso + Spectre, Synopsys HSPICE / Custom Compiler, Keysight ADS (RF) / ngspice, Xschem, Xyce, Qucs. → `analog-mixed-signal`

**PCB:** schematic capture + board layout → Gerber files to the board fab. Altium Designer, Cadence Allegro/OrCAD,
Siemens Xpedition/PADS, Zuken CR-8000 / KiCad. → `pcb-design`

**FPGA toolchains:** synthesis + place & route + bitstream for a programmable chip. AMD Vivado, Intel/Altera Quartus,
Lattice Radiant, Gowin, Efinix / nextpnr, openFPGALoader. → `fpga-toolchain`

### 2.2 Industry facts worth saying
- The "Big Three": **Synopsys, Cadence, Siemens EDA** (formerly Mentor Graphics, bought by Siemens in 2017; HQ
  Wilsonville, Oregon, USA, so our data says *United States*, not Germany, because we use the HQ field).
- Synopsys acquired **Ansys** (completed 2025). Our collection saw this live: the old Ansys RedHawk-SC URL now redirects
  to synopsys.com. That's a nice anecdote showing why live collection beats a static list.
- Open-source silicon grew after Google + SkyWater opened the **SKY130 PDK** (2020): OpenROAD, OpenLane, Yosys, Magic, KLayout.
- Asia: **Empyrean** (China, analog/flat-panel tools), **Zuken** (Japan, PCB), **Primarius** (China, SPICE), **Gowin** (China, FPGA).

### 2.3 File formats you should recognise
Verilog / SystemVerilog / VHDL (HDLs) · SystemC (C++ modelling) · Liberty `.lib` (cell timing) · LEF/DEF (physical
abstracts / placed design) · SDC (timing constraints) · SPEF (parasitics) · SPICE netlist · GDSII / OASIS (final
layout) · Gerber / ODB++ / IPC-2581 (PCB fab) · EDIF (netlist exchange).

---

## 3. Crucible and `igny` (P0)

### 3.1 The four concepts (from the user guide, Section 01)
| Concept | Meaning | Command |
|---|---|---|
| Catalog tool | something Crucible *knows how to get* | `igny catalog --view full` |
| Installed tool | payload downloaded once into the machine inventory (`~/Crucible/tools/<tool>/<ver>`) | `igny tool list` |
| Environment | named, isolated set of **bindings** to installed tools | `igny env create/list/show` |
| Workspace | a project dir with `crucible.toml`, bound to one environment | `igny workspace create/show` |

Key idea: **installed ≠ bound.** The payload is downloaded once; each environment holds a lightweight binding.
Installing the same tool in a second env doesn't download it again.

### 3.2 Selected vs active environment, and the resolution order
- *Selected* = the env written in the workspace's `crucible.toml` (per project).
- *Active* = machine-global runtime state (`igny env activate`).
- `igny run` picks the env in this order: **1. `CRUCIBLE_ENV` → 2. workspace `crucible.toml` → 3. last activated → 4. managed default.**
- Our runs show `CRUCIBLE_ENV: eda-data` inside scripts, which proves `igny run script` resolved our workspace env.

### 3.3 Exactly what we ran
```bash
igny env create eda-data
igny workspace create eda-data-science --path . --env eda-data     # writes crucible.toml
igny catalog --view full                                           # 65 tools; numpy/matplotlib/jupyterlab yes, pandas no
igny tool install numpy matplotlib jupyterlab                      # pip family, bound to eda-data
igny run script ./scripts/pipeline.py -- --collect                 # every script through igny
igny run jupyter nbconvert --to notebook --execute ...             # the notebook through igny
igny workspace lock                                                # writes crucible.lock
```
`igny run script` decides the interpreter from the shebang/extension: a `.py` file runs with **Crucible's own Python 3.12.10**
(`C:\Users\...\Crucible\packages\igny_foundation_pkg_win_3.12.10.0\python\python.exe`) and puts the bound
tools on `PYTHONPATH`. Use `--dry-run` to show this, and `--log` to print the captured run log path.

### 3.4 Lock and sync = reproducibility
- `crucible.lock` records each bound tool's **name, version, source, path, checksum/URL**.
- `igny workspace sync` on another machine reads **the lock (not the toml)**, creates the env if missing and installs the
  exact versions. No override flag, on purpose: an override would build a different toolchain.
- Analogy: `crucible.toml` ≈ `pyproject.toml` (intent); `crucible.lock` ≈ `poetry.lock`/`package-lock.json` (exact resolution).
- The guide warns the lock format isn't stable across CLI versions: regenerate it after upgrading `igny`.

### 3.5 Where Crucible fell short (the brief demands this list; know it by heart)
1. **No pandas** (also no scipy, seaborn, scikit-learn) in the catalog → we used `csv`, `collections.Counter`, numpy.
2. **requests / BeautifulSoup only exist *bundled inside jupyterlab*.** They're importable, but they're not declared tools,
   so they aren't in the lock and could vanish. We deliberately didn't rely on them → stdlib `urllib` + our own `htmlparse.py`.
3. **Isolation leak:** Crucible's Python does not disable the *user site-packages*, so `import scipy` worked inside
   `igny run script` from `%APPDATA%\Python\Python312`. Fix: `python -s` + `PYTHONNOUSERSITE=1` in `pipeline.py`, and
   `check_environment.py` fails if a library resolves outside `Crucible\tools`.
4. **Bundled-copy shadowing:** on a fresh machine, `import numpy` loaded **matplotlib's bundled numpy**
   (`tools\matplotlib\3.11.2\numpy`), not the numpy tool. PYTHONPATH order decides which copy wins, so a pinned
   version can be silently shadowed. `check_environment.py` prints a note when this happens.
5. **Lock weaknesses:** in `crucible.lock` the pip tools have `"checksum": null` (no hash pinning), transitive
   dependencies aren't listed, and every entry says `platform: windows-x86_64`, so cross-OS reproduction is unproven.
6. `igny` isn't on the Git-Bash PATH after install (a `doskey` macro for cmd only); we called the full path to `igny.exe`.
7. `igny --version` prints `dev` instead of a release number (the guide shows `0.0.7`), which makes versions harder to report.
8. `igny doctor` reports Docker missing (only matters for docker-family tools; none used).
9. The user guide documents `igny run script ./x.py` but the brief's starter and the old `run_all.sh` used other forms;
   `igny run --help` is authoritative (guide §19).

---

## 4. Collecting web data responsibly (P1)

### 4.1 HTTP basics you'll be asked about
- `200` OK · `301/302` redirect (urllib follows automatically) · `403` forbidden (e.g. Keysight and one Cadence page block
  non-browser clients; we log and skip) · `404` not found · `429` too many requests · `5xx` server error.
- **User-Agent**: we identify ourselves (`GlobalEDAToolsExplorer/1.0 (...; contact: EDA_CONTACT)`): polite and honest.
- **Rate limiting**: ≥1.5 s between page requests, ≥1.0 s between API calls (`polite_get` in `common.py`).

### 4.2 robots.txt - and the decision it forced
- A site's `robots.txt` says which paths automated clients may fetch. Python's `urllib.robotparser` evaluates it.
- Decision: **Wikidata SPARQL** (`query.wikidata.org/sparql`) would have been the best structured source, but its robots.txt
  says `Disallow: /sparql`; Wikipedia's `/w/api.php` and `/api/rest_v1/` are also disallowed for crawlers. We followed the
  rule and used only `/wiki/` article pages, which are allowed. **This is a strong talking point: the constraint shaped the architecture.**
- Policy in code: robots.txt missing (4xx) → allowed; unreachable (network/5xx) → treated as *not* allowed (fail safe).

### 4.3 REST API: GitHub
- `GET /repos/{owner}/{repo}` → licence SPDX id, owner, homepage. `GET /releases/latest` → tag + date.
  If a project only uses tags: `GET /tags?per_page=1` (name only).
- **Rate limit 60 requests/hour unauthenticated** (5,000 with a token). The collector reads `X-RateLimit-Remaining` and stops
  cleanly, logging skipped repos. The token goes in `GITHUB_TOKEN` env var, **never committed**.
- We do **not** infer first release year from the repo creation date: many projects moved to GitHub years after shipping
  (Magic is from 1983; its GitHub repo is much newer).

### 4.4 HTML parsing without BeautifulSoup (`scripts/htmlparse.py`)
- Wikipedia tables use **rowspan/colspan** (one cell spanning rows/columns). `expand_grid()` rebuilds the full rectangular
  grid so column 3 is always column 3. Two-row headers ("Latest release / Version", "/ Date") are merged.
- Yes/No feature cells are coloured by CSS class (`table-yes`), not text, so the parser keeps the class (`cell_flag`).
- `balanced()` extracts the infobox table with nesting depth counting (regex alone fails on nested tables).
- Infobox = the summary box on a Wikipedia article: we read Developer, Initial release, Stable release, OS, License,
  Website, Repository, Type. Org infoboxes (Headquarters/Industry) are recognised and not treated as tools.

---

## 5. Data engineering - the core of the evaluation (P0/P1)

### 5.1 Layers (medallion-style)
`data/raw/<source>_<date>.json` (**bronze**: as collected, dated, never edited) → `records_normalized.json` (**silver**:
cleaned per-source records) → `eda_tools_clean.csv` (**gold**: one row per tool). Why: you can always re-run cleaning
on the same raw data; you can audit any value back to the raw record; a new collection never overwrites an old snapshot.

### 5.2 Schema and controlled vocabularies
- 23 columns (see README). Multi-valued fields are `"; "`-joined and sorted, so they're deterministic.
- `category` ∈ 10 flow-ordered values; `license_model` ∈ {commercial, open-source, freeware}; platforms ∈ 6 values.
  A controlled vocabulary makes counting and plotting meaningful ("PnR", "place and route" and "physical design" all
  become `place-and-route`).
- **Empty means "not found in any source"**, never "no". E.g. empty `supported_platforms` ≠ "runs nowhere".

### 5.3 How each field is derived (memorise 3-4 examples)
| Field | Rule | Where in code |
|---|---|---|
| category (lists) | keyword rules applied to the **table's own section heading** (e.g. "…software for PCB design" → `pcb-design`); a row's Analog?/Digital? flags override | `common.CATEGORY_RULES`, `collect_published_lists.py` |
| category (vendor pages) | same rules on `<title>` + meta description ("PrimeTime Static Timing Analysis" → `timing-signoff`) | `collect_vendor_sites.py` |
| license_model | from the licence text (GPL/BSD/MIT… → open-source; proprietary/EULA → commercial; freeware → freeware); otherwise from the page's grouping ("Comparison of proprietary EDA software"); for vendor pages, "commercial" only with sales evidence (contact sales, request a demo, pricing) | `common.license_model_from` |
| country_region | the **vendor's** Wikipedia infobox "Headquarters" → last recognised country token ("Sunnyvale, California, U.S." → United States; a US state → United States) | `collect_vendor_origin.py`, `common.country_from_text` |
| region | fixed country→continent table | `common.COUNTRY_REGION` |
| first_release_year | infobox "Initial release" only | `collect_wikipedia_articles.py` |
| latest release | version + date + year taken **together from one record**: the source reporting the most recent release | `deduplicate_data.py` |

Why rule-based and not hand-labelled? The brief forbids made-up values; a written rule is **reproducible, auditable and
explainable**. It can be wrong, but it's wrong *consistently* and can be fixed in one place.

### 5.4 Deduplication = entity resolution (expect deep questions here)
Problem: the same tool appears in several sources with different spellings ("Zuken CR-8000" vs "CR-8000", "Incisive"
under its article "NCSim").

**Merge keys** (any one is enough):
1. same GitHub repository `owner/repo`;
2. same English Wikipedia article;
3. same normalised name (lower-case, alphanumerics only, vendor prefix such as "Synopsys " removed) **and** compatible vendor.

**Union-find (disjoint-set)**: each record starts as its own set; every match `union`s two sets; at the end each set =
one tool. Path compression keeps `find` near O(1). Why union-find? Matches are **transitive** (A=B via repo, B=C via
name ⇒ A=C) and union-find handles that naturally.

**The transitivity trap (a bug the test caught; tell this story!):** a record with an *empty* vendor is "compatible"
with everyone, so it could join "Forge by Vendor A" and "Forge by Vendor B" into one tool. The fix checks the new
record against **all vendors already in the group**, not just the pair. That's the fixture test `example-forge` /
`example-forge-2`.

**Conflict resolution:** per-field **source priority** (`FIELD_PRIORITY`), e.g. licence prefers GitHub's SPDX id, vendor
name prefers the vendor's own site. Real conflicts (licence model, first-release year) go to `review_queue.json`.
Different tools sharing a website path, and same-name-different-vendor cases, are queued, **never auto-merged**.
Precision over recall: a wrong merge destroys information; a missed merge only leaves a duplicate for review.

### 5.5 Validation and quality
`validate_dataset.py` fails the run on: wrong columns, duplicate `tool_id`, missing/invalid `source_url`, missing date,
no provenance, unverified source, values outside vocabularies, region ≠ country's continent, first release > latest
release. It also prints **coverage** (licence models, regions, categories) against the brief's requirements.
`data_completeness.png` shows the % of rows where each field is filled: an honest picture of what public sources reveal.

### 5.6 Provenance / traceability (acceptance criterion 4)
- `source_url` = primary page; `source_types`, `source_count`.
- `provenance.csv` = one line per contributing page, with `fields_reported` (which fields that page supplied).
- Demo: notebook section 6 traces `kicad`, `verilator` and `synopsys-primetime` back to every URL.

---

## 6. Analysis and plots (P1)

| Plot | Question it answers | Design choice to mention |
|---|---|---|
| `tools_by_category.png` | Which flow stages have most tools, and how commercial vs open? | horizontal bars in **flow order** (not sorted by size) so it reads like the design flow; stacked by licence model |
| `license_distribution.png` | Commercial vs open-source vs freeware | counts + %, direct labels |
| `tools_by_region.png` | Where tools come from | only tools with a *documented* country; the title states how many |
| `release_activity.png` | Release activity over time | **two panels** (first release, latest release) instead of a dual-axis chart, because they are different measures |
| `platform_support.png` | OS support by licence model | grouped bars |
| `data_completeness.png` | How complete is each field | shows the limits openly |
| `languages_formats.png`, `top_vendors.png` | Formats and the biggest vendors | top-15 only |

Colour: a colour-blind-validated categorical palette in fixed order (commercial = blue, open-source = orange,
freeware = aqua, unknown = grey), with the same colour meaning the same thing in every chart. PNGs are saved without a
version stamp, so the same CSV gives byte-identical images (acceptance criterion 3).

**Insights to state** (verify against `outputs/findings.md` before the panel): see the cheat sheet's numbers block.
Phrase findings as *"in the collected catalog…"*, never *"in the world…"*, because the sample is source-biased (§9).

---

## 7. File-by-file walkthrough (what to say when they open a file)

| File | One-line explanation |
|---|---|
| `scripts/common.py` | shared schema, vocabularies, keyword rules, polite HTTP + robots, normalisers (dates, years, platforms, countries) |
| `scripts/htmlparse.py` | stdlib HTML: tables with rowspan/colspan, infobox, page meta |
| `scripts/collect_published_lists.py` | Wikipedia comparison/list pages → one record per table row; category from section heading |
| `scripts/collect_wikipedia_articles.py` | each tool's infobox → first/latest release, OS, licence, website, repo |
| `scripts/collect_vendor_origin.py` | developer company infobox → country |
| `scripts/collect_vendor_sites.py` | official product pages (seed) → vendor, category, sales evidence; kept only if HTTP 200 **and** product name on page |
| `scripts/collect_public_repositories.py` | GitHub API with rate-limit handling |
| `scripts/collect_documentation.py` | docs pages → platform/format mentions (weak evidence, installation context only) |
| `scripts/clean_data.py` | normalise, vocabularies, drop unverified, log issues |
| `scripts/deduplicate_data.py` | union-find merge, field priority, release triple, provenance, review queue |
| `scripts/validate_dataset.py` | integrity + coverage checks; non-zero exit on error |
| `scripts/run_analysis.py` | tables, 8 plots, `summary.json`, `findings.md` |
| `scripts/pipeline.py` | orchestrator; fixes snapshot date once; runs each step with Crucible's Python `-s` |
| `scripts/check_environment.py` | proves isolation inside Crucible; lists catalog gaps |
| `data/metadata/seed_tools.json` | discovery list: names + URLs only, **no values** |
| `tests/test_pipeline.py` | offline fixture test: merges, exclusions, review queue, country join, release triple |
| `notebooks/analysis.ipynb` | same plots via `run_analysis.main()` + row tracing + numpy cross-tab |

---

## 8. Python concepts used (P2)
`urllib.request` (HTTP), `urllib.robotparser`, `urllib.parse.quote` (non-ASCII URLs such as "TINA–TI"), `html.parser.HTMLParser`
(event-driven parser: `handle_starttag/endtag/data`), `re` (keyword rules; careful with `\b` word boundaries), `csv.DictReader/
DictWriter`, `json`, `pathlib`, `collections.Counter/defaultdict`, `subprocess.run` (pipeline), `argparse`, `sys.executable`
(run children with the *same* interpreter igny chose), `site.getusersitepackages()` (isolation check), numpy arrays for the
cross-tab, matplotlib `Agg` backend (no display needed).

---

## 9. Limitations, said confidently (never hide them; panels reward honesty)
1. **Source bias.** Wikipedia's tables over-represent PCB/analog/HDL-simulation tools; big commercial IC tools come from a
   ~60-entry discovery seed. The dataset is *a well-sourced catalog*, not a census.
2. **Seed = human choice of *which* URLs to read** (not of values). Defence: every value is still read from the page, and the
   seed is versioned and documented. Next step: discover from more lists automatically.
3. **Country** only when the vendor's Wikipedia article exists; individual maintainers and communities have none. Region
   counts use documented origins only (60 of 131), and the plot title says how many. Europe (5) and Asia (4) are thin:
   Empyrean, Gowin, Efinix, Primarius, Sigasi and Defacto have no English Wikipedia HQ field.
   **Measurement bias to mention yourself:** open-source tools look more recently released (22 of 29 since 2024 vs 9 of 21
   commercial), partly because their dates come live from GitHub while commercial dates come from stale Wikipedia infoboxes.
4. **Keyword rules can misclassify** (e.g. a multi-product homepage). Mitigation: the evidence text is kept in the raw
   record (`_evidence`), and rules are in one place.
5. **Documentation keyword evidence is weak** (mentions ≠ support).
6. **GitHub rate limit** → without a token, some repos are skipped (logged).
7. **Wikipedia release data can be stale** (e.g. ADS listed as 2019). We record what the source says on that date.
8. Some vendor pages **block bots (403)**: Keysight, one Cadence page. They're logged and excluded, not faked.

## 10. "What would you do next?"
- Use the **Wikidata JSON dumps** (bulk download, allowed) instead of SPARQL for structured developer/country/licence data.
- Add sources: awesome-lists (e.g. awesome-open-hardware), conference exhibitor lists (DAC), EDA vendor product indexes, PyPI.
- Request a GitHub token in CI; add GitLab/SourceForge APIs.
- Text classification (TF-IDF + logistic regression) for category, once there's a labelled set, while keeping the rules as the baseline.
- Scheduled monthly collection + diff between snapshots ("which tools released this month").
- A Streamlit/Voilà dashboard (both are in the Crucible catalog!).

---

## 11. Likely panel questions with model answers

**Crucible / reproducibility**
1. *What does "entirely on Crucible" mean in your project?* - Env and workspace created with `igny`; numpy, matplotlib,
   jupyterlab installed with `igny tool install`; every script runs with `igny run script` (Crucible's own Python); the notebook
   runs with `igny run jupyter`; locked with `igny workspace lock`. `check_environment.py` proves it at run time.
2. *How would I reproduce it?* - Clone, `igny workspace sync`, `igny run script ./scripts/pipeline.py`. Sync reads the lock and
   installs the exact versions; the pipeline rebuilds from the committed snapshot, so the plots match the report.
3. *Difference between crucible.toml and crucible.lock?* - toml = identity + selected environment (intent); lock = exact bound
   tools, versions, sources, checksums (resolution). Sync uses the lock.
4. *Selected vs active environment?* - Selected is per project (toml); active is machine-global. igny resolves: CRUCIBLE_ENV →
   toml → last activated → default.
5. *What if a library you need isn't in the catalog?* - The brief says don't install it another way: use stdlib/catalog and record
   the gap. pandas → csv + Counter + numpy; bs4 → html.parser.
6. *Did you find anything wrong with Crucible?* - Yes, the user-site leak (§3.5-3), bundled-only requests/bs4, no pandas, `--version`
   shows `dev`, igny not on Git-Bash PATH.

**Data collection**
7. *Why not just scrape Google or use an LLM to list tools?* - Not traceable, and values could be hallucinated or made up. The brief
   requires every row to have a source URL.
8. *Why not Wikidata SPARQL?* - robots.txt disallows `/sparql`. We followed it. The JSON dumps are the compliant next step.
9. *How do you stay polite?* - robots.txt check, 1-1.5 s spacing, identifying User-Agent with contact, public pages only, GitHub rate
   headers respected.
10. *A vendor page returns 403. What happens?* - Logged in `collection_log_<date>.jsonl`, record excluded; nothing is invented.
11. *Isn't the seed file hand-entered data?* - It's a discovery list of URLs, not values. Every field comes from the fetched page,
    the record is kept only if HTTP 200 and the product name appears on the page.
12. *Why stdlib HTML parsing?* - bs4 isn't a declared Crucible tool, so it's not locked. I wrote a small parser that handles
    rowspan/colspan and infoboxes.

**Data quality / dedup**
13. *How do you deduplicate?* - Union-find over three merge keys (repo, Wikipedia article, name+compatible vendor); ambiguous cases
    go to a review queue; per-field source priority resolves values.
14. *Why union-find?* - Matches are transitive; union-find groups connected records in near-linear time.
15. *Tell me about a bug you found.* - The empty-vendor bridging bug (§5.4), caught by the fixture test; fixed by checking group-level vendors.
    Also the original repo's shared-website check never ran because it looped over an empty list.
16. *Why keep version and date from the same source?* - Mixing them could pair version X with the date of release Y: an invented fact.
17. *How do you handle missing values?* - Leave empty, never impute; report completeness per field.
18. *How do you know the category is right?* - It comes from the source's own grouping or wording via written rules; spot-checked; misclassification
    is a stated limitation, and the evidence is kept for audit.

**Analysis**
19. *What does the data show?* - "In the collected catalog: simulation is the biggest category (39 primary, 72 counting secondary);
    implementation and sign-off are small and almost all commercial, the open-source exception being OpenROAD; 51 % commercial,
    34 % open-source; of the 60 tools with a known vendor country, 49 are US, which reflects the Big Three being US-headquartered
    plus a measurement effect."
20. *Why no dual-axis chart for release activity?* - Two different measures; two panels on one unit avoid a misleading visual correlation.
21. *Is your region chart biased?* - Yes: only tools with a documented vendor country; the title says how many. Communities have no HQ.
22. *Why not pandas?* - Not in the Crucible catalog; Counter + csv + numpy are enough for counting and cross-tabs.

**Engineering**
23. *How is it tested?* - Offline fixture test with synthetic tools: exclusion of unverified sources, cross-source merge, vendor conflict → review,
    empty-vendor bridging, country join, release triple, provenance. Plus `validate_dataset.py` on real data.
24. *How would you scale to 10,000 tools?* - Blocking keys (already: repo/wiki/name), parallel fetch per domain with per-domain rate limits,
    caching with ETags, a database (SQLite is in the stdlib) instead of JSON files.
25. *Why one collector per source?* - Required by the brief; also isolation: a failing source doesn't break others, and each has its own raw snapshot.

**Behavioural**
26. *What was the hardest part?* - Reconciling records across sources without guessing (entity resolution + provenance), and staying inside
    the Crucible and robots.txt constraints at the same time.
27. *What would you do differently?* - Start from the robots-compliant structured source (Wikidata dumps) earlier; ask for a GitHub token up front.
28. *Did you use AI tools?* - **Be honest.** If you used an AI coding assistant, say so, and then show you understand every decision (this guide).
    Panels respect transparency plus understanding; they penalise discovered concealment.

---

## 12. Live demo script (5-7 minutes; rehearse it!)
```bash
cd global-eda-tools-explorer
igny status                                         # workspace + env + lock present
igny env show eda-data                              # numpy, matplotlib, jupyterlab [pip]
igny run script ./scripts/check_environment.py      # isolation proof + catalog gaps
igny run script --dry-run ./scripts/pipeline.py     # shows Crucible's Python is used
igny run script ./scripts/pipeline.py               # rebuild from snapshot: clean -> dedup -> validate -> plots (fast, offline)
igny run script ./tests/test_pipeline.py            # PASS
```
Then open `outputs/tools_by_category.png` and `tools_by_region.png`, and the notebook section 6 (row tracing).
Have `data/processed/provenance.csv` open, filtered on one tool. **Don't run `--collect` live** (~10 min, needs network).
Show `data/raw/collection_log_<date>.jsonl` instead to prove a real live collection happened and what failed.

## 13. Pitfalls - don't say these
- ❌ "This is every EDA tool in the world." → ✅ "a traceable catalog of N tools from 6 source types."
- ❌ "Siemens is German so…" → ✅ "we use headquarters, which is the US for Siemens EDA."
- ❌ "I guessed / assumed the licence." → ✅ "derived by rule X from the licence text the source states."
- ❌ "pip install pandas would have been easier." (it violates the brief) → ✅ "pandas is a recorded gap."
- ❌ Blaming tools for gaps → ✅ state the gap, its effect, and the next step.

## 14. Glossary (quick recall)
RTL · HDL · netlist · standard cell · PDK (process design kit) · STA · DRC · LVS · GDSII · tape-out · SPICE · HLS · UVM ·
formal verification · equivalence checking · P&R · CTS (clock-tree synthesis) · IR drop · EM (electromigration) · Gerber ·
FPGA bitstream · SPDX (standard licence ids) · robots.txt · rate limit · provenance/lineage · entity resolution ·
union-find · controlled vocabulary · idempotent (sync can be re-run safely) · deterministic output · snapshot.
