"""Collector 6 - official documentation pages (platform and language/format evidence).

Source type: documentation. Input: 'docs_url' entries in data/metadata/seed_tools.json.

Keyword matching on a documentation landing page is WEAK evidence: it finds mentions, not guarantees of
support, and absence never implies non-support. This is stated in the report. Only platform words that
appear as installation targets ('install ... on Linux', 'Windows binaries', ...) are counted, to avoid
counting navigation text.
"""
import re

from common import (UNAMBIGUOUS_FORMATS, categorize, detect_languages, empty_raw_record, ensure_dirs, fetch_page,
                    join_multi, load_seed, raw_path, today, write_json)
from htmlparse import page_meta, text_of

PLATFORM_EVIDENCE = {
    "Linux": r"(install\w*|build\w*|packages?|binar\w+|runs?|support\w*)\W+(\w+\W+){0,6}?linux|linux\W+(packages?|binar\w+|install\w*)",
    "Windows": r"(install\w*|build\w*|packages?|binar\w+|runs?|support\w*)\W+(\w+\W+){0,6}?windows|windows\W+(packages?|binar\w+|install\w*)",
    "macOS": r"(install\w*|build\w*|packages?|binar\w+|runs?|support\w*)\W+(\w+\W+){0,6}?(macos|mac os|os x)|(macos|os x)\W+(packages?|binar\w+|install\w*)",
}


def main():
    ensure_dirs()
    records = []
    for t in load_seed():
        url = t.get("docs_url")
        if not url:
            continue
        status, body = fetch_page(url, "documentation")
        if status != 200:
            continue
        text = text_of(body).lower()
        plats = [p for p, pat in PLATFORM_EVIDENCE.items() if re.search(pat, text)]
        langs = detect_languages(text, only=UNAMBIGUOUS_FORMATS)
        meta = page_meta(body)
        cats = categorize(meta["description"], meta["title"], by_position=True)  # the docs page's own headline
        if not plats and not langs and not cats:
            continue
        records.append(empty_raw_record(
            tool_name=t["tool_name"], supported_platforms=join_multi(plats), languages_formats=langs,
            category=cats[0] if cats else "", additional_categories=join_multi(cats[1:]),
            repository_url=("https://github.com/" + t["repository"]) if t.get("repository") else "",
            source_url=url, source_type="documentation", date_collected=today(), fetch_status=status))
    out = raw_path("documentation")
    write_json(out, records)
    print("documentation: %d records -> %s" % (len(records), out))


if __name__ == "__main__":
    main()
