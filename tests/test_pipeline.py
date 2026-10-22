"""Offline end-to-end test of clean -> dedup -> validate -> analysis on a synthetic fixture.

Run through Crucible:  igny run script ./tests/test_pipeline.py
The fixture uses made-up tools ("Example ...") and a temporary project root, so it never touches real
data and needs no network. It checks: unverified sources are excluded, records merge across sources by
repository / name, an empty-vendor record cannot bridge two different vendors, conflicting vendors go to
review, country comes from the vendor_origin record, the release triple stays together, provenance is kept.
"""
import csv
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
FIX = HERE / "fixtures"


def run(script, env):
    r = subprocess.run([sys.executable, "-s", str(SCRIPTS / script)], env=env, capture_output=True, text=True)
    assert r.returncode == 0, "%s failed:\n%s\n%s" % (script, r.stdout, r.stderr)
    return r.stdout


def unit_checks():
    sys.path.insert(0, str(SCRIPTS))
    from common import (CATEGORIES, categorize, country_from_text, norm_category, norm_date, norm_platforms,
                        license_model_from)
    for c in CATEGORIES:
        assert norm_category(c) == c, "vocabulary term not accepted: " + c
    assert country_from_text("Sunnyvale, California, U.S.") == "United States"
    assert country_from_text("Yokohama, Japan") == "Japan"
    assert country_from_text("Wilsonville, Oregon") == "United States"
    assert norm_date("10.0.6 / 29 August 2025; 46 days ago") == "2025-08-29"
    assert norm_platforms("Linux, macOS, Microsoft Windows") == "Linux; Windows; macOS"
    assert license_model_from("GPL-3.0-or-later") == "open-source"
    assert license_model_from("Proprietary") == "commercial"
    assert categorize("PrimeTime Static Timing Analysis | Synopsys")[0] == "timing-signoff"
    assert categorize("Comparison of proprietary software for PCB design")[0] == "pcb-design"
    assert categorize("Design Compiler offers best-in-class RTL synthesis ... high test coverage",
                      by_position=True) == ["synthesis", "verification"]
    from collect_vendor_sites import definition_sentence, vendor_from
    assert vendor_from({"site_name": "", "title": "PRIMARIUS - NanoSpice"}, "Primarius NanoSpice") == "PRIMARIUS"
    assert vendor_from({"site_name": "", "title": "Empyrean Aether™ – Layout Design_Product Portfolio_Empyrean "
                        "Technology Co., Ltd"}, "Empyrean Aether") == "Empyrean Technology Co., Ltd"
    assert vendor_from({"site_name": "", "title": "PrimeTime Static Timing Analysis | Synopsys"},
                       "Synopsys PrimeTime") == "Synopsys"
    assert categorize(definition_sentence("NanoSpice X; NanoSpice is a new generation of parallel SPICE simulator. "
                                          "Designed for", "Primarius NanoSpice"))[0] == "analog-mixed-signal"
    from collect_public_repositories import readme_summary
    assert readme_summary("# Parallax Static Timing Analyzer\n\n[![b](x)](y)\nOpenSTA is a gate level static timing "
                          "verifier.\nAs a stand-alone\n\n* Verilog netlist") == \
        "Parallax Static Timing Analyzer. OpenSTA is a gate level static timing verifier. As a stand-alone"
    from collect_curated_lists import parse_list
    md = ("## Circuit Compilers\n* [abc](https://github.com/berkeley-abc/abc)\n  * System for sequential logic synthesis\n"
          "## CPUs\n* [somecore](https://github.com/x/somecore)\n  * A RISC-V core\n"
          "### Simulation\n\n[ghdl/ghdl](https://github.com/ghdl/ghdl) - VHDL Simulator\n")
    assert parse_list(md, ["Circuit Compilers", "Simulation"]) == [
        ["abc", "https://github.com/berkeley-abc/abc", "System for sequential logic synthesis", "Circuit Compilers"],
        ["ghdl/ghdl", "https://github.com/ghdl/ghdl", "VHDL Simulator", "Simulation"]]  # CPUs section skipped
    from collect_wikipedia_articles import category_members
    page = ('<div id="mw-pages"><a href="/wiki/Comparison_of_EDA_software">Comparison of EDA software</a>'
            '<a href="/wiki/KiCad">KiCad</a><a href="/wiki/Magic_(software)">Magic (software)</a>'
            '<div class="printfooter">')
    assert category_members(page) == [("KiCad", "https://en.wikipedia.org/wiki/KiCad"),
                                      ("Magic", "https://en.wikipedia.org/wiki/Magic_(software)")]
    from collect_github_search import is_tool
    assert is_tool("VHDL compiler and simulator")
    assert is_tool("A High-performance Timing Analysis Tool for VLSI Systems")
    assert not is_tool("An open source library for image processing on FPGA.")
    assert not is_tool("Automated exploratory data analysis tool for pandas")
    assert not is_tool("RISC-V core written in Verilog")
    assert categorize("Hardware Description Language embedded in Python")[0] == "hdl-design-entry"
    from deduplicate_data import vendors_compatible
    assert vendors_compatible("Cadence", "Cadence Design Systems")
    assert vendors_compatible("Autodesk (previously CadSoft Computer)", "Autodesk / CadSoft Computer (discontinued)")
    assert not vendors_compatible("National Instruments", "National Semiconductor")


