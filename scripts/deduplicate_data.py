"""Tool-level deduplication: many per-source records -> one row per tool.

Automatic merge rules (union-find; a group = one canonical tool):
  1. identical GitHub repository (owner/repo), OR
  2. identical English Wikipedia article, OR
  3. identical normalized name (vendor prefix such as 'Synopsys ' ignored) AND compatible vendor
     (equal after normalization, one contains the other, or at least one side empty).
A same-name pair whose vendors differ merges only if a human confirmed it in
data/metadata/review_decisions.json (each decision has a reason). Otherwise it is
sent to manual review instead of merged:
  - same normalized name but two different vendors
  - different tools sharing one website path
  - conflicting licence model or first-release year inside a merged group
Field values are chosen by per-field source priority (FIELD_PRIORITY). The release triple
(latest_version, latest_release_date, latest_release_year) is taken together from ONE record: the one
reporting the most recent release, so a version is never paired with another source's date.
Outputs: eda_tools_clean.csv, provenance.csv, review_queue.json, dedup_stats.json in data/processed/.
"""
import csv
import re
from collections import defaultdict
from urllib.parse import urlparse

from common import (CATEGORIES, FINAL_FIELDS, META, PROCESSED, clean_text, ensure_dirs, github_repo_key, join_multi,
                    name_key, read_json, region_of, slug, split_multi, wiki_key, write_json)

SOURCE_RANK = ["published_list", "wikipedia_article", "vendor_site", "public_repository", "documentation",
               "vendor_origin"]
FIELD_PRIORITY = {
    "tool_name": ["wikipedia_article", "published_list", "vendor_site", "public_repository", "documentation"],
    "vendor_maintainer": ["vendor_site", "published_list", "wikipedia_article", "public_repository"],
    "country_region": ["vendor_origin"],
    "category": ["published_list", "vendor_site", "wikipedia_article", "public_repository", "documentation"],
    "license_model": ["wikipedia_article", "published_list", "public_repository", "vendor_site"],
    "license": ["public_repository", "wikipedia_article", "published_list"],
    "website_url": ["vendor_site", "wikipedia_article", "published_list", "public_repository"],
    "repository_url": ["public_repository", "wikipedia_article", "published_list", "documentation"],
    "wikipedia_url": ["wikipedia_article", "published_list"],
    "first_release_year": ["wikipedia_article"],
}
RELEASE_PRIORITY = ["public_repository", "wikipedia_article", "published_list"]
VENDOR_PREFIXES = ("synopsys", "cadence", "siemens", "mentor", "keysight", "zuken", "lattice", "intel", "amd",
                   "xilinx", "efinix", "gowin", "empyrean", "primarius", "silvaco", "defacto", "ansys", "altium")
CONFLICT_FIELDS = ("license_model", "first_release_year")


def merge_key(name):
    k = name_key(name)
    for p in VENDOR_PREFIXES:
        if k.startswith(p) and len(k) > len(p) + 2:
            return k[len(p):]
    return k


def vendor_key(v):
    v = re.sub(r"\b(inc|ltd|llc|gmbh|corp|corporation|co|limited|technologies|technology|software|systems|"
               r"design|eda|ag|sa|the)\b\.?", " ", clean_text(v).lower())
    return name_key(v)


def vendor_parts(v):
    """Vendor name parts: parenthetical notes dropped, split on '/', legal suffixes removed."""
    return [k for k in (vendor_key(p) for p in re.split(r"[/;]", re.sub(r"\(.*?\)", " ", clean_text(v)))) if k]


def load_decisions():
    """Human review decisions (data/metadata/review_decisions.json): pairs of vendor names confirmed to be the
    same maintainer for a given tool name. They only allow a merge the automatic rules held back; they never
    add a value to the dataset."""
    out = set()
    for d in (read_json(META / "review_decisions.json", {}) or {}).get("same_tool", []):
        vs = [vendor_key(v) for v in d["vendors"]]
        for a in vs:
            for b in vs:
                out.add((merge_key(d["tool_name"]), a, b))
    return out


