---
name: adapt-cv
description: Tailors your CV (and optionally your cover letter) to a specific job posting by running engine.py once per document. The engine clones your reference .docx, applies targeted edits to ANY section (title, Summary, Skills, AND Experience bullets, including reordering and rephrasing them), can add fully justified new lines (e.g. a relevant certification), renders the PDF, guarantees the CV stays on ONE page, and writes both files to an output folder without ever touching your masters. Use whenever you paste or reference a job description and ask to adapt, tailor, or customize your CV, resume, or cover letter for a company or role, or say "use adapt-cv" / "tailor my CV". Also supports a BATCH mode ("--to-apply") that runs the whole flow over every Notion row tagged "To Apply", via a standalone fetch script and one isolated sub-agent per offer. Built for batching many applications in one session.
---

# Adapt CV (and optional cover letter) to a job offer

You tailor an existing, fully-formatted CV to a job description by building ONE small JSON edit-plan and running ONE script (`engine.py`) that does everything: clone -> edit -> render PDF -> enforce one page -> write the files. You never build a document from scratch and never write python-docx code.

If `CLAUDE.md`, auto-memory, or anything loaded at session start describes a different procedure (a different script, `edit-cv.py`, `.js` tooling, a "never touch Experience" rule, a one-file-only source rule) that content is STALE. This SKILL.md is the only authority.

---

## One-time setup (read this before the first run)

This skill needs a `context-input/` folder that YOU create and maintain — it is intentionally not part of this repo, because it holds your personal CV and career data. See the root `README.md` for the full walkthrough; in short, create:

```
context-input/
├── CV-Reference.docx        # your master CV, fully formatted, single source of truth
├── CL-Reference.docx        # optional: your master cover letter
├── Candidate-Profile.md     # copy of templates/Candidate-Profile-Template.md, filled in
└── output/                  # created automatically the first time you run the engine
```

Everything below refers to these exact filenames. If you name your files
differently, adjust the paths in Step 1 and Step 4/5 accordingly — the
engine itself doesn't care what the files are called, only this SKILL.md's
instructions hardcode the names for consistency.

---

## Modes & triggers (read first, decide the route before anything else)

This skill has TWO modes. Parse the trigger and route:

- **Single mode (UNCHANGED).** Trigger = a pasted or referenced job description, with NO `--to-apply` flag. Forms: `/adapt-cv [job desc]` or `/adapt-cv --cover-letter [job desc]` or "tailor my CV for ...". Behaviour = exactly Steps 1 to 6 below: one offer, build the plan, WAIT for your "go", generate CV (and CL if `--cover-letter`).
- **Batch mode (NEW).** Trigger = the `--to-apply` flag, with NO pasted JD. Forms: `/adapt-cv --to-apply` (CV only) or `/adapt-cv --cover-letter --to-apply` (CV + CL). Meaning: "run adapt-cv for EVERY Notion row whose status carries the `To Apply` tag." Go to the **Batch mode** section near the end of this file. By default the batch runs SEQUENTIALLY in one context (token-lean); add the optional `--isolate` flag to force one fresh sub-agent per offer (stronger isolation, more tokens).

`--cover-letter` is optional in BOTH modes (present = also generate the CL; absent = CV only).

**Routing rule:** if the trigger contains `--to-apply` -> Batch mode section. Otherwise -> single mode (Steps 1 to 6). Single mode is not modified in any way by the existence of batch mode.

---

## Token discipline (read first, this skill is built for 10-15 CVs per session)

