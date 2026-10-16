"""Collector 4 - official vendor product pages (mainly commercial IC-design tools).

Source type: vendor_site. Input: 'website_url' entries in data/metadata/seed_tools.json, which is a
DISCOVERY list (tool name + URL to check) and holds no field values.

Every value comes from the fetched page (robots.txt permitting, >= 1.5 s between requests):
  vendor_maintainer  <- og:site_name, else the brand after the last '|' or ' - ' in <title>
  category           <- keyword rules (common.CATEGORY_RULES) on <title> + meta description
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


def vendor_from(meta):
    if len(meta["site_name"]) > 2 and meta["site_name"].lower() not in ("english", "home", "en", "us"):
        return meta["site_name"]
    parts = re.split(r"\s+[|–—-]\s+", meta["title"])
    return parts[-1].strip() if len(parts) > 1 and len(parts[-1]) <= 40 else ""


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
        # the vendor's own summary sentence first, then the title; earliest keyword = primary category
        cats = categorize(meta["description"], meta["title"], by_position=True)
        model = license_model_from(meta["description"])
        if not model and SALES.search(text):
            model = "commercial"
        records.append(empty_raw_record(
            tool_name=t["tool_name"], vendor_maintainer=vendor_from(meta),
            category=cats[0] if cats else "", additional_categories=join_multi(cats[1:]),
            license_model=model, website_url=url, languages_formats=detect_languages(evidence),
            source_url=url, source_type="vendor_site", date_collected=today(), fetch_status=status))
        records[-1]["_evidence"] = evidence[:300]
    out = raw_path("vendor_site")
    write_json(out, records)
    print("vendor sites: %d of %d product pages kept -> %s" % (len(records), tried, out))


if __name__ == "__main__":
    main()
