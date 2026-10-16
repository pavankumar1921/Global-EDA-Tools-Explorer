# Panel answers: full answers to the 28 questions in teacher.md

How to use this: for each question, say the **short answer** first (one sentence), then the **full answer**
if they want more. Use **"If they push"** only when they dig deeper. Speak in your own words; don't recite.
All numbers are from the committed snapshot (2026-10-15).

---

## Part A - Crucible and reproducibility

### Q1. What does "entirely on Crucible" mean in your project?
**Short:** Every tool, library and script in the project is installed and run through `igny`; nothing is installed or run outside it.

**Full:** I created the environment with `igny env create eda-data` and made the project folder a workspace bound to it
with `igny workspace create eda-data-science --path . --env eda-data`. I checked `igny catalog` and installed numpy,
matplotlib and jupyterlab with `igny tool install`; I never used system pip. Every script runs with
`igny run script`, which uses Crucible's own Python 3.12 with the bound tools on its path, and the notebook runs with
`igny run jupyter`. Finally I locked the workspace with `igny workspace lock`. To prove it at run time, the first
pipeline step, `check_environment.py`, checks that the interpreter is Crucible's, that `CRUCIBLE_ENV` is set, and that
numpy and matplotlib load from Crucible's tools folder. If any check fails, the run stops.

**If they push:** "I also found that Crucible's Python can still see the user's personal site-packages, so I run every
step with `python -s` and `PYTHONNOUSERSITE=1` to keep it fully isolated."

### Q2. How would I reproduce your project on my machine?
**Short:** Clone the repo, run `igny workspace sync`, then `igny run script ./scripts/pipeline.py`.

**Full:** `igny workspace sync` reads `crucible.lock`, creates the `eda-data` environment if it doesn't exist, and installs
exactly the locked versions: numpy 2.5.4, matplotlib 3.11.2 and jupyterlab 4.6.4. Then `pipeline.py` rebuilds the dataset
and every plot from the committed raw snapshot, so you get the same plots as the report. I tested this by
simulating a fresh machine: I pointed Crucible at empty folders (`CRUCIBLE_ROOT` and `IGNYTION_HOME`), ran sync,
and the pipeline rebuilt with 0 errors. I also ran the rebuild twice and the PNGs and CSV were byte-identical (same MD5).
If you want *fresh* data instead, run `pipeline.py -- --collect`.

**If they push:** "Reproducing the *plots* is deterministic because they come from a dated snapshot. A *fresh
collection* will differ slightly, because websites change; that's expected and the snapshot date records it."

### Q3. What's the difference between crucible.toml and crucible.lock?
**Short:** The toml says *which* environment the project uses; the lock records *exactly what* is in it.

**Full:** `crucible.toml` is the workspace marker. It holds the workspace name, a stable ID and the selected environment
(`eda-data`); without it, the folder isn't a workspace. `crucible.lock` is written by `igny workspace lock` and records
every bound tool: name, version, source (pip, artifact or docker), platform and checksum where available. When someone
runs `igny workspace sync`, Crucible reads the **lock**, not the toml, so they get the identical toolchain. That's why
the brief says to commit both together. It's like `pyproject.toml` versus `poetry.lock`, or `package.json` versus
`package-lock.json`.

**If they push:** "The lock has weaknesses I documented: pip tools have `checksum: null`, so there's no hash pinning, and every entry
is tagged `windows-x86_64`, so reproducing on Linux from this lock is untested."

### Q4. What's the difference between the selected and the active environment?
**Short:** Selected is per project, written in crucible.toml; active is a machine-wide "currently switched on" setting.

**Full:** The selected environment is recorded in the workspace's `crucible.toml`: it's the project's preference.
The active environment is global runtime state, set with `igny env activate`. When `igny run` needs an environment, it
checks in this order: the `CRUCIBLE_ENV` variable, then the workspace's toml, then the last activated environment, then the
managed default. So `igny status` shows my env as "inactive", but my scripts still run in `eda-data` because the
workspace's toml selects it. Inside my scripts, `CRUCIBLE_ENV` shows `eda-data`, which confirms that.