def vendors_compatible(a, b):
    """Compatible if either is empty, or some part of one equals / contains some part of the other:
    'Cadence' ~ 'Cadence Design Systems'; 'Autodesk (previously CadSoft)' ~ 'Autodesk / CadSoft (discontinued)';
    but 'Example Vendor A' !~ 'Example Vendor B' and 'National Instruments' !~ 'National Semiconductor'."""
    pa, pb = vendor_parts(a), vendor_parts(b)
    return not pa or not pb or any(x == y or x in y or y in x for x in pa for y in pb)


def url_key(u):
    p = urlparse(clean_text(u).lower())
    path = p.path.rstrip("/")
    return p.netloc.removeprefix("www.") + path


class UF:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def pick(group, field, order):
    cands = [r for r in group if r[field] and r["source_type"] in order]
    cands.sort(key=lambda r: order.index(r["source_type"]))
    return cands[0][field] if cands else ""


def main():
    ensure_dirs()
    recs = read_json(PROCESSED / "records_normalized.json", [])
    n = len(recs)
    uf, review = UF(n), []

    by_repo, by_wiki, by_name = defaultdict(list), defaultdict(list), defaultdict(list)
    for i, r in enumerate(recs):
        if github_repo_key(r["repository_url"]):
            by_repo[github_repo_key(r["repository_url"])].append(i)
        if wiki_key(r["wikipedia_url"]):
            by_wiki[wiki_key(r["wikipedia_url"])].append(i)
        by_name[merge_key(r["tool_name"])].append(i)
    for idx_map in (by_repo, by_wiki):
        for idxs in idx_map.values():
            for j in idxs[1:]:
                uf.union(idxs[0], j)
    # vendors already present in each group: a name-merge must be compatible with ALL of them, otherwise a
    # record with an empty vendor could bridge two tools from different vendors (union is transitive)
    decisions = load_decisions()
    group_vendors = defaultdict(set)
    for i, r in enumerate(recs):
        if r["vendor_maintainer"]:
            group_vendors[uf.find(i)].add(r["vendor_maintainer"])
    for nk, idxs in by_name.items():
        for a in range(len(idxs)):
            for b in range(a + 1, len(idxs)):
                i, j = idxs[a], idxs[b]
                ri, rj = uf.find(i), uf.find(j)
                if ri == rj:
                    continue
                if all(vendors_compatible(x, y) or (nk, vendor_key(x), vendor_key(y)) in decisions
                       for x in group_vendors[ri] for y in group_vendors[rj]):
                    uf.union(i, j)
                    group_vendors[uf.find(j)] = group_vendors.pop(ri, set()) | group_vendors.pop(rj, set())
                elif recs[i]["vendor_maintainer"] and recs[j]["vendor_maintainer"]:
                    review.append({"type": "same_name_different_vendor", "name": recs[i]["tool_name"],
                                   "vendors": sorted({recs[i]["vendor_maintainer"], recs[j]["vendor_maintainer"]})})

    groups = defaultdict(list)
    for i in range(n):
        groups[uf.find(i)].append(recs[i])

    pairs, orphans = [], []
    for g in groups.values():
        if all(r["source_type"] == "vendor_origin" for r in g):
            # only the vendor's company page mentions this tool (e.g. its product page returned 403):
            # a row needs at least one tool-level source, so it is excluded
            orphans.append({"tool": g[0]["tool_name"], "source_url": g[0]["source_url"],
                            "reason": "only a vendor-origin record; no tool-level source answered"})
            continue
        g.sort(key=lambda r: SOURCE_RANK.index(r["source_type"]) if r["source_type"] in SOURCE_RANK else 99)
        row = {f: "" for f in FINAL_FIELDS}
        for f, order in FIELD_PRIORITY.items():
            row[f] = pick(g, f, order)
        row["tool_name"] = row["tool_name"] or g[0]["tool_name"]
        row["tool_id"] = slug(row["tool_name"])
        row["region"] = region_of(row["country_region"])
        # categories: primary by priority, every other category any source assigned -> additional
        all_cats = [r["category"] for r in g if r["category"]] + \
                   [c for r in g for c in split_multi(r["additional_categories"])]
        row["additional_categories"] = join_multi(c for c in all_cats if c in CATEGORIES and c != row["category"])
        # release triple from ONE record: the most recent release reported by any source
        rel = [r for r in g if (r["latest_version"] or r["latest_release_year"]) and r["source_type"] in RELEASE_PRIORITY]
        rel.sort(key=lambda r: (r["latest_release_date"] or r["latest_release_year"] or "0000",
                                -RELEASE_PRIORITY.index(r["source_type"])), reverse=True)
        if rel:
            for f in ("latest_version", "latest_release_date", "latest_release_year"):
                row[f] = rel[0][f]
        for f in ("supported_platforms", "languages_formats"):
            row[f] = join_multi(x for r in g for x in split_multi(r[f]))
        models = {r["license_model"] for r in g if r["license_model"]}
        if models == {"commercial", "freeware"}:
            # freeware IS proprietary software given away free: a 'proprietary' licence and a 'free of charge'
            # listing agree, so the more specific value wins and it is not a conflict
            row["license_model"] = "freeware"
        for f in CONFLICT_FIELDS:
            vals = sorted({r[f] for r in g if r[f]})
            if f == "license_model" and set(vals) == {"commercial", "freeware"}:
                continue
            if len(vals) > 1:
                review.append({"type": "field_conflict", "tool": row["tool_name"], "field": f, "values": vals,
                               "chosen": row[f]})
        primary = g[0]
        row["source_url"] = primary["source_url"]
        row["date_collected"] = primary["date_collected"]
        row["source_types"] = join_multi(r["source_type"] for r in g)
        row["source_verified"] = "true" if all(r["fetch_status"] == "200" for r in g) else "false"
        row["source_count"] = len({r["source_url"] for r in g})
        pairs.append((row, g))

    # unique tool_id (distinct tools that slug identically get a numeric suffix), assigned BEFORE
    # provenance rows are written so both files agree
    pairs.sort(key=lambda p: (p[0]["tool_id"], p[0]["vendor_maintainer"], p[0]["source_url"]))
    ids, rows, prov = defaultdict(int), [], []
    for row, g in pairs:
        ids[row["tool_id"]] += 1
        if ids[row["tool_id"]] > 1:
            row["tool_id"] += "-%d" % ids[row["tool_id"]]
        rows.append(row)
        for r in g:
            contributed = [f for f in ("vendor_maintainer", "country_region", "category", "license_model", "license",
                                       "first_release_year", "latest_version", "supported_platforms",
                                       "languages_formats") if r.get(f)]
            prov.append({"tool_id": row["tool_id"], "source_type": r["source_type"], "source_url": r["source_url"],
                         "date_collected": r["date_collected"], "fetch_status": r["fetch_status"],
                         "fields_reported": "; ".join(contributed)})

    # distinct tools sharing one website path -> review, never auto-merged (checked on the final rows)
    seen = defaultdict(list)
    for r in rows:
        if r["website_url"] and urlparse(r["website_url"]).path.strip("/"):
            seen[url_key(r["website_url"])].append(r["tool_id"])
    for k, tids in sorted(seen.items()):
        if len(tids) > 1:
            review.append({"type": "shared_website_path", "url_key": k, "tool_ids": tids})

    with open(PROCESSED / "eda_tools_clean.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FINAL_FIELDS)
        w.writeheader()
        w.writerows(rows)
    with open(PROCESSED / "provenance.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["tool_id", "source_type", "source_url", "date_collected", "fetch_status",
                                          "fields_reported"])
        w.writeheader()
        w.writerows(sorted(prov, key=lambda p: (p["tool_id"], p["source_type"], p["source_url"])))
    write_json(PROCESSED / "review_queue.json", review)
    excluded = read_json(PROCESSED / "excluded_records.json", []) or []
    write_json(PROCESSED / "excluded_records.json", [e for e in excluded if "only a vendor-origin" not in e.get("reason", "")] + orphans)
    # a duplicate = an extra record of the SAME source type merged into a tool; combining records of
    # different source types is cross-source enrichment, not duplication
    dups = sum(len(g) - len({r["source_type"] for r in g}) for _, g in pairs)
    write_json(PROCESSED / "dedup_stats.json", {"source_records": n, "canonical_tools": len(rows),
                                                 "duplicates_merged": dups,
                                                 "multi_source_tools": sum(1 for _, g in pairs if len(g) > 1),
                                                 "review_items": len(review)})
    print("dedup: %d source records -> %d tools (%d duplicates merged, %d review items)"
          % (n, len(rows), dups, len(review)))


if __name__ == "__main__":
    main()
