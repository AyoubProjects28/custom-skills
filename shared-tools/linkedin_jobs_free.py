#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
linkedin_jobs_free.py — free, multi-site job scraper used by the
`search-jobs` and `job-market-analysis` skills.

It is a thin CLI wrapper around the open-source `python-jobspy` library,
which scrapes LinkedIn, Indeed, Glassdoor and Google Jobs without needing a
paid API or scraping credits. If every requested site comes back empty (most
commonly a temporary LinkedIn rate-limit), it falls back once to Jobicy's
free public API for remote-friendly postings.

This script runs on YOUR machine (via a terminal, or via an MCP tool that
gives an agent shell access to your computer), not inside a cloud sandbox —
job sites generally block scraping from shared/cloud IP ranges, so this has
to run from a normal residential/office connection.

-------------------------------------------------------------------------
SETUP (one time)
-------------------------------------------------------------------------
    python -m pip install -U python-jobspy

python-jobspy pulls in pandas as a dependency; both install cleanly with pip
on Windows, macOS and Linux. No account, API key, or paid plan required.

-------------------------------------------------------------------------
USAGE
-------------------------------------------------------------------------
    python linkedin_jobs_free.py \\
        --search "Software Engineer,Backend Engineer,Platform Engineer" \\
        --location "New York, NY" \\
        --results 30 \\
        --hours-old 720 \\
        --sites linkedin,indeed,google \\
        --out jobs.json

Flags:
    --search            Comma-separated job titles / search terms. Each term
                         is scraped as a separate query and results are
                         merged and deduplicated.
    --location           Free-text location, passed straight to jobspy
                         (e.g. "Hong Kong", "Remote", "Paris, France").
    --results             Results wanted PER SITE PER SEARCH TERM (default 20).
                         Total volume ≈ len(sites) × len(search terms) × results.
    --hours-old            Max posting age in hours. 720 = 30 days (recent/fresh
                         search), 4320 = 6 months (maximize volume for market
                         analysis). Default 720.
    --sites                Comma-separated jobspy site names: any of
                         linkedin, indeed, glassdoor, google, zip_recruiter.
                         Default "linkedin,indeed,google". Using more than
                         one site is the main defense against a single site
                         (usually LinkedIn) rate-limiting you.
    --linkedin-easy-apply   Only return LinkedIn postings with "Easy Apply"
                         enabled.
    --country-indeed       Country filter passed to jobspy for Indeed/Glassdoor
                         (default "USA"). Set to the country you're searching in.
    --out                  Path to write the output JSON array to (required).

-------------------------------------------------------------------------
OUTPUT
-------------------------------------------------------------------------
A JSON array written to --out, one object per job, deduplicated by URL
(falling back to title+company when a listing has no URL):

    {
      "title": "...", "company": "...", "location": "...",
      "job_url": "...", "description": "...", "date_posted": "...",
      "site": "linkedin" | "indeed" | "google" | "glassdoor" | "jobicy",
      "salary": "min-max CUR" | ""
    }