### Q5. What if a library you need isn't in the Crucible catalog?
**Short:** The brief says not to install it any other way, so I used the standard library and recorded the gap.

**Full:** The catalog has numpy, matplotlib and jupyterlab, but not pandas, scipy, seaborn, requests or BeautifulSoup as
tools. For HTTP I used `urllib` from the standard library; for HTML parsing I wrote a small parser on `html.parser`;
for tables and group-bys I used `csv`, `collections.Counter` and numpy. Each missing library is recorded in
`requirements-notes.md` and in the report's "where Crucible fell short" section, with its effect: mostly more code
than pandas would need, but no loss of capability for this analysis.

### Q6. Did you find anything wrong with Crucible?
**Short:** Yes, five things: missing data libraries, hidden bundled dependencies, an isolation leak, a weak lock file, and some CLI rough edges.

**Full:**
1. **No pandas or scipy** in the catalog.
2. **Hidden bundled dependencies:** requests and bs4 can be imported only because jupyterlab bundles them. They're not in the
   lock, so I didn't rely on them. On a fresh machine, numpy was even loaded from **matplotlib's bundled copy**,
   not the numpy tool, so the PYTHONPATH order decides which version you get.
3. **Isolation leak:** Crucible's Python still sees the user's personal site-packages. `import scipy` worked inside
   `igny run script` although scipy isn't in Crucible. I blocked it with `python -s` and a check script.
4. **Lock file:** no checksums for pip tools, no transitive dependencies, and Windows-only platform tags.
5. **CLI:** `igny` wasn't on the Git-Bash PATH after install, and `igny --version` prints `dev` instead of a version.

**If they push:** "None of these stopped the project, but points 2 to 4 matter for reproducibility, which is Crucible's
main promise, so I reported them."

---

## Part B - Data collection

### Q7. Why not just Google the tools, or ask an AI/LLM to list them?
**Short:** Because neither gives a traceable source for each value, and the brief forbids made-up values.

**Full:** The brief requires every row to record the URL it came from and the date, with no hand-entered rows and
no made-up values. An LLM can produce plausible but wrong facts (wrong release year, wrong country), and you can't
point to where each value came from. Search-engine results aren't a stable, citable source either. My collectors
fetch real public pages, read only what those pages state, and store the URL and date with every value, so any
cell can be checked.

### Q8. Why didn't you use Wikidata's SPARQL endpoint? It's the obvious structured source.
**Short:** Its robots.txt disallows `/sparql` for automated clients, and the brief says to follow robots.txt.

**Full:** I evaluated it first; it would have given developer, country, licence and release dates in one query. But
`query.wikidata.org/robots.txt` says `Disallow: /sparql`, and Wikipedia's API paths are disallowed for crawlers too.
So I used only the normal `/wiki/` article pages, which robots.txt allows: the comparison tables, each tool's infobox,
and each developer company's infobox. The compliant way to use Wikidata at scale would be its downloadable JSON dumps,
which is my first "next step".

**If they push:** "The constraint actually shaped the architecture: it's why I wrote a table and infobox parser."

### Q9. How did you make sure the collection was polite and legal?
**Short:** It checks robots.txt, waits between requests, identifies itself, and reads only public pages.

**Full:** Before fetching any page, the code reads that site's robots.txt with Python's `robotparser` and skips
disallowed URLs. It waits at least 1.5 seconds between page requests and 1 second between API calls. The User-Agent
names the project and a contact address. It reads only public pages, with no logins and no paywalls. For GitHub it uses the official
REST API, reads the `X-RateLimit-Remaining` header and stops cleanly at the limit. If robots.txt can't be reached,
the code treats the site as *not allowed*; it fails safe.

### Q10. What happens when a vendor page returns 403 or fails?
**Short:** It's logged and the record is excluded. Nothing is invented to fill the gap.

**Full:** Every failure goes into `data/raw/collection_log_2026-10-15.jsonl` with the URL, status and error. Network errors
are retried up to 4 times with backoff. If the page still fails, that record never enters the dataset, because the
cleaning step keeps only records whose source returned HTTP 200. In the final snapshot, Keysight's ADS product page
returned 403 (bot protection), so ADS's data comes only from Wikipedia. A tool that existed *only* through a failed
page is dropped completely rather than kept with guessed values.

