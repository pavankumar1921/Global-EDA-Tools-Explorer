"""Collector 5 - open-source repositories through the public GitHub REST API.

Source type: public_repository. Repositories come from the seed ('repository': 'owner/name') first, then
from GitHub links found by the other collectors in this snapshot.

Per repository: GET /repos/{r} (licence SPDX id, owner, homepage, description + topics -> category), then GET /repos/{r}/releases/latest
(tag + publication date). If the project publishes no GitHub releases, GET /repos/{r}/tags?per_page=1
gives the newest tag name only (no date: a tag's date would need another call per tag).
first_release_year is NOT inferred from the repository creation date (a repo can be created long after
the tool first shipped, e.g. a migration from SourceForge).

Rate limit: 60 requests/hour without a token. The collector reads X-RateLimit-Remaining and stops
cleanly when it runs out, logging every repository it could not reach. Set GITHUB_TOKEN (never commit
it) for 5,000 requests/hour.
"""
import json
import os

from common import (categorize, empty_raw_record, join_multi, ensure_dirs, github_repo_key, license_model_from, load_seed,
                    log_event, norm_license, polite_get, raw_path, read_json, today, write_json)

API = "https://api.github.com/repos/%s"
SKIP_SPDX = {"NOASSERTION", "OTHER"}


def repo_list():
    seen, out = set(), []
    for t in load_seed():
        r = (t.get("repository") or "").lower()
        if r and r not in seen:
            seen.add(r)
            out.append((t["tool_name"], t["repository"]))
    for src in ("published_list", "wikipedia_article"):
        for rec in read_json(raw_path(src), []) or []:
            r = github_repo_key(rec.get("repository_url", ""))
            if r and r not in seen:
                seen.add(r)
                out.append((rec["tool_name"], r))
    return out


def main():
    ensure_dirs()
    headers = {"X-GitHub-Api-Version": "2022-11-28"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    records, remaining = [], None
    repos = repo_list()

    def get(url):
        nonlocal remaining
        status, body, err, hdrs = polite_get(url, accept="application/vnd.github+json", delay=1.0, headers=headers)
        rl = {k.lower(): v for k, v in hdrs.items()}.get("x-ratelimit-remaining")
        if rl is not None:
            remaining = int(rl)
        return status, body, err

    for i, (tool, repo) in enumerate(repos):
        if remaining is not None and remaining < 3:
            for _, r in repos[i:]:
                log_event("skipped_rate_limit", collector="public_repositories", repo=r)
            print("GitHub rate limit reached: %d repositories skipped (set GITHUB_TOKEN)" % (len(repos) - i))
            break
        status, body, err = get(API % repo)
        if status != 200:
            log_event("fetch_failed", collector="public_repositories", url=API % repo, status=status, error=err)
            continue
        meta = json.loads(body)
        version, rel_date = "", ""
        st, rb, _ = get(API % repo + "/releases/latest")
        if st == 200:
            rel = json.loads(rb)
            version, rel_date = rel.get("tag_name") or rel.get("name") or "", (rel.get("published_at") or "")[:10]
        elif st == 404:
            st, tb, _ = get(API % repo + "/tags?per_page=1")
            if st == 200 and json.loads(tb):
                version = json.loads(tb)[0].get("name", "")
        # category from the maintainers' own one-line description and topics (earliest keyword wins)
        desc = meta.get("description") or ""
        cats = categorize(desc, by_position=True) or categorize(" ".join(meta.get("topics") or []), by_position=True)
        spdx = (meta.get("license") or {}).get("spdx_id") or ""
        lic = "" if spdx in SKIP_SPDX else norm_license(spdx)
        records.append(empty_raw_record(
            tool_name=tool, vendor_maintainer=(meta.get("owner") or {}).get("login", ""),
            category=cats[0] if cats else "", additional_categories=join_multi(cats[1:]),
            license=lic, license_model=license_model_from(lic),
            website_url=meta.get("homepage") or "", repository_url=meta.get("html_url", ""),
            latest_version=version, latest_release_date=rel_date, latest_release_year=rel_date[:4],
            source_url=API % repo, source_type="public_repository", date_collected=today(),
            fetch_status=status))
        records[-1]["_evidence"] = desc[:300]
    out = raw_path("public_repository")
    write_json(out, records)
    print("repositories: %d of %d records -> %s" % (len(records), len(repos), out))


if __name__ == "__main__":
    main()