def main():
    unit_checks()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        raw = root / "data" / "raw"
        raw.mkdir(parents=True)
        (raw / "published_list_2026-01-01.json").write_text((FIX / "raw_sample.json").read_text())
        (raw / "public_repository_2026-01-01.json").write_text((FIX / "raw_repo_sample.json").read_text())
        (raw / "vendor_origin_2026-01-01.json").write_text((FIX / "raw_origin_sample.json").read_text())
        env = dict(os.environ, EDA_PROJECT_ROOT=str(root), EDA_SNAPSHOT_DATE="2026-01-01", PYTHONNOUSERSITE="1")
        run("clean_data.py", env)
        run("deduplicate_data.py", env)
        run("validate_dataset.py", env)
        run("run_analysis.py", env)

        proc = root / "data" / "processed"
        rows = list(csv.DictReader(open(proc / "eda_tools_clean.csv", encoding="utf-8")))
        ids = sorted(r["tool_id"] for r in rows)
        assert ids == ["example-forge", "example-forge-2", "example-sim"], ids  # 404 'Sim Pro' excluded
        sim = next(r for r in rows if r["tool_id"] == "example-sim")
        assert sim["source_count"] == "2", sim  # list row + repository merged
        assert sim["license"] == "MIT" and sim["license_model"] == "open-source", sim
        assert (sim["latest_version"], sim["latest_release_date"]) == ("v1.2.0", "2025-03-02"), sim
        assert sim["supported_platforms"] == "Linux; Windows; macOS", sim
        assert sim["additional_categories"] == "verification", sim
        forges = [r for r in rows if r["tool_id"].startswith("example-forge")]
        assert sorted(r["country_region"] for r in forges) == ["", "United States"], forges
        us = next(r for r in forges if r["country_region"])
        assert us["vendor_maintainer"] == "Example Vendor A Inc." and us["region"] == "North America", us
        review = json.load(open(proc / "review_queue.json"))
        assert any(x["type"] == "same_name_different_vendor" for x in review), review
        excluded = json.load(open(proc / "excluded_records.json"))
        assert [e["tool"] for e in excluded] == ["Example Sim Pro"], excluded
        prov = list(csv.DictReader(open(proc / "provenance.csv", encoding="utf-8")))
        assert sum(1 for p in prov if p["tool_id"] == "example-sim") == 2
        assert (root / "outputs" / "findings.md").exists() and (root / "outputs" / "tools_by_category.png").exists()
    print("PASS: pipeline fixture test")


if __name__ == "__main__":
    main()