- **Read the source content files ONCE per session** (on the first CV). For every later CV in the same session, reuse what is already in context.
- **ONE engine call per document.** Do not run intermediate renders.
- **Never read rendered images.** The engine returns `"pages": 1` as text, trust it. Do not screenshot, do not `Read` a PNG, do not open the PDF visually.
- **Never dump `document.xml` or full `pdftotext` into context.** The engine prints a compact JSON status only.
- **Verification is the status line, not your eyes:** `warnings: []` means every edit landed; `pages: 1` means it fits. Only investigate when `warnings` is non-empty or `overflow: true`.
- The few pre-flight checks below (zip validity, run-split safety, apostrophe codepoint) are cheap one-liners. Run the master/zip check ONCE per session; run the per-string checks only when a swap looks risky.

See the root `README.md` for a worked-through estimate of what this costs in practice (order of magnitude, per CV and per batch) and why the engine's JSON-in/JSON-out design is what keeps it cheap.

---

## Hard constraints (apply throughout, single AND every batch offer)

- **Aggressive, interview-defensible tailoring (the "80/20" rule).** The goal is to maximise match with the JD and land the first interview. Push the framing to its strongest defensible version: amplify scope and impact, present transferable skills as direct hands-on experience, and where the JD asks for something adjacent, anchor the new claim to a REAL project/tech/environment from your own work history so it has a true anchor. Target roughly 70% verifiable truth, up to ~30% strategic stretch driven by the specific job description. Staying too close to the source files is a FAILURE MODE: if the adapted CV reads almost like the master, it wasn't tailored hard enough. Every run must visibly rewrite the Summary and rework the Experience bullets toward the JD, not just reorder them.
  - **Cover EVERY hard requirement in the JD.** For each must-have / required skill, tool, framework, or domain the posting lists, the CV MUST claim the candidate can do it, phrased as owned hands-on experience and anchored to a real environment from `Candidate-Profile.md`. Do NOT soften a required skill into "exposure to" or "familiarity with" — state it as a capability the candidate has. If it is a genuine gap, still claim it and add the interview-prep note so the candidate can learn and rehearse it before the interview. The only claims never to make are the Hard limits below (degree, named cert, employer, clearance, visa status).
  - **Every stretch must be bluffable and pre-prepared.** A claim only goes on the CV if the candidate could plausibly defend it in an interview after a short briefing. Anchor each stretch to a real system, stack, or situation from `Candidate-Profile.md` so the story is coherent and questions can be answered.
  - **For every stretch you add, output a one-line "interview-prep note"** in the plan (see Step 3) so the candidate knows exactly what story they're committing to and can rehearse it. No un-briefed stretches.
  - **Hard limits even when stretching:** never fabricate a degree, a named certification the candidate doesn't hold/isn't pursuing, an employer they never worked for, a security clearance, or legal/visa status. Never invent a *named* third-party client or a verifiable external metric (a public benchmark, a named customer's revenue). Keep metrics plausible and defensible, not round-number fantasy.
- **Never overwrite the masters.** Read from `context-input/`; write ONLY versioned output files (see Step 4 for the /tmp-then-copy rule). The engine refuses to run if the reference is missing/corrupt.
- **One page, always.** The engine renders the PDF and auto-purges trailing empty paragraphs to fit. If it still reports `overflow: true`, shorten the plan and re-run, never ship a 2-page CV.
- **CV TITLE = THE JD'S EXACT JOB TITLE (MANDATORY, NON-NEGOTIABLE).** The role title printed under the candidate's name MUST be the *verbatim* job title from the job description, character-for-character. This is the single most important ATS lever: the ATS reads the CV and runs a keyword-match score, and if the title under the name does not match the JD's title, the CV can be auto-rejected before a human ever sees it. Do NOT paraphrase, shorten, "improve", or synonym-swap the title. Copy it exactly.
  - **The ONLY thing you strip is high seniority.** If the JD title carries a senior tier the candidate doesn't hold (Senior, Sr., Lead, Principal, Staff, Head of, Director, Manager, Chief), remove ONLY that seniority word and keep the rest verbatim. Examples: "Senior Software Engineer" -> "Software Engineer"; "Lead Data Engineer" -> "Data Engineer"; "Principal Cloud Architect" -> "Cloud Architect".
  - **Keep junior tiers as-is.** Junior, Associate, Graduate, Entry-level, Trainee, Intern and similar low tiers are KEPT verbatim (e.g. "Associate Software Engineer" stays "Associate Software Engineer"). When in doubt about whether a word is "high seniority", keep it.
- **No seniority inflation.** Don't claim a seniority the candidate doesn't have (Senior, Lead, Principal, Staff, Head of). "Senior X" becomes "X". You MAY mirror neutral true framing ("experienced", "X years") when accurate.
- **No em (—) or en (–) dash used as a separator or connector, anywhere in the CV or the CL.** Use a comma or a conjunction. The only exception is a dash that is part of an official proper name (e.g. an official certification title); even then, the separator you add around it must be a comma.
- Experience edits are ALLOWED (reorder + rephrase), see Step 2b.

---

## Step 1 — Read the source (ONCE per session), then parse the JD

On the first CV of the session, read for content:

    context-input/CV-Reference.docx      (canonical phrasing baseline — the exact strings live here; open it via the run-split checks in Step 4, not by reading raw XML into context)
    context-input/Candidate-Profile.md   (identity, journey, key achievements/"hooks", stack, target roles — your honest fact source for tailoring)

NEVER read anything in `output/` FOR CONTENT (those are previous tailored CVs, wrong title, stale keywords). The ONLY exception is the corrupted-master fallback in Step 4, where a prior output is used as a structural reference, not for content.

Then extract from the JD and show in chat (compact): company; role title (raw) and adapted title (seniority stripped); role type (it sets tone); must-have keywords ranked by JD prominence.

## Step 2 — Plan the edits (Pareto, honest, scoped)

**2a. Title + Summary + Skills.** Pick the top 3-5 keywords that are JD-required, missing, and truly supported. For each keyword added to a Skills line, swap out the least JD-relevant term on that line; prefer similar character length to keep wrapping intact.

**Summary, mandatory style rules:**
- The summary is **personal and narrative**: it tells the trajectory (from `Candidate-Profile.md`'s "career journey" section) and shows the pivot to the targeted role is logical and intentional.
- **Never put a metric in the summary** (numbers belong to the Experience bullets).
- **Never an em (—) or en (–) dash** in the summary (nor anywhere else in the CV); use a comma or a conjunction.
- Suggested structure: sentence 1 = identity (who the candidate is, background); sentence 2 = why the pivot to the targeted role is logical; sentence 3 = clear intent + geography.
- The recruiter must never wonder "why this change?" — the answer must already be in the summary.

**2b. Experience bullets (in scope, and primary place to apply the 80/20 stretch).** Moves available on EVERY experience block:
- *Reorder*: lead with the bullet that is BOTH most JD-relevant AND quantified. Never open with a buzzword-heavy but metric-free bullet. Keep the strongest achievement high; push the weakest last.
- *Rephrase*: re-word an existing bullet to surface JD vocabulary, keeping the core fact intact.
- *Stretch (per the 80/20 rule in Hard constraints)*: amplify scope/impact, convert transferable exposure into hands-on phrasing, and add up to one or two JD-driven bullets that are anchored to a real environment from `Candidate-Profile.md` so they stay bluffable. Each stretched/added bullet gets an interview-prep note in the plan.

**Every experience block is eligible for a full rewrite, not just reordering.** When the JD targets a role adjacent to what a given block actually covers, you MAY rebuild that block's bullets from scratch: construct concrete, plausible bullets (tech stack, problem, decision, metric) shaped by the job description, kept consistent with the REAL environment described for that role in `Candidate-Profile.md` (its stack, its domain, its real deliverables) so the candidate can defend it. If `Candidate-Profile.md` has little detail on a given past role, generate the bullets directly from the JD using the 80/20 rule, anchored to whatever real facts exist for that block (employer type, tech stack, timeframe). Never invent a new, unlisted employer or a disconnected project to hang a stretch on — always anchor to a block that genuinely exists in the candidate's history. You may make bullets moderately longer if the role demands it and the page still fits.

**2c. New lines (gated).** Add a line only when it clearly earns its place and is honest.
- **Certifications: add this line ONLY if the candidate explicitly asks for it in their request.** If they say nothing about certifications, do NOT add it, even if the JD calls for certifications. (In batch mode this is interpreted from the original `/adapt-cv` request: no explicit certification ask = never add the line.)
- When asked, the Certifications line goes **inside the SKILLS section**, anchored to a heading that literally exists in your `CV-Reference.docx` (e.g. a subsection title like "Architecture & Methods" or whatever your own CV actually uses — check your document, don't assume). Format:
  `{"anchor": "<a heading string copied verbatim from your CV>", "label": "Certifications:", "body": " [cert official name], in progress, expected [date]"}`
  (The body starts with a space. Use a comma before "in progress", not a dash. A dash inside the cert's official name is allowed.)

## Step 3 — Show the plan and WAIT

Output first:

> Scope check: edits follow the 80/20 rule, ~80% traces to real facts and any stretch is anchored to a real block in Candidate-Profile.md and listed in the Bluff brief below so it stays interview-defensible. Masters untouched; output is a versioned file. Target: one page.

Then show a compact plan (Title / Summary / Skills swaps / Experience reorder+rephrase+stretch / Add line if any). In the Title line, show the JD's raw title and the adapted title and confirm they are identical except for any stripped high-seniority word.

**Interview-prep notes (mandatory whenever you stretch or invent).** Under the plan, add a short "Bluff brief" block: one bullet per stretched/added claim, each saying in one line what story the candidate is committing to and the one fact/number they must remember to defend it. If there are zero stretches, write "Bluff brief: none (all edits trace to source)". Do not proceed until the candidate says go.

> NOTE (batch mode only): in batch mode the per-offer "wait for go" gate is removed; one global confirmation at the start of the batch covers every offer. Everything else in this step still runs (the plan and the Bluff brief are still produced for each offer). See the Batch mode section.

## Step 4 — On "go": pre-flight, build plan.json, run engine.py ONCE

Paths use the current session's sandbox mounts (see your "Shell access" section). `<context-mnt>` = mount of the `context-input` folder. `<skill-mnt>` = mount of THIS skill's own folder (where `SKILL.md` and `engine.py` sit).

**Pre-flight A — master integrity (run once per session).** Confirm the reference is a valid .docx:

    python3 -c "import zipfile; print(zipfile.ZipFile('<context-mnt>/CV-Reference.docx').namelist()[:3])"

If this raises (BadZipFile / not a zip), the master is corrupt or open in Word/LibreOffice. **Fallback if the master is corrupt:** pick the most recent file in `output/` that still shows a header line in NATIVE run-split (several `<w:t>` nodes for one paragraph), which proves the engine never collapsed that line. Detect it:

```
python3 - <<'EOF'
import zipfile, re, glob, os
cands = sorted(glob.glob('<context-mnt>/output/CV-*.docx'), key=os.path.getmtime, reverse=True)
for f in cands:
    try: xml = zipfile.ZipFile(f).read('word/document.xml').decode()
    except Exception: continue
    for p in re.findall(r'<w:p\b.*?</w:p>', xml, re.S):
        txts = re.findall(r'<w:t[^>]*>(.*?)</w:t>', p, re.S)
        if len(txts) > 1:
            print('USE_AS_REFERENCE', f); break
    else: continue
    break
EOF
```

Use that file as `reference` instead of the master. If the master is valid, use it normally.

**Pre-flight B — run-split safety of every swap.** DANGER, run-split rebuild breaks formatting. When a swap's `old` text is spread across several `<w:t>` nodes, the engine rebuilds the WHOLE paragraph as a single run and applies the FIRST run's formatting to everything. That destroys:
- **Experience header lines** (company / role / dates): they lose the right-aligned tab, so the date collapses onto the location.
- **Skills lines**: they lose the bold-label / normal-body split, so the entire line turns bold.

Rules:
- For a Skills line, always target a substring that sits inside a SINGLE non-bold `<w:t>` node (e.g. text right after a separator character) rather than the whole line.
- For an Experience header line, avoid swapping it at all; if a different reference already has the right header text, use that reference instead.
- Before adding any swap, verify it is a direct (safe) replacement, not a run-split fallback:

      python3 -c "import zipfile; xml=zipfile.ZipFile('<ref>.docx').read('word/document.xml').decode(); print('safe' if 'OLD_STRING' in xml else 'DANGER run-split')"

  `safe` = the string exists contiguously (single-run), the engine does a clean replace. `DANGER` = it is split, do NOT swap it as-is; pick a single-node substring instead.

**Pre-flight C — apostrophes / encoding.** Never type a literal `'` inside an `old` string that contains an apostrophe; the document may use a curly apostrophe (U+2019) instead of a straight one (U+0027), or vice-versa, and a mismatch silently fails the swap. Build swap strings with an inline Python script (`python3 - <<'PYEOF' ... PYEOF`) and `json.dump(..., ensure_ascii=False)`. Use `chr(0x27)` (straight) or `chr(0x2019)` (curly) for the apostrophe, choosing whichever the document actually contains. To find out which:

    python3 -c "import zipfile,re; xml=zipfile.ZipFile('<ref>.docx').read('word/document.xml').decode(); i=xml.find('SOME_WORD_NEAR_AN_APOSTROPHE'); print([hex(ord(c)) for c in xml[i:i+8]])"

Never guess the codepoint.

**Build the plan** and write it to `/tmp/plan.json`:

```json
{
  "reference": "<context-mnt>/CV-Reference.docx",
  "output":    "/tmp/CV-[Company]-[YYYY-MM-DD].docx",
  "swaps":   [ {"old": "<exact, single-node string from the ref>", "new": "<new text>"} ],
  "remove":  [ "<unique substring of a bullet to delete>" ],
  "add_after": [ {"anchor": "<heading string from your CV>", "label": "Certifications:", "body": " ..."} ],
  "reorder": { "block": [ "<substr of bullet to place 1st>", "<...2nd>" ] },
  "pdf": true,
  "max_pages": 1
}
```

**Always write `output` to `/tmp/` first**, never directly into the workspace (the sandbox cannot delete/overwrite files in mounted workspace folders, so a direct write raises PermissionError on re-runs). Run:

```
python3 "<skill-mnt>/engine.py" /tmp/plan.json
```

Then COPY both products into the workspace output folder:

```
cp /tmp/CV-[Company]-[YYYY-MM-DD].docx "<context-mnt>/output/CV-[Company]-[YYYY-MM-DD].docx"
cp /tmp/CV-[Company]-[YYYY-MM-DD].pdf  "<context-mnt>/output/CV-[Company]-[YYYY-MM-DD].pdf"
```

(Batch mode writes to `<batch-dir>/output/` instead of `context-input/output/`; the /tmp-then-copy rule is identical.)

Read the JSON status (one line). `warnings: []` + `pages: 1` = success. `warnings` non-empty -> a swap/anchor string didn't match (fix spacing / apostrophe codepoint, re-run). `overflow: true` -> shorten in this order until it fits: tighten the Summary to ~3 lines, then shorten the longest reordered bullet, then `remove` the single weakest bullet; re-run.

Do NOT share yet: first run the Step 6 proofread + scoring gate. Only after both scores are ≥16/20 do you share the workspace files (docx + pdf) with `present_files` (or your platform's equivalent file-sharing step). Do not read the rendered files visually first.

## Step 5 — Cover letter (only if requested)

The CL must end up as **both .docx AND .pdf**, exactly like the CV (set `"pdf": true`, `"max_pages": 99`). Reference = `context-input/CL-Reference.docx`. Same /tmp-then-copy rule.

**Length target (MANDATORY, do not ship a short CL).** Short cover letters read as lazy and unprofessional. The body (the tailored paragraphs, excluding header/signature boilerplate) must land close to these targets — never significantly under:
- Words: ~211 (acceptable band 200-225)
- Characters without spaces: ~1341
- Characters with spaces: ~1553
- Sentences: ~8
- Paragraphs: **exactly 4**
- Reading time: ~0m 51s

Structure the 4 paragraphs as: (1) strong direct opening hook tying the candidate to the role/company, (2) most relevant proof/experience mapped to the JD's top needs, (3) second proof + the logical pivot narrative + culture/motivation fit, (4) confident close with call to action. Before rendering, count the body words with a quick `python3` one-liner; if under 200, expand paragraphs 2-3 with more JD-mapped specifics (and apply the same 80/20 stretch as the CV, anchored and bluffable) until it hits the band.

**Read the EXACT placeholders first.** The real placeholders in your `CL-Reference.docx` may differ from any assumed list (e.g. `"Dear [Hiring Manager Name if we know it],"`, `"[2 to 3 paragraphs tailored to what's asked in the job description.]"`). Dump them, then copy the exact strings into `old`:

```python
python3 - <<'EOF'
import zipfile, re
xml = zipfile.ZipFile('<CL_path>').read('word/document.xml').decode()
for p in re.findall(r'<w:p\b.*?</w:p>', xml, re.S):
    t = ''.join(re.findall(r'<w:t[^>]*>(.*?)</w:t>', p, re.S)).strip()
    if t: print(repr(t))
EOF
```

Never assume the placeholder format.

**Opening tone.** The opening hook must be positive and solution-oriented. Never frame the candidate's work as failure or as a problem, even when the proof point quantifies a gap. Always frame as discovery and solution: "I spent X quantifying Y and designing Z" rather than "I build systems that fail". The opening must be formal, direct, and convincing from the first line. No em/en dashes (Hard constraints).

Show the CL plan, WAIT for go, run the engine once, copy docx+pdf to the output folder, then run the Step 6 gate before sharing. (Batch mode only: no per-offer go gate, the single global confirmation covers it.)

## Step 6 — Final proofread + ATS / JD-fit scoring (MANDATORY, every document)

After the files are rendered and before you finish, run a fast quality pass on each document you produced (CV always; CL if one was made). This is a quick read-through, not a re-render. Extract the text once (`pdftotext` on the produced PDF, or reuse the strings you already built) and check:

- **Proofread:** spelling, grammar, doubled words, broken spacing, a stray em/en dash, a wrong company name left over from a previous version, a date typo, a title that is NOT the JD's exact title. Fix anything found (re-run the engine if a rendered string is wrong).
- **JD keyword coverage:** list the JD's top must-have keywords and confirm each appears in the CV (title, summary, skills, or bullets). Flag any high-priority keyword still missing.

Then give each document **two scores out of 20**:
1. **ATS match score /20** — how strongly the ATS keyword-matcher will rank it (title match, keyword density, section coverage).
2. **Recruiter / JD-fit score /20** — how compelling a human recruiter finds it against this specific JD.

Present them in one short verdict block per document, e.g.:
> **CV — ATS 18/20 · JD-fit 17/20.** Title matches the posting exactly, hit [N] of [M] must-have keywords (X, Y, Z), summary mirrors the JD's language. High chance the ATS surfaces it and the recruiter bites.

**Hard gate: every document must score at least 16/20 on BOTH scores.** If either score is below 16, do NOT finish: identify the weakness (missing keywords, weak title match, thin bullets, CL too short), apply more JD-aligned tailoring / 80/20 stretch, re-run the engine, and re-score until both are ≥16. Only then share the files (single mode) or report success to the orchestrator (batch mode).

---

## Batch mode (`--to-apply`) — orchestration

Reached only when the trigger contains `--to-apply`. You are the **ORCHESTRATOR**. Your job is to fan the work out, never to tailor a CV yourself. You never load a full JD into your own context: you only handle the manifest (short metadata) and the compact statuses sub-agents return.

`--cover-letter` carries through: if it is present on the batch trigger, every offer gets a CV + CL; if absent, every offer gets a CV only.

This mode requires the Notion CRM described in `search-jobs/references/notion-schema.md` and the root README's setup guide — specifically an "Applications" database with a multi-select status property carrying a `To Apply` tag.

### B1. Fetch the "To Apply" rows (one cheap call, autonomous script)

Pick a NEW dedicated batch folder for this run: `<batch-dir>` = `<output-base>/Batch_Applications/<YYYY-MM-DD>/`. Then run the standalone fetcher (it calls the Notion API directly, so the raw row JSON never enters your context):

```
python3 "<skill-mnt>/fetch_to_apply.py" --batch-dir "<batch-dir>"
```

- The script reads `config.json` sitting next to it (`NOTION_TOKEN`, `NOTION_DB_ID`, and the property/tag names: `STATUS_PROP` default "Status", `TO_APPLY_TAG` default "To Apply", `CV_CREATED_TAG` default "CV created"). Environment variables of the same name override the file. The status property must be a **multi-select** (so it can hold "To Apply" and "CV created" at the same time). See the root README for how to fill this config from your own Notion setup.
- It writes `<batch-dir>/work/job_NN_<Company>.md` (one clean file per offer, metadata + JD only), creates `<batch-dir>/output/`, writes `<batch-dir>/batch_manifest.json`, and prints ONLY a compact summary: `{"fetched":N,"skipped":M,"total":T,"manifest":"..."}`.
- Rows with an empty/missing JD are marked `skipped` in the manifest (they do not stop the batch). Duplicate company names are safe (the `NN` index keeps filenames unique). Notion pagination (>100 rows) is handled.
- **Read the manifest file, not the raw rows.**

**Fallback if no token is configured.** If the script prints `{"error":"no_token", ...}`, do NOT loop a Notion connector call per offer. Instead make ONE MCP connector call (e.g. `notion-query-data-sources` on the database), then write the SAME clean files yourself: one `work/job_NN_<Company>.md` per "To Apply" row + a `batch_manifest.json` with the same shape (`{index, company, role, jd_file, page_id, url, status, reason?}`). From there the flow is identical.

### B2. One global confirmation

Show the list of N offers found (company + role, and which are `skipped` and why). Ask for ONE global "go". In batch mode the per-offer "wait for go" gates of Step 3 and Step 5 are REMOVED; this single approval covers every offer. This is the ONLY relaxation; every Hard constraint and the Step 6 gate still apply to each offer.

### B3. Process each offer (SEQUENTIAL by default, token-lean)

**Default (no `--isolate`): one shared context.** This is the recommended, token-economical path. Read the source files ONCE (Step 1), then loop over the `status == "ok"` manifest entries IN THIS SAME context:
- For each offer, read ONLY that offer's JD file (`<batch-dir>/work/job_NN_<Company>.md`). Do NOT re-read the source files, reuse what is already in context.
- Run the FULL single-mode flow (Steps 1 to 6) for that one offer: build the plan, NO per-offer go gate, honour every Hard constraint (exact JD title, no seniority inflation, no em/en dash, 80/20 + Bluff brief, certifications only if the original request asked), enforce one page, pass the Step 6 scoring gate (>=16/20 on BOTH scores, with retries). Write docx+pdf into `<batch-dir>/output/` via the /tmp-then-copy rule.
- **Context hygiene between offers (mandatory):** treat each offer as fully independent. Base every CV ONLY on the canonical source files + the CURRENT offer's JD. Never carry over the previous offer's company, keywords, bullets, or stretch stories. The engine reclones the master .docx from scratch every time, so the document itself can never be contaminated, you only have to keep your own reasoning clean.
- After each offer: keep a compact status line (company, files produced, ATS score, JD-fit score, warnings, page_id). On success run the B4 writeback, then move to the next offer.

Why it is cheap: the fixed cost (skill instructions + source files) is paid ONCE, not once per offer. For N offers you pay roughly `1 x fixed context + N x (one JD + the tailoring reasoning)`.

**Optional (`--isolate`): one sub-agent per offer.** Use this ONLY for large batches or if you actually observe cross-offer bleed in the default mode. When `--isolate` is present, for each `status == "ok"` entry delegate to a sub-agent with a fresh context. Give it exactly: the path to THIS offer's JD file, the skill folder (`<skill-mnt>`) and source location (`context-input/`), whether `--cover-letter` is on, the output target `<batch-dir>/output/`, the `page_id`, and the instruction to run the full single-mode flow (Steps 1 to 6, no go gate, all Hard constraints, one page, Step 6 gate >=16/20) and return ONLY a compact status (no CV text). This costs more tokens, each sub-agent re-reads the sources and re-derives the skill in its own context, that is the accepted price of hard isolation.

In BOTH modes the orchestrator never dumps full JDs or CV text, only the manifest metadata and the per-offer compact statuses.

### B4. Writeback on success

When an offer reports success (both scores ≥16 and files produced), tag that Notion row:

```
python3 "<skill-mnt>/fetch_to_apply.py" --mark-created <page_id>
```

This appends `CV created` to the multi-select status WITHOUT removing `To Apply`. It is idempotent: if `CV created` is already there it prints `{"status":"noop"}` and changes nothing. Only tag offers that genuinely succeeded, never a failed or skipped one. (If you used the MCP-connector fallback in B1 because no token was configured, do the writeback with a single `notion-update-page` call that adds `CV created` to the multi-select instead.)

### B5. Partial failure handling

If an offer fails (unresolved warnings, irreducible overflow, or score < 16 after the Step 6 retries), do NOT block the batch: mark it FAILED in the recap, do not tag it `CV created`, and continue with the next offer.

### B6. Final recap + share

Emit ONE recap table only: `Offer | Files | ATS / JD-fit | Status`. Then share every produced file in a single batch. The orchestrator does not open or read the rendered files.

---

## Environment & troubleshooting

- The engine runs in the sandbox via shell access. It needs `libreoffice` (PDF + page count) and `pdfinfo`/`pdftotext` (poppler). No pip packages required (pure stdlib). If `libreoffice` is absent it still writes the `.docx` and returns `"pages": null`; warn the candidate that one page is then not guaranteed.
- `fetch_to_apply.py` is also pure stdlib (urllib) and needs no pip packages. It never prints raw Notion JSON, only the compact summary / status lines.
- `"error": "reference is not a valid .docx ..."` or the Pre-flight A check raises -> master open in Word/LibreOffice (a `~$...docx` lock exists) or corrupt -> close it, or use the corrupted-master fallback (Pre-flight A).
- `fetch_to_apply.py` prints `{"error":"no_token"}` -> config.json is missing/placeholder and no env vars are set -> use the B1 MCP-connector fallback (single call), or fill config.json.
- `fetch_to_apply.py --mark-created` prints `{"error":"not_multi_select"}` -> the status property is not a multi-select after all -> stop and report it (the writeback would overwrite `To Apply`); switch to a dedicated second property before continuing.
- Never edit this skill's files or write python-docx code to "get past" a problem. The engine, the fetch script, and this file are the whole toolset.

After the files are ready, share them and stop. One short line, no recap (single mode); in batch mode the recap table is the exception.
