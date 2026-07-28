# shared-tools

Scripts used by more than one skill in this repo.

## `linkedin_jobs_free.py`

A free, multi-site job scraper built on [`python-jobspy`](https://github.com/speedyapply/JobSpy).
Both `search-jobs` (find and apply to jobs) and `job-market-analysis`
(aggregate market trends) call this same script — one to find candidate
postings, the other to pull hundreds of postings for statistical analysis.

See the docstring at the top of the script for full usage, or the root
`README.md` for how it fits into the overall setup and why it runs on your
own machine instead of in a cloud sandbox.

Quick setup:

```bash
python -m pip install -U python-jobspy
```

Quick test:

```bash
python linkedin_jobs_free.py --search "Software Engineer" --location "Remote" --results 5 --out test.json
```
