---
name: job-market-analysis
description: >-
  Job market analysis for a target city/country. Given a city, runs a large,
  FREE LinkedIn job search via JobSpy (run on your own machine via
  shell/PowerShell; aims for ≥400 postings in your target niche plus a
  broad market scan), aggregates trends (most in-demand roles overall, and
  by seniority: graduate/associate/2-year), identifies which Tier 1/2/3
  roles are realistic and where you should focus applications, then writes
  a market-analysis file to your Job_Market_Analysis folder. That file then
  feeds Step 0 of the `search-jobs` skill. Trigger this skill when the user
  writes "/job-market-analysis [city]" (e.g. "/job-market-analysis Taiwan",
  "/job-market-analysis Singapore"), or asks "analyze the job market in
  [city]," "what roles are in demand in [city]," "where should I apply in
  [city]," "tech market trends in [city]." Uses a shell/PowerShell tool for
  the JobSpy scrape.
---

# Job Market Analysis

This skill produces a **job market analysis** for a target city, in the same
style as the example templates in `references/`, driven by a large JobSpy
scrape (free) rather than hand-waved judgment. Its output is the **input to
Step 0 of the `search-jobs` skill**.

## One-time setup (read this before the first run)

1. **Your candidate profile.** A `Candidate-Profile.md` file (copied from
   `templates/Candidate-Profile-Template.md` at the repo root and filled
   in) living in your own `context-input/` folder. This is what tells the
   skill your background, target roles, and priority tiers — never
   hardcoded here.
2. **The JobSpy scraper**, at `<repo-root>/shared-tools/linkedin_jobs_free.py`
   in this repo. Requires Python 3.10+ and `pip install -U python-jobspy`
   on the machine that runs it. Replace `<repo-root>` in the commands below
   with the absolute path where you cloned this repository.
3. **A `Job_Market_Analysis/` output folder** somewhere accessible both to
   your machine (for the scrape) and to the sandbox running this skill (for
   the aggregation script). Pick a path once and reuse it consistently —
   `search-jobs` needs to find files here too.

## Required tools

- **A shell/PowerShell tool with access to your own machine**, to run the
  JobSpy scraper (a cloud sandbox has no access to job sites). If access
  isn't granted, ask for it.
- **Shell access to the sandbox**, to run `scripts/aggregate.py` on the
  scraped JSON files.

### The scraper

Script: `<repo-root>/shared-tools/linkedin_jobs_free.py` (JobSpy -> real
LinkedIn postings + Indeed/Google/Jobicy fallback). Prerequisite on your
machine: Python 3.10+ and `python-jobspy` (`pip install -U python-jobspy`).
The script writes one JSON file of postings per role family;
`aggregate.py` reads them (fields `title`, `company`, `location`,
`job_url`, `description` — already compatible).

## Output

A Markdown file in your configured output folder:
```
<your Job_Market_Analysis folder>/
```
Name: `{Prefix}_Job_Market_Analysis_{Month}{Year}.md` (e.g.
`Taiwan_Job_Market_Analysis_June2026.md`). `{Prefix}` comes from
`references/market-config.md` (e.g. Taiwan -> `Taiwan`, Hong Kong -> `HK`).

---

## INPUT: the target city

Given as an argument, e.g. `/job-market-analysis Taiwan`. If missing, ask:
"Which city do you want to run the market analysis for?" before anything
else.

Keep the raw value as `{Location}`. Then resolve it via
`references/market-config.md`: `location_search`, `file_prefix`,
`local_language` (+ keywords), `visa`, `known_hubs`. If the city isn't
listed -> use the `DEFAULT` block plus a quick web search (business
language, typical visa sponsorship).

## Depth (mode)

Default: **standard, ≥400 postings in your target niche** (a firm
requirement), roughly 500+ raw postings across all families combined.
Accept if you specify: `quick` ~180 (fast test), `standard` ≥400 niche
(default), `deep` ~1000 (reliable family × seniority verdicts). The mode
only changes `--results` per run (see Step 2).

---

## STEP 1 — Pre-flight

Before scraping, announce the plan: number of families × `--results` ×
sites ≈ estimated volume, and confirm the target (≥400 niche postings in
`standard` mode). The JobSpy scrape is **free** (no credits, no paid API),
so there's no cost guardrail; the only risk is LinkedIn rate-limiting at
very high volume, which is worked around by also scraping Indeed + Google
and, if needed, several locations.

Read `references/role-taxonomy.md` (families + search terms) and
`references/market-config.md` (resolved at input time). Prepare the output
folder for the scraped datasets (reachable by both your machine and the
sandbox):
```
<your Job_Market_Analysis folder>\_scrape_data\<Location>\
```

---

## STEP 2 — JobSpy scrape via shell/PowerShell (niche + broad scan)

Run the scraper **on your own machine via shell/PowerShell access**. One
command per family, writing a JSON file to
`_scrape_data\<Location>\<family>.json`.

**Build the query matrix** (from `role-taxonomy.md`):
- **Niche layer**: one query per family in Section A (your target roles,
  ~11 families in the example taxonomy). `--search` = that family's terms
  (comma-separated), `--location` = the city's `location_search`.
- **Broad-scan layer**: one query per family in Section B (general market
  pulse, ~6 families in the example taxonomy).

**Parameters per run:**
- `--results` by mode: quick→15, **standard→40 (niche) / 20 (broad)**, deep→70.
- `--sites linkedin,indeed,google` (multi-site keeps volume up even if
  LinkedIn rate-limits; JobSpy returns up to `--results` per site).
