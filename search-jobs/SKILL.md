---
name: search-jobs
description: >-
  End-to-end job search pipeline: given a city (and optionally a job title,
  a result count, and free-form constraints), finds postings on LinkedIn for
  free via JobSpy (run on your own machine via a shell/PowerShell tool),
  creates application records in a Notion CRM, and drafts a personalized
  outreach email for each one. Always prioritizes the most accessible
  seniority levels first (graduate/associate/mid 1-3 years) before moving up
  to more senior roles you still have a real shot at. Trigger this skill
  when the user writes "/search-jobs [city]" OR the flag form
  "/search-jobs --location "Hong Kong" --job "software engineer" --results 15",
  or asks to "run a job search," "find me jobs," "fill my Notion with
  applications," or "find postings" for a given city, even without naming
  JobSpy or Notion explicitly. Uses the Notion connector and a
  shell/PowerShell tool with access to the user's own machine.
---

# Search Jobs — end-to-end application pipeline

This skill automates your job search for a target city end to end: find
LinkedIn postings (JobSpy, free) -> create application records in Notion ->
draft a personalized outreach email. Everything is driven by a single
required input: the city.

## One-time setup (read this before the first run)

This skill needs three things set up once. See the root `README.md` for the
full walkthrough with screenshots-equivalent step-by-step instructions.

1. **Your Notion CRM.** Two databases (Applications, and optionally People)
   with the exact properties documented in `references/notion-schema.md`.
   Fill in your own database IDs at the top of that file once you've created
   them — this skill reads that file before its first Notion call.
2. **Your candidate profile.** A `Candidate-Profile.md` file (copied from
   `templates/Candidate-Profile-Template.md` at the repo root and filled in)
   living in your own `context-input/` folder. This is what tells the skill
   who you are, what your "hooks" are, and how to tier target roles — it is
   never hardcoded in this skill.
