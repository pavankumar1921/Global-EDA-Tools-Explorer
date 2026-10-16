# Requirements notes (Crucible dependency check)

Checked on **2026-10-15** with `igny catalog --view full` (catalog of 65 tools); `igny --version` prints `dev`
(foundation package 3.12.10.0). Every dependency was installed with `igny tool install`; nothing with
system `pip`, a system package manager, or a manual PATH edit.

| Library | Needed for | In Crucible catalog? | Installed via | Decision |
|---|---|---|---|---|
| Python 3.12.10 + standard library | everything: HTTP (`urllib`), robots.txt (`urllib.robotparser`), HTML parsing (`html.parser`), CSV/JSON | yes - Crucible's own interpreter runs every `igny run script` | Crucible foundation package | used |
| numpy 2.5.4 | numeric arrays and cross-tabs in the analysis and notebook | yes | `igny tool install numpy` | used |
| matplotlib 3.11.2 | every plot | yes | `igny tool install matplotlib` | used |
| jupyterlab 4.6.4 | the analysis notebook (`igny run jupyter lab` / `nbconvert --execute`) | yes | `igny tool install jupyterlab` | used |
| pandas | dataframes, merges, group-bys | **no** | - | **gap**: replaced by `csv` + `collections.Counter` + numpy |
| requests | HTTP client | not as a tool (only bundled inside jupyterlab) | - | **gap**: not relied on; `urllib.request` used |
| beautifulsoup4 | HTML parsing | not as a tool (only bundled inside jupyterlab) | - | **gap**: not relied on; `scripts/htmlparse.py` on `html.parser` |
| scipy, seaborn, scikit-learn | statistics / styling / ML | **no** | - | **gap**: not needed for counting-based analysis |

Why not use requests/bs4 although `import` works: they are not declared tools, so they are not in
`crucible.lock`; a future jupyterlab version could drop them and silently break the project.

Isolation finding: Crucible's Python does **not** disable the user site-packages
(`%APPDATA%\Python\Python312\site-packages`). On this machine `import scipy` succeeded inside
`igny run script` from that folder. The project defends against this: `pipeline.py` starts every step
with `python -s` and `PYTHONNOUSERSITE=1`, and `check_environment.py` fails the run if numpy or
matplotlib resolve outside `Crucible\tools`.
