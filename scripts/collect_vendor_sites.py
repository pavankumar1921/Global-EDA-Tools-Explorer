"""Collector 4 - official vendor product pages (mainly commercial IC-design tools).

Source type: vendor_site. Input: 'website_url' entries in data/metadata/seed_tools.json, which is a
DISCOVERY list (tool name + URL to check) and holds no field values.

Every value comes from the fetched page (robots.txt permitting, >= 1.5 s between requests):
  vendor_maintainer  <- og:site_name, else the last '|' / ' - ' / '_' part of <title> that is not the product name
  category           <- keyword rules (common.CATEGORY_RULES) on <title> + meta description; if none match,
                        on the page's own definition sentence of the product ('<product> is a ...')
  languages_formats  <- format/language names mentioned in <title> + meta description
  license_model      <- 'commercial' only when the page shows sales evidence (contact sales, request a
                        demo/quote, pricing, buy) and states no open-source licence
A record is kept only if the page returned HTTP 200 AND the tool name appears on the page.
"""
import re

from common import (categorize, detect_languages, empty_raw_record, ensure_dirs, fetch_page, join_multi,
                    license_model_from, load_seed, log_event, name_key, raw_path, today, write_json)
from htmlparse import page_meta, text_of

SALES = re.compile(r"contact sales|talk to (an? )?(expert|sales)|request (a )?(demo|quote|evaluation|pricing)|free trial|"
                   r"get (a )?quote|buy now|pricing|how to buy|request information", re.I)


def vendor_from(meta, tool_name):
    if len(meta["site_name"]) > 2 and meta["site_name"].lower() not in ("english", "home", "en", "us"):
        return meta["site_name"]
    # title parts are split on ' | ', ' - ', ' – ' and '_' ('Product Portfolio_Empyrean Technology Co., Ltd');
    # a part that names the product itself is not the vendor ('PRIMARIUS - NanoSpice' -> 'PRIMARIUS')
    parts = [p.strip() for p in re.split(r"\s+[|–—-]\s+|_", meta["title"]) if p.strip()]
    keys = {name_key(tool_name), name_key(tool_name.split()[-1])}
    brands = [p for p in parts if not any(k in name_key(p) for k in keys)]
    return brands[-1] if len(parts) > 1 and brands and len(brands[-1]) <= 40 else ""


def definition_sentence(text, tool_name):
    """The page's own definition of the product ('NanoSpice is a ... parallel SPICE simulator'), or ''."""
    names = "|".join(re.escape(n) for n in {tool_name, tool_name.split()[-1]})
    m = re.search(r"\b(?:%s)\W{0,2}\s+(?:is|are)\s+[^.;]{10,250}" % names, text, re.I)
    return m.group(0) if m else ""


def main():
    ensure_dirs()
    records, tried = [], 0
    for t in load_seed():
        url = t.get("website_url", "")
        if not url:
            continue
        tried += 1
        status, body = fetch_page(url, "vendor_sites")
        if status != 200:
            continue
        meta = page_meta(body)
        text = text_of(body)
        # the product name (or its distinctive last word, e.g. 'Genus' in 'Cadence Genus') must be on the page
        page_key = name_key(text)
        if not any(k and k in page_key for k in (name_key(t["tool_name"]), name_key(t["tool_name"].split()[-1]))):
            log_event("name_not_on_page", collector="vendor_sites", url=url, tool=t["tool_name"])
            continue
        evidence = "%s %s" % (meta["title"], meta["description"])
        languages = detect_languages(evidence)
        # the vendor's own summary sentence first, then the title; earliest keyword = primary category
        cats = categorize(meta["description"], meta["title"], by_position=True)
        if not cats:
            # no keyword in the title or summary: the page's own definition sentence of the product
            definition = definition_sentence(text, t["tool_name"])
            cats = categorize(definition, by_position=True)
            evidence = "%s %s" % (evidence, definition)
        model = license_model_from(meta["description"])
        if not model and SALES.search(text):
            model = "commercial"
        records.append(empty_raw_record(
            tool_name=t["tool_name"], vendor_maintainer=vendor_from(meta, t["tool_name"]),
            category=cats[0] if cats else "", additional_categories=join_multi(cats[1:]),
            license_model=model, website_url=url, languages_formats=languages,
            source_url=url, source_type="vendor_site", date_collected=today(), fetch_status=status))
        records[-1]["_evidence"] = evidence[:300]
    out = raw_path("vendor_site")
    write_json(out, records)
    print("vendor sites: %d of %d product pages kept -> %s" % (len(records), tried, out))


if __name__ == "__main__":
    main()