3. **The JobSpy scraper**, which lives in this repo at
   `shared-tools/linkedin_jobs_free.py`. Requires Python 3.10+ and
   `pip install -U python-jobspy` on the machine that will actually run it
   (see "Required tools" below for why it can't run in a cloud sandbox).
   Replace `<repo-root>` in the commands below with the absolute path where
   you cloned this repository.

## Required tools

- **Notion** (`notion-create-pages`, `notion-update-page`, `notion-fetch`, `notion-search`, `notion-query-data-sources`)
- **A shell/PowerShell tool with access to your own machine**, to run the JobSpy scraper.

If Notion isn't connected, say so and stop. If shell access to your machine
isn't granted, ask for it — postings must be scraped from YOUR machine's
network connection, not from a cloud sandbox, which most job sites block
outright.

### The scraper

Script: `<repo-root>/shared-tools/linkedin_jobs_free.py` (JobSpy as the main
engine -> real LinkedIn/Indeed/Google postings; a free-API fallback if
LinkedIn rate-limits). Prerequisite on your machine: Python 3.10+ and
`python-jobspy` installed (`pip install -U python-jobspy`). The script
writes a JSON array of postings, which you then read.

---

## Input: parameters (city + options)

The skill accepts **two calling forms**, treated identically:

1. **Simple form**: `/search-jobs Paris` (just the city).
2. **Flag form**:
   `/search-jobs --location "Hong Kong" --job "software engineer" --results 15`

Parse the following flags (all optional except the city):

- `--location "<city>"` -> `{Location}` (e.g. "Hong Kong"). Without the flag,
  take the city given as plain text. If no city is given anywhere, ask:
  "Which city do you want to search?" before anything else.
- `--job "<title>"` -> `{JobQuery}`. When present, **this title becomes the
  priority target of the search** (passed to the scraper's `--search`,
  expanded to close variants). **Always read the market-analysis file
  (Step 0) if one exists** and use it to: (a) confirm this title is among
  the most in-demand in that city, (b) prioritize the companies/variants
  the analysis flags as most in-demand (focus score, volume), (c) pull the
  visa/language context. If the requested title is **low-demand** per the
  analysis, say so honestly and suggest the closest high-demand variant.
  Without `--job`, use the analysis file's Tier-1 list directly.
- `--results <n>` -> `{Results}` (default 20). Passed as-is to the
  scraper's `--results`.
- `--easy-apply` -> filter to LinkedIn **"Easy Apply" postings only**.
  Passes `--linkedin-easy-apply` to the scraper. Useful for maximizing fast
  response rate. Can be a direct flag or a free-form constraint ("easy apply
  only").

**Free-form constraints (natural language).** You can add plain-language
conditions to your request, e.g. "no [local language] required," "remote
only," "startups only," "exclude 5+ year roles." Interpret these as
**filters** applied after scraping, on each posting's title + description:
- "no [language] required" -> **exclude** any posting whose description
  requires that local language as mandatory. If in doubt (language listed
  as a "plus," not required), keep it.
- Generalize: any inclusion/exclusion constraint you state is applied as a
  hard filter before Notion records are created. If a constraint empties
  the whole result set, say so honestly instead of ignoring it.

Keep `{Location}`, `{JobQuery}`, `{Results}` and the constraint list for the
rest of the pipeline.

## Seniority priority (always)

Whatever the target role, **process postings from the most accessible level
up to the most demanding**, in this order:

1. **First**: graduate / entry / junior / associate / mid (≈0-3 years).
2. **Then**: more senior levels **only as long as you still have a real
   shot** (mid-senior asking for ~3-4 years, "senior" open to ~3-year
   profiles).
3. **Drop by default**: postings clearly out of reach right now
   (Staff/Principal/Lead/Manager/Director, or explicitly requiring 5+
   years), unless you explicitly ask to include them.

Infer the level from both the title AND the description (years of
experience requested). In the final recap and the order applications are
created, respect this junior -> senior progression.

---

## STEP 0 — Find (or build) the market-analysis file

The pipeline leans on a market-analysis file that ranks postings by
priority (Tier 1/2/3). These files live in whatever folder you configure as
your `Job_Market_Analysis/` output folder (the same one the
`job-market-analysis` skill writes to — see that skill's SKILL.md and the
root README for the exact path convention you choose).

Typical filename: `{Location}_Job_Market_Analysis_{Month}{Year}.md`
(e.g. `HK_China_Job_Market_Analysis_June2026.md`).

### 0a — Look for a matching file

1. List the contents of your `Job_Market_Analysis/` folder.
2. Look for a file whose **prefix matches `{Location}` or a close alias**.
   Ignore the date suffix. Examples of aliases to recognize:
   - `Paris` -> `Paris`, `IDF`, `Ile_de_France`, `France`
   - `Hong Kong` -> `HK`, `HK_China`, `HongKong`
   - `Singapore` -> `SG`, `Singapore`
   - `Shanghai` / `Beijing` -> `China`, `Shanghai`, `Beijing`
   - More generally: same city, same administrative region, or same country.
3. If **exactly one** file matches clearly -> use it (go to 0c).
4. If **several** files are plausible -> show the list and ask which to use.
5. If **none** match -> go to the fallback (0b).

### 0b — Fallback: no market analysis for this city yet

Don't invent a list of jobs. Have a short exchange:

1. Say there's no market analysis yet for `{Location}`, and ask:
   **"What roles / kinds of positions do you want to target in this city?"**
2. When they answer, evaluate each role against their profile (read
   `context-input/Candidate-Profile.md`, specifically its "target roles and
   priority tiers" and "feasibility notes" sections). For each requested
   role, say honestly:
   - **Realistic now** (matches their Tier 1)
   - **Stretch** (matches their Tier 2 — achievable but ambitious, often
     asks for more years than they have)
   - **Unrealistic** -> in this case, **propose a close, more accessible
     alternative** drawn from their own Tier 1 in `Candidate-Profile.md`.
3. Agree on a **final list of roles to search**. This list plays the role
   of the "Tier 1 jobs" for the rest of the pipeline.
4. (Optional, offer but don't force) Save this quick analysis into a new
   `{Location}_Job_Market_Analysis_{MonthYear}.md` file for next time.

### 0c — Extract context from the analysis file

If a file exists, read it and extract:
- The exact **target city/region** to use in every search and the Notion
  `Location` field (e.g. "Hong Kong", "Paris").
- The **Tier-1-ranked jobs** (and only Tier 1, unless told otherwise):
  title + company.
- Useful market context: local language, visa constraints, sectors.

**Visa constraint (always):** only keep companies likely to sponsor a work
visa for a foreign hire, if that applies to you (check
`Candidate-Profile.md`'s work-authorization field). Drop any posting that
explicitly states no visa sponsorship, if sponsorship is something you need.

---

## ANTI-DUPLICATE RULE (before ANY Notion record creation)

The skill can be re-run several times for the same city. To avoid
duplicates, **always check existence before creating** a page, and on a
match **update the existing page instead of creating a new one** — never
overwrite a field you've already filled in by hand.

### How to check
Use `notion-query-data-sources` on the Applications database with a filter:

- **Application**: look for a page whose `Job URL` == the posting's URL.
  This is the most reliable key (unique per posting). Fallback if there's
  no usable URL: same `Position` + same `Company`.

### What to do based on the result
- **No match** -> create the page normally (`notion-create-pages`).
- **Match found** -> do NOT recreate it. Reuse the existing page (keep its
  URL/id) and fill it in via `notion-update-page`:
  - Only fill **empty** fields (e.g. missing `Job Description`, `Outreach
    Email`, `Location`).
  - **Never overwrite** a field that's already filled in, especially
    `Status`, `Notes`, `Keywords Matched`, or dates — you may have edited
    them by hand.

At the end, report how many entries were **created** vs. **updated**
(already existing).

---

## STEP 1 — Find postings (JobSpy) + create Applications (Notion)

### 1a — LinkedIn search via JobSpy (shell/PowerShell, free)

Determine the **search terms** (`--search`):
- If `{JobQuery}` is given (`--job`) -> use it, expanded to close variants
  (e.g. "software engineer" -> "software engineer,software developer,
  backend engineer").
- Otherwise -> the **Tier-1 titles** from the analysis file (or the roles
  agreed on in 0b).

Run the scraper **on your own machine via shell/PowerShell access**. You
can group several titles into one command (comma-separated), and
`{Results}` comes from `--results` (default 20):

```powershell
cd "<repo-root>\shared-tools"
python linkedin_jobs_free.py --search "<terms>" --location "{Location}" --results {Results} --hours-old 720 --sites linkedin,indeed,google --out "_run_jobs.json"
```

Then read `_run_jobs.json` (via a file-read tool). Each entry contains:
`title`, `company`, `location`, `job_url` (direct LinkedIn/site URL),
`description` (full text), `date_posted`, `site`, `salary`.

Filter/prioritize, in this order:
1. **Visa constraint** (if applicable to you): drop postings that explicitly
   rule out sponsorship.
2. **Your free-form constraints** (e.g. "no [language] required," "remote
   only"): apply as hard filters on title + description.
3. **Relevance**: if `{JobQuery}` -> keep postings matching that role;
   otherwise -> keep postings matching the Tier-1 companies + titles.
4. **Seniority sort**: order the kept postings from most accessible to most
   senior (see "Seniority priority" above), dropping levels clearly out of
   reach (5+ years / Staff / Principal / Lead / Manager / Director) unless
   told otherwise.

> Time-window note: `--hours-old 720` = 30 days. If results are thin,
> widen to `--hours-old 4320` (6 months). The script falls back to
> Indeed/Google, then Jobicy, if LinkedIn rate-limits; report which source
> was actually used (the `[engine] ...` lines in the script's output).

> Visa note: do NOT exclude a posting just because visa sponsorship isn't
> mentioned. Judge by company reputation; only drop a posting if it
> explicitly rules out sponsorship.

### 1b — Create the Application in Notion

For each kept posting, **apply the anti-duplicate rule above first**
(search by `Job URL`). If the posting doesn't exist yet, call
`notion-create-pages` on the Applications database; if it exists, update
the existing page. The full schema, IDs and an example are in
`references/notion-schema.md` — **read it before the first call**.

Fill-in rules: `Status = "To Apply"`, `Source = "LinkedIn"`,
`Location = [target city]`, `Job Description` = the JSON's `description`
field, `Job URL` = the JSON's `job_url` field, `Date Applied` = today's date
(ISO-8601). Leave `Contacts` empty (see Step 2).

**Save the Notion URL** of each Application created — it's used for the
email in Step 3.

---

## STEP 2 — Contacts (left empty for now)

There's no free, reliable source for finding recruiter contacts (JobSpy
doesn't return a recruiter). By default:

- **Leave the Application's `Contacts` field empty.**
- **Don't create People pages.**
- If the JSON does contain a non-empty `recruiter_name`/`recruiter_url` for
  a posting (rare), you can note it in the Application's `Notes` — but
  never invent one or create a People page from it.

You can fill in contacts by hand later, or via a dedicated tool (e.g. a
free tier of a contact-enrichment service) if you decide to connect one.

---

## STEP 3 — Outreach email + Application update

For each Application, draft a personalized outreach email. Since there's
usually no named contact (Step 2), address it generically to the
**recruiter / hiring manager** of the company (e.g. "Dear Hiring Team" /
"Dear [Company] Hiring Manager"). The full style guide, exact structure and
your project "hooks" are in `references/outreach-email-guide.md` — **read
it before drafting**.

Key principles: English (always), max ~200 words, first person, a
hook-driven opening sentence tying your profile to this specific posting,
no filler, one clear CTA, standard signature. Every email must prove you
read the posting: read the description fetched in Step 1, identify 2-3 key
requirements, and match them precisely to your projects from
`Candidate-Profile.md`'s "key achievements" section.

Update the Application via `notion-update-page`: fill in `Outreach Email`
with the drafted text.

---

## Execution summary

```
Input: parse --location / --job / --results + free-form constraints (or a plain city)
Step 0: resolve {Location} -> market-analysis file (context; Tier-1 list if no --job)
Step 1a: shell/PowerShell -> python linkedin_jobs_free.py --search <role|Tier1> --location {Location} --results {Results} ... --out _run_jobs.json -> read the JSON
          -> filter (visa, free-form constraints, relevance) -> SORT junior->senior
For each kept posting, in junior -> senior order:
  1b. notion-create-pages (Application, Status "To Apply", Job URL, Job Description) -> save the URL
  2.  Contacts left empty (no People pages)
  3.  Draft the Outreach Email (generic recipient) -> notion-update-page (Application.Outreach Email)
```

At the end, give a short recap: number of Applications created vs. updated,
which engine was used (linkedin/indeed/jobicy), and the Notion links of the
pages.

## Guardrails

- **Visa**: never keep a posting that explicitly excludes sponsorship, if
  sponsorship applies to you.
- **Never invent anything**: no fake posting, no fake contact, no invented
  email. If JobSpy returns nothing for a role, say so and move on.
- **Execution on your machine**: postings are scraped via shell/PowerShell
  access to your own machine (which has normal internet access), never via
  a cloud sandbox's shell (which blocks most job sites). Always read the
  JSON the script produced, never assume its content.
- **Scope**: by default, process **all relevant Tier-1 postings** found (no
  cap). The script returns up to `--results 20` candidates per query; among
  them, keep all the relevant Tier-1 ones. If you want a different scope
  (Tier 2/3, or a hard cap like "just 3"), that instruction is respected.
