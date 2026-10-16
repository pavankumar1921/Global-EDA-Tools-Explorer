"""Collector 1 - published lists of EDA software (Wikipedia list/comparison pages).

Source type: published_list. Only /wiki/ article pages are fetched (robots.txt allows them;
Wikipedia's API and the Wikidata SPARQL endpoint are disallowed for crawlers, so they are not used).

Per table row we record what the page states: name, developer, platform, licence, latest release,
languages/formats. Category comes from the table's own section heading via the documented keyword
rules in common.CATEGORY_RULES (e.g. a row in "Comparison of proprietary software for PCB design" is
pcb-design). Licence model comes from the licence cell, or from the section heading when the page
groups tools as "proprietary" / "free and open-source".
"""
import re
from urllib.parse import quote

from common import (categorize, clean_text, detect_languages, empty_raw_record, ensure_dirs, fetch_page,
                    join_multi, license_model_from, norm_date, norm_license, norm_platforms, norm_year,
                    raw_path, today, write_json)
from htmlparse import cell_flag, links_of, parse_tables, text_of, wiki_article

PAGES = [
    "https://en.wikipedia.org/wiki/Comparison_of_EDA_software",
    "https://en.wikipedia.org/wiki/List_of_HDL_simulators",
    "https://en.wikipedia.org/wiki/List_of_free_electronics_circuit_simulators",
]


def col(header, *needles):
    """Index of the first header containing any needle (case-insensitive), else None."""
    for i, h in enumerate(header):
        hl = h.lower().replace(" ", "")
        if any(n.replace(" ", "") in hl for n in needles):
            return i
    return None


def tool_name_and_link(cell_html):
    """Tool name = first link's text if the cell starts with it, else the cell text. Drops '(former X)'."""
    txt = text_of(cell_html)
    links = [(h, t) for h, t in links_of(cell_html) if t]
    name = txt
    if links and (txt.startswith(links[0][1]) or txt.startswith("[")):
        name = links[0][1]
    name = re.split(r"\s+by\s+|\s+\(", name)[0]
    name = clean_text(name.strip(" []*"))
    article = wiki_article(links[0][0]) if links and name and links[0][1].startswith(name[:4]) else ""
    other = links[0][0] if links and not article and not links[0][0].startswith("https://en.wikipedia") else ""
    if "wikipedia.org" in other or "wikidata.org" in other:
        other = ""
    return name, article, other


def developer_of(cell_html, name_cell_html):
    """Developer text and its Wikipedia link (if any)."""
    if cell_html is None:  # 'Application and developer' column: "<tool> by <developer>"
        m = re.search(r"\bby\s+(.+)$", text_of(name_cell_html))
        if not m:
            return "", ""
        dev = clean_text(m.group(1))
        links = [wiki_article(h) for h, t in links_of(name_cell_html)[1:] if wiki_article(h) and t and t in dev]
        return dev, (links[0] if links else "")
    txt = text_of(cell_html)
    if txt.lower() in ("n/a", "-", "?"):
        return "", ""
    links = [wiki_article(h) for h, t in links_of(cell_html) if wiki_article(h)]
    return txt, (links[0] if links else "")


