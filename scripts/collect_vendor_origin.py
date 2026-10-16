"""Collector 3 - country of origin of each vendor, from the vendor's own Wikipedia article.

Source type: vendor_origin. For every tool whose developer links to a Wikipedia article (found by the
published-list and article collectors, or given as 'vendor_wikipedia' in the seed), fetch that article
once and read the organisation infobox ('Headquarters', else 'Country' / 'Location'). The country is
parsed from the text by common.country_from_text (e.g. 'Sunnyvale, California, U.S.' -> United States).
Links that are people or products (no organisation infobox) give no country.
"""
from collections import defaultdict

from common import (country_from_text, empty_raw_record, ensure_dirs, fetch_page, load_seed, log_event,
                    raw_path, read_json, today, wiki_key, write_json)
from htmlparse import parse_infobox, wiki_article


def tool_vendor_links():
    """{company_article_url: [tool_name, ...]} from this snapshot's raw files and the seed."""
    links = defaultdict(list)
    for src in ("published_list", "wikipedia_article"):
        for rec in read_json(raw_path(src), []) or []:
            url = wiki_article(rec.get("vendor_wikipedia_url", ""))
            if url and wiki_key(url) != wiki_key(rec.get("wikipedia_url", "")):
                links[url].append(rec["tool_name"])
    for t in load_seed():
        url = wiki_article(t.get("vendor_wikipedia", ""))
        if url:
            links[url].append(t["tool_name"])
    return links


def main():
    ensure_dirs()
    records, companies = [], 0
    for url, tools in sorted(tool_vendor_links().items()):
        status, body = fetch_page(url, "vendor_origin")
        if status != 200:
            continue
        box = parse_infobox(body)
        hq = next((box[k][0] for k in box if k.startswith("headquarters")), "") or \
            next((box[k][0] for k in ("country", "location", "country of origin") if k in box), "")
        country = country_from_text(hq)
        if not country:
            log_event("no_country", collector="vendor_origin", url=url, headquarters=hq[:120])
            continue
        companies += 1
        # vendor_maintainer is left empty on purpose: the tool's own sources name the vendor; this
        # record only contributes country_region, and an empty vendor never blocks the merge
        for tool in sorted(set(tools)):
            rec = empty_raw_record(tool_name=tool, country_region=country,
                                   source_url=url, source_type="vendor_origin", date_collected=today(),
                                   fetch_status=status)
            rec["vendor_wikipedia_url"] = url
            records.append(rec)
    out = raw_path("vendor_origin")
    write_json(out, records)
    print("vendor origin: %d companies with a country -> %d tool records -> %s" % (companies, len(records), out))


if __name__ == "__main__":
    main()