### Q11. Isn't your seed file hand-entered data?
**Short:** No. It's a list of *which pages to read*, not of values. Every value is read from the page itself.

**Full:** The original version of the project did have hand-typed values in the seed (country, category, licence), and
some were wrong; I removed them all. Now `seed_tools.json` holds only tool names and URLs: product page, GitHub repo,
docs page or Wikipedia article. I needed it because Wikipedia's comparison tables cover PCB, analog and HDL simulation
tools but not the big chip-implementation tools like Design Compiler, Innovus or PrimeTime. For seed tools, the vendor
name, category and licence model are read from the fetched page. A record is kept only if the page returns 200 **and**
the product name actually appears on it.

**If they push:** "The honest limitation is that *choosing which URLs to read* is a human decision. I state that in
the report as a source of bias."

### Q12. Why did you write your own HTML parser instead of using BeautifulSoup?
**Short:** BeautifulSoup isn't a Crucible tool, so using it would break the "entirely on Crucible" rule.

**Full:** bs4 is importable only because jupyterlab bundles it; it's not in the lock and could disappear in a future
version. So I wrote `htmlparse.py` on the standard library's `html.parser`. The tricky part is Wikipedia tables: cells
can span several rows or columns (`rowspan`/`colspan`), and some "Yes/No" cells are coloured by CSS class instead
of text. My parser rebuilds the full grid so every column lines up, merges two-row headers, reads the yes/no
classes, and extracts infoboxes even when tables are nested.

---

## Part C - Data quality and deduplication

### Q13. How do you deduplicate?
**Short:** Records are merged when they share a GitHub repo, a Wikipedia article, or the same name with a compatible vendor; anything ambiguous goes to human review.

**Full:** The same tool shows up in several sources under different spellings, for example "CR-8000" and "Zuken CR-8000". I use
three merge keys: the same GitHub repository, the same Wikipedia article, or the same normalised name (lower-case,
letters and digits only, vendor prefix like "Synopsys " removed) *with* a compatible vendor. Records are grouped with
union-find. Then each field takes its value from the most trusted source for that field (for example, licence from
GitHub's SPDX id, vendor name from the vendor's own site). The result is 268 source records → 131 tools, with 89 tools
combining 2 to 6 sources. Cases like "same name, different vendor" are **not** merged automatically. They go to
`review_queue.json`, and a human decision with a written reason goes into `review_decisions.json`.

### Q14. Why union-find?
**Short:** Because matches are transitive, and union-find groups linked records efficiently.

**Full:** If record A matches B by repository, and B matches C by name, then A, B and C are all the same tool, even though
A and C share nothing directly. Union-find (disjoint-set) handles this naturally: each record starts in its own set,
every match unites two sets, and at the end each set is one tool. With path compression it runs in almost linear time,
so it scales well.

**If they push:** "Transitivity is also its risk. That's exactly the bug in the next answer."

### Q15. Tell me about a bug you found and fixed.
**Short:** A record with no vendor could wrongly join two different companies' tools into one, and my test caught it.

**Full (STAR):**
- **Situation:** dedup merges same-name records if their vendors are "compatible", and an empty vendor counts as compatible with anyone.
- **Task:** make sure two different tools with the same name, from different vendors, never merge.
- **Action:** my fixture test has "Forge by Vendor A" and "Forge by Vendor B" plus a record with no vendor. The test
  failed: the empty-vendor record bridged both into one tool, because union-find is transitive. I changed the check so a
  new record must be compatible with **all** vendors already in the group, not just one.
- **Result:** the test passes, and the two tools stay separate.

**Second story, if they want one:** the name "OpenROAD" on Wikipedia is actually Actian's business-software IDE, not the
chip tool. My vendor check refused to merge them, which exposed that I'd linked the wrong article, so I fixed the seed.

### Q16. Why do you take the version and the release date from the same source?
**Short:** Mixing them could pair one release's version with another release's date, which would be an invented fact.

