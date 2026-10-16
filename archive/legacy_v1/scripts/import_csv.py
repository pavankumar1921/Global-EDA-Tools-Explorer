"""Import a collected CSV (starter-dataset schema) into the pipeline's raw JSON format.

Usage: python scripts/import_csv.py <file.csv> [--date YYYY-MM-DD]

Each CSV row becomes up to two raw records so provenance stays per source:
  * public_repository record: repository_url as source_url (license, release tag/date, category, maintainer)
  * documentation record: documentation_url as source_url (platforms, design languages)
Conservative mapping rules (nothing is guessed; anything unclear stays empty):
  - category: keyword rules on the free-text category; unmatched -> empty (logged)
  - license: only a plain recognised license name is kept (mapped to SPDX); long notes such as
    "component-dependent ..." or "verify ..." are NOT treated as a license
  - license_model: 'open-source' only if the license is a recognised open-source licence, or the
    description itself begins with "Open-source"
  - platforms: Linux distro names -> Linux; macOS -> macOS; Windows only when stated as native
    (a "Windows via Docker/WSL" statement is NOT counted as Windows support)
  - languages_formats: only Verilog / SystemVerilog / VHDL / SPICE mentions, not scripting interfaces (Tcl, Python)
"""
import argparse
import csv
import re
import shutil

from common import (RAW, clean_text, empty_raw_record, ensure_dirs, join_multi, log_event,
                    snapshot_date, write_json)

CATEGORY_RULES = [
    (r"synthesis", "front-end-synthesis"),
    (r"layout", "layout-physical-verification"),
    (r"circuit simulation|mixed-signal|mixed signal|spice", "analog-mixed-signal"),
    (r"verif|formal", "verification-formal"),
    (r"simulat", "simulation"),
    (r"pcb|schematic", "pcb-design"),
    (r"physical design|place|route|gdsii|implementation flow", "place-and-route"),
]
SPDX = {"bsd 3-clause": "BSD-3-Clause", "bsd-3-clause": "BSD-3-Clause", "isc": "ISC", "mit": "MIT",
        "apache-2.0": "Apache-2.0", "apache 2.0": "Apache-2.0", "gpl-2.0": "GPL-2.0-only",
        "gpl-3.0": "GPL-3.0-only", "lgpl-3.0": "LGPL-3.0-only", "mpl-2.0": "MPL-2.0"}
LANG_PATTERNS = [("SystemVerilog", r"\bsystemverilog\b"), ("Verilog", r"\bverilog\b"),
                 ("VHDL", r"\bvhdl\b"), ("SPICE", r"\bspice\b")]


def map_category(text):
    t = text.lower()
    for pat, cat in CATEGORY_RULES:
        if re.search(pat, t):
            return cat
    return ""


def map_license(text):
    return SPDX.get(clean_text(text).lower(), "")


def map_platforms(text):
    t = text.lower()
    out = []
    if re.search(r"debian|ubuntu|rhel|rocky|centos|fedora|linux", t):
        out.append("Linux")
    if "macos" in t:
        out.append("macOS")
    if re.search(r"\bwindows\b", t) and not re.search(r"docker|wsl", t):
        out.append("Windows")
    return join_multi(out)


def map_languages(text):
    t = text.lower()
    return join_multi(name for name, pat in LANG_PATTERNS if re.search(pat, t))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--date", default=snapshot_date())
    a = ap.parse_args()
    ensure_dirs()
    (RAW / "imported").mkdir(exist_ok=True)
    shutil.copy(a.csv_path, RAW / "imported" / ("%s_%s" % (a.date, a.csv_path.replace("\\", "/").split("/")[-1])))

    repo_recs, doc_recs = [], []
    with open(a.csv_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            name = clean_text(row.get("tool_name"))
            if not name:
                continue
            cat = map_category(row.get("tool_category", ""))
            if not cat:
                log_event("import_unmapped_category", tool=name, value=row.get("tool_category"))
            lic = map_license(row.get("license", ""))
            desc = clean_text(row.get("description"))
            model = "open-source" if lic or desc.lower().startswith("open-source") else ""
            repo_url = clean_text(row.get("repository_url"))
            common = dict(tool_name=name, vendor_maintainer=clean_text(row.get("provider_or_maintainer")),
                          date_collected=a.date, fetch_status="")  # not fetched by this pipeline
            repo_recs.append(empty_raw_record(
                **common, category=cat, license_model=model, license=lic,
                website_url=clean_text(row.get("official_product_url")), repository_url=repo_url,
                latest_version=clean_text(row.get("latest_release_tag")),
                latest_release_date=clean_text(row.get("latest_release_date")),
                source_url=repo_url or clean_text(row.get("official_product_url")),
                source_type="public_repository"))
            docs = clean_text(row.get("documentation_url"))
            plats = map_platforms(row.get("platforms", ""))
            langs = map_languages(" ".join([row.get("supported_languages_or_interfaces", ""),
                                            row.get("formats_or_design_flow", "")]))
            if docs and (plats or langs):
                doc_recs.append(empty_raw_record(
                    **common, supported_platforms=plats, languages_formats=langs, repository_url=repo_url,
                    website_url=clean_text(row.get("official_product_url")),
                    source_url=docs, source_type="documentation"))
    write_json(RAW / ("public_repository_%s.json" % a.date), repo_recs)
    write_json(RAW / ("documentation_%s.json" % a.date), doc_recs)
    print("imported %d repository-source and %d documentation-source records for %s"
          % (len(repo_recs), len(doc_recs), a.date))


if __name__ == "__main__":
    main()