`description` is the full posting text — this is what the calling skill
filters on (visa mentions, required languages, seniority, keywords). Nothing
is truncated here; keeping large descriptions out of the calling LLM's
context is the job of the *caller* (read this JSON with a script, not by
pasting it into a prompt — see the root README's "why this architecture is
token-efficient" section).

Progress and fallback events are logged to stderr as "[engine] ..." lines so
a calling agent can report which source actually produced the data.
"""
import argparse
import json
import sys
import urllib.request
import urllib.parse


def log(msg):
    print("[engine] %s" % msg, file=sys.stderr)


def _salary_str(row):
    lo = row.get("min_amount")
    hi = row.get("max_amount")
    cur = row.get("currency")
    if lo or hi:
        lo_s = "" if lo is None or (isinstance(lo, float) and lo != lo) else str(lo)
        hi_s = "" if hi is None or (isinstance(hi, float) and hi != hi) else str(hi)
        return ("%s-%s %s" % (lo_s, hi_s, cur or "")).strip()
    return ""


def run_jobspy(search_terms, location, results, hours_old, sites, easy_apply, country):
    try:
        from jobspy import scrape_jobs
    except ImportError:
        log("python-jobspy is not installed. Run: python -m pip install -U python-jobspy")
        return []

    all_rows = []
    terms = [t.strip() for t in search_terms.split(",") if t.strip()]
    for term in terms:
        log("scraping sites=%s term=%r location=%r results_wanted=%d hours_old=%d"
            % (sites, term, location, results, hours_old))
        try:
            df = scrape_jobs(
                site_name=sites,
                search_term=term,
                google_search_term="%s jobs near %s" % (term, location),
                location=location,
                results_wanted=results,
                hours_old=hours_old,
                country_indeed=country,
                linkedin_fetch_description=True,
                linkedin_easy_apply=easy_apply or None,
            )
        except Exception as e:
            log("scrape_jobs failed for term=%r: %s" % (term, e))
            continue
        if df is None or df.empty:
            log("0 results for term=%r" % term)
            continue
        for _, row in df.iterrows():
            all_rows.append({
                "title": str(row.get("title") or ""),
                "company": str(row.get("company") or ""),
                "location": str(row.get("location") or ""),
                "job_url": str(row.get("job_url") or ""),
                "description": str(row.get("description") or ""),
                "date_posted": str(row.get("date_posted") or ""),
                "site": str(row.get("site") or ""),
                "salary": _salary_str(row),
            })
        log("term=%r -> %d rows so far (cumulative)" % (term, len(all_rows)))
    return all_rows


def run_jobicy_fallback(search_terms, results):
    """Free public API, remote-friendly postings only. Used only when every
    jobspy site returned zero rows (most often a LinkedIn rate-limit)."""
    log("jobspy returned 0 rows overall, falling back to Jobicy (remote jobs only)")
    term = search_terms.split(",")[0].strip()
    url = "https://jobicy.com/api/v2/remote-jobs?" + urllib.parse.urlencode({
        "count": min(results, 50),
        "tag": term,
    })
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        log("jobicy fallback failed: %s" % e)
        return []
    out = []
    for j in data.get("jobs", []):
        lo = j.get("annualSalaryMin")
        hi = j.get("annualSalaryMax")
        out.append({
            "title": j.get("jobTitle", ""),
            "company": j.get("companyName", ""),
            "location": j.get("jobGeo", "Remote"),
            "job_url": j.get("url", ""),
            "description": j.get("jobExcerpt", ""),
            "date_posted": j.get("pubDate", ""),
            "site": "jobicy",
            "salary": ("%s-%s" % (lo, hi)) if lo else "",
        })
    log("jobicy fallback -> %d rows" % len(out))
    return out


def dedup(rows):
    seen, out = set(), []
    for r in rows:
        key = r["job_url"] or (r["title"] + "|" + r["company"])
        key = key.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser(
        description="Free multi-site job scraper (LinkedIn/Indeed/Glassdoor/Google via python-jobspy).")
    ap.add_argument("--search", required=True, help="comma-separated search terms / job titles")
    ap.add_argument("--location", required=True)
    ap.add_argument("--results", type=int, default=20,
                     help="results wanted per site per search term (default 20)")
    ap.add_argument("--hours-old", type=int, default=720,
                     help="max posting age in hours; 720=30d, 4320=6mo (default 720)")
    ap.add_argument("--sites", default="linkedin,indeed,google",
                     help="comma-separated jobspy site names (default linkedin,indeed,google)")
    ap.add_argument("--linkedin-easy-apply", action="store_true",
                     help="only LinkedIn postings with Easy Apply enabled")
    ap.add_argument("--country-indeed", default="USA",
                     help="country filter for indeed/glassdoor (default USA)")
    ap.add_argument("--out", required=True, help="path to write the output JSON array")
    args = ap.parse_args()

    sites = [s.strip() for s in args.sites.split(",") if s.strip()]
    rows = run_jobspy(args.search, args.location, args.results, args.hours_old,
                       sites, args.linkedin_easy_apply, args.country_indeed)
    if not rows:
        rows = run_jobicy_fallback(args.search, args.results)

    rows = dedup(rows)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    log("wrote %d deduplicated jobs -> %s" % (len(rows), args.out))


if __name__ == "__main__":
    main()