**Full:** Different sources report different "latest" releases. GitHub might say v2.1 from 2026 while Wikipedia
says v1.9 from 2024. If I took the version from one and the date from the other, I'd create a combination nobody
published. So I take version, date and year together, from the single source reporting the most recent release.

### Q17. How do you handle missing values?
**Short:** I leave them empty and never guess, and I report how complete each field is.

**Full:** The brief says a field that can't be found stays empty. I don't impute anything, so empty means "no source stated
it", not "no" or "zero". Then I measure it: `data_completeness.png` shows the percentage filled per field. Vendor is
95%, category 96% and licence model 90%, while first release year is only 23%, because many vendors don't publish it. That
honesty is part of the result: it shows what public information exists.

### Q18. How do you know your categories are correct?
**Short:** They come from what the source itself says, through written keyword rules, and I spot-checked the results.

**Full:** For list pages, the category comes from the table's own heading. A tool in "Comparison of proprietary
software for PCB design" is `pcb-design`, and the most specific heading wins. For vendor pages, I take the first category
keyword in the vendor's own summary sentence; for example, "Design Compiler offers best-in-class RTL synthesis…" gives
synthesis. The rules are in one place (`common.py`), so they're reproducible and auditable. I spot-checked known tools
(KiCad → PCB, SPICE → analog, PrimeTime → timing sign-off) and fixed the rules where they were wrong. The raw records
keep the evidence text.

**If they push:** "Rules follow marketing wording. Cadence now sells 'Innovus+ Synthesis and Implementation', so Innovus
comes out as synthesis with place-and-route as a secondary category. I document that as a limitation."

---

## Part D - Analysis

### Q19. What does your data show?
**Short:** Simulation tools dominate, implementation and sign-off are small and almost all commercial, and most tools with a known origin are American.

**Full:** In the collected catalog of 131 tools:
- **Category:** simulation is the largest (39 as main category, 72 counting secondary), then PCB (27) and analog (22).
  Place-and-route, timing sign-off and HLS are small and almost all commercial; the open-source exception is OpenROAD.
- **Licence:** 51% commercial, 34% open-source, 5% freeware.
- **Region:** of the 60 tools with a known vendor country, 49 are US. That reflects the Big Three (Synopsys, Cadence,
  Siemens EDA) being US-headquartered, plus a measurement effect: companies have a headquarters, communities don't.
- **Release activity:** 36 of the 58 tools with a known release shipped something in 2024 to 2026; the oldest first release is 1973 (SPICE).

**If they push:** "Open-source *looks* more active (22 of 29 released since 2024 versus 9 of 21 commercial), but part of
that is the source: GitHub dates are live, while Wikipedia's commercial dates are often stale. I'd be careful
concluding anything from it."

### Q20. Why didn't you use a dual-axis chart for release activity?
**Short:** First releases and latest releases are different measures, and a second y-axis can create a misleading visual correlation.

**Full:** With two y-axes you can make two lines appear to move together just by choosing the scales. I used two
panels sharing the same x-axis (years) and the same unit (number of tools): first release year on top, latest release
year below. That way the reader compares them honestly.

### Q21. Is your region chart biased?
**Short:** Yes, and I show it: it only counts tools with a documented vendor country, and the chart title says how many.

**Full:** Country comes from the vendor company's headquarters. Open-source communities and individual developers
don't have one, and several Asian and European vendors (Empyrean, Gowin, Efinix, Sigasi) have no English Wikipedia
headquarters field. So only 60 of 131 tools have a country, and the US share is inflated. The chart title states
"60 of 131 tools have a documented vendor country". To improve it, I'd add company registries or Wikidata dumps.

### Q22. Why didn't you use pandas?
**Short:** pandas isn't in the Crucible catalog, and the brief forbids installing it another way.

**Full:** The analysis is mainly counting and cross-tabulating, so `csv.DictReader` plus `collections.Counter` plus numpy
handles it fine. For example, the category-by-licence cross-tab in the notebook is a numpy array. It took more lines
than pandas would, and I recorded that as a Crucible gap in the report.

---

## Part E - Engineering

### Q23. How is the project tested?
**Short:** An offline end-to-end test runs the whole pipeline on made-up fixture data and checks every rule, and the validator checks the real data.

