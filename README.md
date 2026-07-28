# claude-skills

Three Claude Skills that together form a free, end-to-end job-search
pipeline: analyze a city's job market, find and log postings, and generate
a tailored CV + cover letter + outreach email for each one.

- **`job-market-analysis`** — scrapes hundreds of postings for a target
  city and turns them into a ranked report: which roles are most in
  demand, at which seniority, and where you specifically should focus.
- **`search-jobs`** — finds postings for a city, logs them as application
  records in a Notion CRM, and drafts a personalized outreach email for
  each one.
- **`adapt-cv`** — tailors your master CV (and optionally your cover
  letter) to a specific job description, one document at a time or in
  batch over every "To Apply" row in your Notion CRM.

All three are designed to be **generic**: nothing in this repo contains
anyone's personal data. Your CV, your career facts, your Notion database
IDs, and your API tokens all live in files you create locally, outside this
repo, following the templates provided here.

---

## Table of contents

1. [How the pieces fit together](#how-the-pieces-fit-together)
2. [Why this architecture is token-efficient](#why-this-architecture-is-token-efficient)
3. [What JobSpy is](#what-jobspy-is)
4. [Setup](#setup)
5. [Setting up your Notion CRM](#setting-up-your-notion-crm)
6. [Usage](#usage)
7. [Costs](#costs)

---

## How the pieces fit together

```
job-market-analysis  →  writes a market-analysis .md file (which roles, where, at what seniority)
        ↓
   search-jobs        →  reads that file, scrapes matching postings, logs them to Notion,
        ↓                 drafts an outreach email per posting
        ↓
    adapt-cv          →  reads your Notion "To Apply" rows (or a single pasted JD),
                          tailors your CV/cover letter per posting
```

You don't have to use all three — `adapt-cv` works standalone against a
single pasted job description with no Notion or JobSpy setup at all.
`search-jobs` works standalone too, using a quick manual Q&A instead of a
market-analysis file if you skip `job-market-analysis`. But run together,
each skill's output is the next one's input, so a whole session (find
postings for a city → log them → draft a tailored CV and outreach email for
each) requires only a couple of top-level commands.

---

## Why this architecture is token-efficient

The expensive part of any of these tasks isn't the reasoning, it's the raw
text volume: a formatted resume's underlying XML can run 5,000-15,000+
tokens, and a batch of scraped job postings with full descriptions can
easily total hundreds of thousands of tokens. Every skill in this repo is
built around one rule: **push bulk text processing into a deterministic
script, and only let the model see compact summaries.**

- **`adapt-cv/engine.py`** never regenerates a resume. It takes a small
  JSON "edit plan" (a handful of find-and-replace pairs, roughly 50-150
  tokens) and does raw XML surgery on a copy of your `.docx`, entirely
  outside the model's context. The model never reads or re-emits the
  document's XML; it only sees a one-line JSON status back
  (`{"warnings": [], "pages": 1}`). This turns an edit's cost from
  "proportional to document size" into a small constant, regardless of how
  long your CV is or how many edits you make.
- **`job-market-analysis/scripts/aggregate.py`** does the same for job
  postings. A single market scan can pull 400-1000+ full postings —
  potentially half a million tokens of raw descriptions. The script reads
  every posting on disk, dedupes, classifies, and scores them in plain
  Python, and only the resulting Markdown tables (a few hundred tokens
  total) ever enter the model's context. Reading 500 raw postings directly
  in a prompt would be both prohibitively expensive and, past a certain
  volume, literally impossible to fit in a context window.
- **`adapt-cv/fetch_to_apply.py`** talks to the Notion API directly via
  `urllib` and writes one clean Markdown file per job offer to disk. The
  model reads a compact manifest (`{index, company, role, status}`) instead
  of Notion's verbose, deeply nested JSON API responses.
- **`shared-tools/linkedin_jobs_free.py`** writes scraped postings straight
  to a JSON file on disk. The calling skill reads that file with a script
  or a targeted read, not by pasting hundreds of postings into a prompt.

The net effect: the model's job is reduced to the part that actually needs
judgment (deciding *what* to tailor, *which* postings matter, *how* to
frame an achievement) while every mechanical, high-volume step (rewriting
document XML, parsing hundreds of postings, calling an API and reshaping
its response) runs in a script that costs the same whether it processes one
job posting or a thousand.

### Roughly how many tokens does tailoring one CV cost?

There's no exact fixed number since it depends on your CV's length and how
much reasoning a given job description requires, but the order of
magnitude looks like this, in a single Claude Skills / Cowork session:

| Step | Approx. tokens | Notes |
|---|---|---|
| Read `Candidate-Profile.md` + parse the JD (once per session) | ~1,500-3,000 | fixed cost, paid once no matter how many CVs you generate that session |
| Build the edit plan + reasoning per CV | ~1,000-2,500 | this is the part that scales with JD complexity, not document length |
| Run `engine.py` (JSON in, JSON status out) | ~150-400 | flat, regardless of CV length or number of edits |
| Step 6 proofread + ATS/JD-fit scoring | ~500-1,200 | one `pdftotext` extract read once, not re-rendered |
| **Marginal cost per CV after the first** | **~3,000-6,000** | |
| **First CV of a session (includes the fixed read)** | **~5,000-9,000** | |

For a 10-CV batch run in the default sequential mode (see `adapt-cv`'s
Batch mode section), the total cost is roughly `1 × fixed cost + 10 ×
marginal cost` — around 35,000-65,000 tokens for the whole batch, not
10× the first CV's cost. This is why batch mode defaults to one shared
context instead of spinning up 10 independent sub-agents that would each
re-pay the fixed cost (the `--isolate` flag exists for when you actually
need that stronger isolation and are willing to pay for it).

---

## What JobSpy is

[`python-jobspy`](https://github.com/speedyapply/JobSpy) is an open-source
Python library that scrapes job postings from LinkedIn, Indeed, Glassdoor,
Google Jobs and ZipRecruiter and returns them as a clean, structured
dataset (title, company, location, URL, full description, salary if
listed, posting date). It's free, requires no API key, and needs no paid
plan or scraping credits — you `pip install` it and call it from a normal
Python script.

That's the entire reason this pipeline can run for free: instead of paying
for a jobs API or a scraping service, `shared-tools/linkedin_jobs_free.py`
is a thin CLI wrapper around JobSpy that both `search-jobs` and
`job-market-analysis` call to pull postings. The trade-off is that
scraping has to run from a normal machine (yours) rather than a cloud
sandbox, since job sites generally block requests coming from
cloud/datacenter IP ranges — see the Setup section below.

---

## Setup

### 1. Prerequisites

- **Claude** with Skills support (Claude Code, the Claude Agent SDK, or
  Cowork/Claude Desktop with skills enabled).
- **Python 3.10+** on the machine that will run the scraper (your own
  computer — see below for why).
- **`python-jobspy`**, the only external Python dependency in this repo
  (everything else — `engine.py`, `fetch_to_apply.py`, `aggregate.py` — is
  pure standard library, nothing to install). Install it with:
  ```bash
  python -m pip install -r requirements.txt
  ```
- **LibreOffice** and **poppler** (`pdfinfo`, `pdftotext`) available in
  whatever environment runs `adapt-cv/engine.py` — this is what renders
  the tailored `.docx` to a one-page-checked PDF. Most sandboxed shell
  environments used by Claude Skills ship these by default; if yours
  doesn't, install them (`apt install libreoffice poppler-utils` on
  Debian/Ubuntu, or the equivalent for your OS).
- **A Notion account and a Notion internal integration token**, only
  needed for `search-jobs` and `adapt-cv`'s batch mode — see below.

### 2. Clone the repo and install the skills

```bash
git clone https://github.com/<your-username>/claude-skills.git
```

Point your Claude Skills directory at (or copy) the three skill folders
(`adapt-cv/`, `search-jobs/`, `job-market-analysis/`) exactly as they are —
each one is a self-contained skill with its own `SKILL.md`. How you "install"
a skill depends on which Claude product you're using (Claude Code, the
Agent SDK, or Cowork); consult your product's skills documentation for the
exact install location. `shared-tools/` and `templates/` are not skills
themselves — they're shared resources the skills' `SKILL.md` files
reference by path.

### 3. Create your personal context folder

This is the folder that holds YOUR data — it is never committed to this
repo. Create it anywhere convenient and keep track of its path, since every
skill's `SKILL.md` refers to it as `context-input/`:

```
context-input/
├── CV-Reference.docx        # your master CV, fully formatted (the single source of truth adapt-cv edits copies of)
├── CL-Reference.docx        # optional: your master cover letter, same idea
├── Candidate-Profile.md     # copy templates/Candidate-Profile-Template.md here and fill it in
└── output/                  # created automatically the first time you run adapt-cv
```

Fill in `Candidate-Profile.md` carefully — it's the one file all three
skills read to know who you are, what your standout achievements are, and
which roles you're realistically targeting. See the template's inline
instructions for what goes in each section.

### 4. Set the scraper path

`search-jobs/SKILL.md` and `job-market-analysis/SKILL.md` both reference
the scraper as `<repo-root>/shared-tools/linkedin_jobs_free.py`. Once you
know where you cloned this repo, either replace `<repo-root>` in those two
files with the actual absolute path, or just tell your agent the path once
at the start of a session — either works, since the instructions are read
fresh each time.

### 5. Pick a Job_Market_Analysis output folder

`job-market-analysis` writes its reports there, and `search-jobs` reads
them from the same place. Any folder works, as long as it's reachable both
by whatever runs the scraper (your machine) and by whatever runs the
aggregation script (your Claude session's shell/sandbox) — a folder inside
a workspace directory your Claude product already has access to is the
simplest choice.

### 6. Configure `adapt-cv` for Notion batch mode (optional)

If you want `/adapt-cv --to-apply` to work (tailor a CV for every "To
Apply" row in Notion automatically), copy the template and fill in your
own values:

```bash
cp adapt-cv/config.example.json adapt-cv/config.json
```

```json
{
  "NOTION_TOKEN": "secret_xxx...",
  "NOTION_DB_ID": "<your Applications database ID>",
  "STATUS_PROP": "Status",
  "TO_APPLY_TAG": "To Apply",
  "CV_CREATED_TAG": "CV created",
  "JD_PROP": "Job Description",
  "COMPANY_PROP": "Company",
  "ROLE_PROP": "Position",
  "URL_PROP": "Job URL"
}
```

**`adapt-cv/config.json` is listed in `.gitignore` on purpose** — only
`config.example.json` (blank) is tracked by this repo, so your real token
can never end up in a commit by accident. GitHub's push protection would
also block a push containing a live Notion token, as a last-resort
backstop, but the gitignore is the actual fix.

If you skip this step, batch mode still works via a one-time fallback that
uses your Notion MCP connector instead of a direct API token — slightly
more manual, but no config file needed.

---

## Setting up your Notion CRM

Both `search-jobs` and `adapt-cv`'s batch mode expect a Notion database
called **Applications** with a specific set of properties. Here's how to
build it from scratch in about 10 minutes.

### Step 1 — Create the Applications database

1. In Notion, create a new page (e.g. "Job Applications") and add a new
   **database** (table) inside it called **Applications**.
2. Add these properties (exact names matter — the skills read them by
   name):

   | Property | Type |
   |---|---|
   | Position | Title (the default title column — rename it) |
   | Company | Text |
   | Location | Text |
   | Job URL | URL |
   | Job Description | Text |
   | Status | **Multi-select** (add options: `To Apply`, `Applied`, `Emailed`, `Interview`, `Offer`, `Rejected`, `Withdrawn`, `Ghosted`) |
   | Source | Select (add options: `LinkedIn`, `Indeed`, `Company Website`, `Other`) |
   | Date Applied | Date |
   | Outreach Email | Text |
   | Keywords Matched | Text |
   | Notes | Text |
   | Salary | Text |

   **Status must be Multi-select, not Select or the built-in Status type.**
   `adapt-cv`'s batch mode needs to add a `CV created` tag alongside `To
   Apply` on the same row, which only a multi-select property allows.

3. (Optional) Add a **Contacts** property of type **Relation**, pointing to
   a second database called **People**, if you want to track named
   recruiter contacts. The default free pipeline in `search-jobs` leaves
   this empty and skips creating a People database entirely — only set
   this up if you plan to add contacts by hand or connect a
   contact-enrichment tool later. See `search-jobs/references/notion-schema.md`
   for the full People schema if you do.

### Step 2 — Create a Notion integration and get a token

1. Go to <https://www.notion.so/my-integrations> and click **New
   integration**.
2. Give it a name (e.g. "claude-skills"), select your workspace, and create
   it.
3. Copy the **Internal Integration Token** (starts with `secret_` or
   `ntn_`) — this is your `NOTION_TOKEN`.
4. Open your Applications database in Notion, click the `•••` menu in the
   top right, go to **Connections**, and add the integration you just
   created. Without this step, the integration can't see the database at
   all, even with a valid token.

### Step 3 — Get your database ID

Open the Applications database as a full page (not inline), and copy the
32-character ID out of the URL:
```
https://www.notion.so/yourworkspace/<THIS-PART-IS-THE-ID>?v=...
```
This is your `NOTION_DB_ID` for `adapt-cv/config.json`, and the
`APPLICATIONS_DB_PAGE_ID` in `search-jobs/references/notion-schema.md`.

### Step 4 — Get your data-source (collection) ID

`search-jobs` uses `notion-create-pages` / `notion-query-data-sources`
against a `collection://...` URL, not the plain page ID. The easiest way to
get this: ask your Claude session (with the Notion connector active) to
run `notion-search` for your database's name — the result includes the
`collection://` URL. Copy it into
`search-jobs/references/notion-schema.md`'s ID block.

### Step 5 — Connect the Notion connector to Claude

If you're using Claude Desktop / Cowork / Claude Code with an MCP Notion
connector, connect it to the same workspace and make sure it's authorized
for the Applications (and People, if used) database. `search-jobs` and
`adapt-cv`'s no-token fallback both rely on this connector being available.

You're done — `search-jobs/SKILL.md`'s "anti-duplicate" logic and
`adapt-cv`'s batch mode will now be able to read and write your Applications
database.

---

## Usage

Once setup is done, typical prompts:

```
/job-market-analysis Hong Kong
/search-jobs Hong Kong
/search-jobs --location "Singapore" --job "software engineer" --results 20
/adapt-cv [paste a job description]
/adapt-cv --cover-letter [paste a job description]
/adapt-cv --to-apply
/adapt-cv --cover-letter --to-apply --isolate
```

Or in plain language: "analyze the job market in Paris," "find me
associate-level cloud roles in Singapore," "tailor my CV for this job
description," "run adapt-cv for every offer I've marked To Apply."

---

## Costs

- **JobSpy / the scraper**: free, no account, no API key, no request
  limits beyond what the job sites themselves rate-limit.
- **Notion**: free tier is enough for personal use.
- **LibreOffice / poppler**: free, open source.
- **The only real cost is your Claude usage** (tokens spent reasoning and
  calling tools), which is why the architecture section above matters —
  every script in this repo exists specifically to keep that the only
  cost.