def main():
    ensure_dirs()
    records = []
    for page in PAGES:
        status, body = fetch_page(page, "published_lists")
        if status != 200:
            continue
        page_title = page.rsplit("/", 1)[-1].replace("_", " ")
        merged = {}  # (table index, name) -> record; comparison tables repeat a tool once per platform
        for ti, t in enumerate(parse_tables(body)):
            h = t["header"]
            c_name = col(h, "application", "simulator name", "name", "software")
            if c_name is None:
                continue  # e.g. the 'Key' legend table
            c_dev = col(h, "developer", "author/company", "business or developer")
            c_plat = col(h, "platform", "architecture", "operating system")
            c_lic = col(h, "license")
            c_ver = col(h, "latest release / version")
            c_date = col(h, "latest release / date")
            c_year = col(h, "latest release year")
            c_lang = [i for i, x in enumerate(h) if re.search(r"language|imports|exports|formats", x, re.I)
                      and "interface language" not in x.lower()]
            c_desc = col(h, "description", "comment", "notes")
            flags = {k: col(h, k) for k in ("schematic", "simulation", "pcb editing", "analog", "digital",
                                             "source code")}
            context = "%s %s %s" % (page_title, t["section"], t["subsection"])
            if "List by developer" in t["section"]:
                # titled 'List of electrical engineering software': mixes EDA with general CAD (AutoCAD, FreeCAD)
                # and power-grid tools, so it is out of scope for an EDA dataset
                continue
            # the most specific heading that names a category wins (the table's own heading, then its section,
            # then the page title); categories named by the broader headings become additional ones
            table_cats = (categorize(t["subsection"]) or categorize(t["section"]) or categorize(page_title))
            table_cats += [c for c in categorize(t["subsection"], t["section"], page_title) if c not in table_cats]
            heading = next((x for x in (t["subsection"], t["section"]) if x and x != "Contents"), "")
            anchor = ("#" + quote(heading.replace(" ", "_"), safe="/()_-")) if heading else ""
            for row in t["rows"]:
                if c_name >= len(row):
                    continue
                name, article, other_link = tool_name_and_link(row[c_name])
                if not name or len(name) > 80:
                    continue
                get = lambda i: row[i] if i is not None and i < len(row) else ""
                dev, dev_link = developer_of(get(c_dev) if c_dev not in (None, c_name) else None, row[c_name])
                plat_text = text_of(get(c_plat))
                lic_text = text_of(get(c_lic))
                if c_lic is None and c_plat is not None and "license" in h[c_plat].lower():
                    # 'Operating System/License' column: platform words go to platforms, the rest is licence
                    lic_text = "; ".join(x for x in re.split(r"[,;/]", plat_text)
                                         if x.strip() and not norm_platforms(x))
                lic = norm_license(lic_text)
                hint = ""
                if re.search(r"proprietary", context, re.I):
                    hint = "proprietary"
                elif re.search(r"free and open-source|open source software", context, re.I):
                    hint = "open-source"
                src_flag = cell_flag(get(flags["source code"])) if flags["source code"] is not None else ""
                if src_flag == "yes":
                    hint = "open-source"
                elif src_flag == "no" and "free" in page_title.lower():
                    hint = "freeware"  # the page lists free-of-charge simulators; closed source -> freeware
                model = license_model_from(lic_text, "" if lic_text and license_model_from(lic_text) else hint)
                cats = list(table_cats)  # per-row copy: a row-level override must not leak into later rows
                analog_f = cell_flag(get(flags["analog"])) if flags["analog"] is not None else ""
                digital_f = cell_flag(get(flags["digital"])) if flags["digital"] is not None else ""
                if analog_f == "no" and digital_f == "yes":  # the row's own flags beat the page grouping
                    cats = ["simulation"] + [c for c in cats if c != "simulation"]
                extra = list(cats[1:])
                if cell_flag(get(flags["pcb editing"])) == "yes":
                    extra.append("pcb-design")
                if cell_flag(get(flags["simulation"])) == "yes" or cell_flag(get(flags["analog"])) == "yes":
                    extra.append("analog-mixed-signal")
                if cell_flag(get(flags["digital"])) == "yes":
                    extra.append("simulation")
                lang_text = " ".join(text_of(get(i)) for i in c_lang)
                rec = empty_raw_record(
                    tool_name=name, vendor_maintainer=dev, category=cats[0] if cats else "",
                    additional_categories=join_multi(x for x in extra if x != (cats[0] if cats else "")),
                    license_model=model, license=lic, wikipedia_url=article,
                    website_url=other_link if other_link and "github.com" not in other_link else "",
                    repository_url=other_link if "github.com" in other_link else "",
                    latest_version=text_of(get(c_ver))[:40],
                    latest_release_date=norm_date(text_of(get(c_date))),
                    latest_release_year=norm_year(text_of(get(c_year)) or text_of(get(c_date))),
                    supported_platforms=norm_platforms(plat_text),
                    languages_formats=detect_languages(lang_text, text_of(get(c_desc)) if c_lang else ""),
                    source_url=page + anchor, source_type="published_list",
                    date_collected=today(), fetch_status=status)
                rec["vendor_wikipedia_url"] = dev_link
                key = (ti, name.lower())
                if key in merged:  # same tool on another platform row: union the multi-valued fields
                    m = merged[key]
                    for f in ("supported_platforms", "languages_formats", "additional_categories"):
                        m[f] = join_multi(m[f].split("; ") + rec[f].split("; "))
                else:
                    merged[key] = rec
        records.extend(merged.values())
        print("published list %s: %d rows" % (page_title, len(merged)))
    out = raw_path("published_list")
    write_json(out, records)
    print("published lists: %d records -> %s" % (len(records), out))


if __name__ == "__main__":
    main()