**Full:** `tests/test_pipeline.py` runs through `igny run script`. It creates a temporary project with synthetic tools
("Example Sim", "Example Forge") and runs clean → dedup → validate → analysis. It checks that an unverified (404) source is
excluded, that records from different sources merge, that two vendors with the same tool name stay separate and go to
review, that country is joined from the vendor record, that version and date stay together, and that provenance is kept.
It also unit-tests the date, country, platform and category rules. On the real data, `validate_dataset.py` fails the run on
any error (schema, duplicate IDs, missing source URL, values outside the vocabularies) and prints coverage. The final
result is 0 errors.

### Q24. How would you scale this to 10,000 tools?
**Short:** Use bulk sources, parallel per-site fetching, caching, and a database instead of JSON files.

**Full:**
1. **Bulk sources:** use Wikidata JSON dumps instead of fetching one page at a time.
2. **Parallel fetching:** fetch different websites in parallel, while keeping the polite delay per site.
3. **Caching:** cache pages with ETags so unchanged pages aren't downloaded again.
4. **Storage:** move from JSON files to SQLite, which is in Python's standard library, so still Crucible-compliant.
5. **Dedup:** the dedup already uses blocking keys (repository, article, name), so it won't compare every pair.
6. **Review:** grows with the data, so I'd prioritise review items by confidence.

### Q25. Why one collector per source?
**Short:** The brief requires it, and it keeps sources independent.

**Full:** Each collector writes its own dated raw file, so a failing source (for example a site that blocks bots) doesn't break
the others. I can re-run just one source, and each source's rules stay in one small script that's easy to explain and
test. It also makes provenance clean: every record knows its source type.

---

## Part F - Behavioural

### Q26. What was the hardest part?
**Short:** Combining records from different sources into one correct row per tool without ever guessing.

**Full:** Each source names tools and vendors differently, and some names collide (OpenROAD the chip tool versus OpenROAD the
business IDE). I had to merge aggressively enough to avoid duplicates, but carefully enough never to merge two
different tools, and keep every value traceable. Doing that while staying inside Crucible (no pandas) and inside
robots.txt (no Wikidata SPARQL) made it a real engineering problem, not just scraping.

### Q27. What would you do differently?
**Short:** Start from a bulk structured source like the Wikidata dumps, and get a GitHub token from day one.

**Full:** I'd use Wikidata's downloadable dumps from the start for developer, country and licence data, which would
fill the country and first-release gaps. I'd use a GitHub token to avoid the 60-requests-per-hour limit. I'd also write the
fixture tests *before* the dedup code: the tests caught two real bugs, so writing them earlier would have saved time.

### Q28. Did you use AI tools to build this?
**Answer honestly; this matters more than any other answer.** Say only what is true. A truthful version could sound like:

> "Yes. I used an AI coding assistant, Claude Code, to help write and debug parts of the code and the documentation.
> I directed the work, checked the results against the problem statement, ran everything myself through Crucible,
> and made sure I understand every decision: why we avoided SPARQL, how the dedup works, why fields stay empty. I'm
> happy to walk through any file or change something live."

Then prove it: be ready to open any script and explain it, using `teacher.md` §7 as your map. Panels respect
transparency combined with real understanding. They penalise it heavily if they discover something you concealed.

---

## Bonus: 3 more questions panels often ask

**"Walk me through the pipeline."** Six collectors → dated raw JSON files in `data/raw` → `clean_data.py` normalises
values and drops unverified sources → `deduplicate_data.py` merges into one row per tool and writes provenance →
`validate_dataset.py` checks integrity and coverage → `run_analysis.py` writes the plots and findings. `pipeline.py` runs them all
in order through Crucible.

**"Show me where one value came from."** Open `provenance.csv` and filter on `kicad`. It shows two pages: the Wikipedia
comparison table (category, licence, platforms) and KiCad's Wikipedia article (first release 1992, latest version 10.0.6).

**"Is this every EDA tool in the world?"** "No. It's a traceable catalog of 131 tools from 6 public sources, covering every flow
stage, both licence models and four continents. The pipeline is built to grow: adding a source adds tools,
and every new row will still be traceable."
