# Panel cheat sheet - read this 15 minutes before you go in

## Pitch (30 s)
"I built a reproducible pipeline, running entirely on Crucible, that collects EDA-tool information from public
sources worldwide and produces one deduplicated, traceable row per tool: **131 tools, 6 source types,
268 source records, all 10 flow stages from HLS to sign-off plus PCB and FPGA, commercial + open-source +
freeware, vendors on 4 continents**. Every row has its source URL and date; nothing is hand-typed or guessed;
the workspace is locked and reproduces on an empty machine with `igny workspace sync`."

## Numbers to quote (snapshot 2026-10-15)
| | |
|---|---|
| Tools / source records / multi-source tools | **131 / 268 / 89** |
| Licence model | commercial **67** (51 %) · open-source **44** (34 %) · freeware **7** · unknown 13 |
| Largest category | simulation **39** primary (72 incl. secondary) · PCB 27 · analog 22 |
| Regions (60 tools with a documented country) | N. America **49** · Europe **5** · Asia **4** · Oceania 2 |
| Top vendors | Cadence 15 · Synopsys 9 · Siemens 5 · Zuken 3 · YosysHQ 3 |
| Release activity | 36 of 58 tools with a known release shipped in 2024-26; earliest first release 1973 (SPICE) |
| Completeness | vendor 95 % · category 96 % · licence model 90 % · first release 23 % · repo 23 % |
| Validation | **0 errors**, 5 warnings; fixture test PASS; byte-identical rebuilds |

## The 6 sources (one collector each)
Wikipedia lists · Wikipedia tool infoboxes · developer company infoboxes (country) · vendor product pages
(seed) · GitHub API · documentation pages.

## Crucible in one breath
`igny env create eda-data` → `igny workspace create … --env eda-data` → `igny tool install numpy matplotlib jupyterlab`
→ `igny run script ./scripts/pipeline.py` → `igny workspace lock` → teammate: `igny workspace sync`.
Resolution order: CRUCIBLE_ENV → crucible.toml → last activated → default. **Lock = exact versions; sync reads the lock.**

## Crucible shortfalls (have 3 ready)
1. No pandas/scipy/bs4/requests as tools → stdlib + numpy.
2. User site-packages leak into Crucible's Python (scipy imported) → `python -s` + fail-fast check.
3. numpy loaded from matplotlib's *bundled* copy on a fresh machine → version shadowing risk.
4. Lock: pip tools have `checksum: null`, no transitive deps, `platform: windows-x86_64` only.
5. igny not on Git-Bash PATH; `--version` prints `dev`.

## Design decisions → one-line "why"
| Decision | Why |
|---|---|
| No Wikidata SPARQL / Wikipedia API | robots.txt disallows them; used allowed `/wiki/` pages |
| Rules, not hand labels, for category/licence | brief forbids made-up values; rules are reproducible + auditable |
| Seed = URLs only | big IC tools are missing from Wikipedia tables; values still come from the pages |
| Union-find dedup + review queue | transitive matches; ambiguous → human, never guessed |
| Group-level vendor check | stops an empty-vendor record bridging two vendors (bug found by test) |
| Version + date from ONE record | never pair one source's version with another's date |
| Freeware beats commercial | freeware *is* proprietary-but-free, so the sources agree |
| Two-panel release chart | different measures, no dual axis |
| Dated raw snapshot, never edited | rebuild = same plots; audit any value |

## Best stories (STAR format)
1. **OpenROAD name collision** - Wikipedia "OpenROAD" = Actian's business IDE; vendor check refused the merge → found and fixed the seed.
2. **Empty-vendor bridging bug** - fixture test caught union-find transitivity merging two vendors; fixed with group-level check.
3. **Category leak bug** - one row's override changed the table-level variable, so all later rows became "simulation"; found by spot-checking SPICE.
4. **Ansys → Synopsys** - RedHawk-SC URL now redirects to synopsys.com: live data catches industry change.
5. **Measurement bias** - open-source looks "more active" partly because GitHub dates are live and Wikipedia's commercial dates are stale.

## Limitations (say them before they ask)
Not a census · thin Europe/Asia (no HQ data for Empyrean, Gowin, Efinix, Sigasi…) · rule-based category follows
marketing wording (Innovus+ → synthesis) · stale commercial release data · flaky sources (403, TLS) are logged.

## Demo (rehearsed order)
```bash
igny status
igny run script ./scripts/check_environment.py
igny run script ./scripts/pipeline.py          # offline rebuild, ~10 s
igny run script ./tests/test_pipeline.py
```
Open `outputs/tools_by_category.png`, `tools_by_region.png`, then notebook §6 (trace `kicad`), then
`data/processed/provenance.csv`. **Don't** run `--collect` live; show `data/raw/collection_log_2026-10-15.jsonl`.

## If you get stuck
"Good question. What I can say from the data is… and the way I'd verify the rest is…". Then point to a file.
Be honest about how the project was built (including AI assistance); show you understand every decision.