- `--hours-old 4320` by default (6 months — maximizes volume for solid
  conclusions). For a "fresh trend" read, run one extra pass at
  `--hours-old 720` (30 days) only if asked.
- **Multi-location**: if `market-config.md` lists several `location_search`
  values for the city (e.g. Taiwan = "Taipei, Taiwan" + "Taiwan"), run the
  niche layer against each to boost volume.

Example (one niche family):
```powershell
cd "<repo-root>\shared-tools"
python linkedin_jobs_free.py --search "Customer Engineer,Customer Success Engineer,Field Engineer" --location "Taipei, Taiwan" --results 30 --hours-old 4320 --sites linkedin,indeed,google --out "<your Job_Market_Analysis folder>\_scrape_data\Taiwan\CustomerEngineer.json"
```

> **≥400-postings guarantee (control loop).** After scraping the whole
> niche layer, run `aggregate.py` (Step 3) once and read the Snapshot
> ("Postings kept in your target niche: N"). **If N < 400**, widen and
> re-scrape BEFORE writing the report: (a) raise `--results` to 60, (b) add
> nearby locations, (c) add close title variants, (d) keep `--hours-old
> 4320`. Repeat until N ≥ 400 (or, if the market is genuinely too small,
> say so honestly in the doc with the N actually reached).

> **Saving datasets**: each run writes its JSON to `_scrape_data\<Location>\`.
> DO NOT load hundreds of postings into context — aggregate via the script.
> If a run fails (rate-limit), note it, retry, or move to the next family.

---

## STEP 3 — Aggregation (Python script, sandbox)

Run the quantitative engine on the dataset folder (the sandbox mount of
your `_scrape_data\<Location>` folder):

```bash
python3 <skill-path>/scripts/aggregate.py \
  "/path/to/mounted/_scrape_data/Taiwan" \
  --city "Taipei, Taiwan" \
  --lang-keywords "mandarin,中文,繁體中文,native chinese" \
  --out /tmp/market_stats.md
```

(`--lang-keywords` = the city's `local_language.keywords` from
`market-config.md`. If the city is English-first / low severity, you can
omit it — the default covers Mandarin.)

The script dedupes, normalizes title -> family, infers seniority, detects
the local-language barrier, and writes ready-to-paste Markdown blocks to
`--out`: Market snapshot, General trends, Volume by family, **Role ×
seniority matrix**, **Focus score**, and an appendix listing the kept
niche postings (with URL).

Read `/tmp/market_stats.md` (compact) — this is the **only** data you load
into context. Check the "niche kept ≥ 400" counter here (otherwise, loop
back to Step 2).

---

## STEP 4 — Write the analysis file

Read `references/output-template.md` (exact structure + the tiering rule +
the CONTRACT with `search-jobs`) and `context-input/Candidate-Profile.md`
(positioning + hooks).

Assemble the output `.md`:
1. **Auto sections** (0, 1, 2a/2b/2c): paste `aggregate.py`'s output as-is.
2. **Curated sections** (Tier 1/2/3, Priority Companies, Positioning,
   Sequencing, Signals): from the **real-postings appendix** the script
   produced, classify each posting into Tier 1/2/3 per the tiering rule.
   **Only cite postings that are actually present** in the appendix, never
   invent one.
3. Respect the **fixed format of the "Tier 1" section**
   (`| Role | Company | Level | Notes |`) — this is what `search-jobs`
   parses.
4. Drop: `EXCLUDED` families, postings with `lang!` on a high-severity
   language market, postings that explicitly exclude visa sponsorship (if
   sponsorship applies to you).

Write the file to your `Job_Market_Analysis/` folder with the right name.
Then present it.

---

## Execution summary

```
0. Resolve {Location} -> market-config (location_search, prefix, language, visa, hubs)
1. Pre-flight: read taxonomy, prepare _scrape_data\<Location>\, announce ≥400-niche-postings target
2. Shell/PowerShell: python linkedin_jobs_free.py per family (niche ~11 + broad ~6),
   --sites linkedin,indeed,google --hours-old 4320 -> dump JSON into _scrape_data\<Location>\
   -> LOOP: aggregate, if niche kept < 400 -> widen + re-scrape
3. sandbox: python3 scripts/aggregate.py <...>/_scrape_data/<Location> --city ... --lang-keywords ... --out stats.md
4. Read stats.md -> write the final .md (auto + Tier 1/2/3 curation) -> Job_Market_Analysis\
```

At the end: a short recap (postings analyzed, niche kept, top 3 families by
focus score, file path), and a reminder that you can follow up with
`/search-jobs {Location}`.

## Guardrails

- **Volume**: aim for **≥400 niche postings kept** before concluding;
  otherwise widen (results, locations, variants, 6-month window). If the
  market is genuinely too small, write that honestly with the N reached.
  Note: don't over-read family × seniority cells with a count below ~25
  (anecdotal).
- **Execution on your machine**: the scrape runs via shell/PowerShell on
  your own machine (open internet access), never via the sandbox's shell
  (which blocks job sites). Aggregation runs in the sandbox on the JSON
  already written.
- **Never invent anything**: no posting/company outside the dataset. If a
  family returns nothing, write that honestly.
- **Context**: never load hundreds of raw postings into context — go
  through the script. Only `stats.md` and its appendix are read.
- **LinkedIn rate-limit**: at very high volume LinkedIn may cut off;
  multi-site (Indeed/Google) compensates. Note in the doc which source(s)
  were actually used.
- **`search-jobs` contract**: keep the Tier-1 section in the fixed table
  format (`| Role | Company | Level | Notes |`) — breaking it breaks the
  downstream skill's parsing.
