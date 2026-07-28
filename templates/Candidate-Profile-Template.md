# Candidate Profile — Template

This file is the single source of truth about **you** that all three skills
(`adapt-cv`, `search-jobs`, `job-market-analysis`) read from. Fill it in once,
save it as `Candidate-Profile.md` inside your own `context-input/` folder
(see the root `README.md` for the full folder layout), and every skill will
use it automatically — you never re-explain your background in a prompt.

Keep it factual. `adapt-cv` uses it as the anchor for honest, defensible
tailoring; `search-jobs` pulls your "hooks" for outreach emails;
`job-market-analysis` uses it to judge which roles are realistic for you.

Delete every instruction line in `[brackets]` once you've replaced it with
your own content.

---

## Identity

- **Name:** [Your full name]
- **Current role:** [Title] at [Company], [City] [e.g. "on a work visa" / "local hire" if relevant]
- **Experience:** [~N years in Y field]
- **One-line positioning:** [The single sentence that describes what makes your
  profile distinctive — e.g. "engineer who also runs client-facing demos and
  scoping calls," or "backend engineer who has shipped 3 production ML
  pipelines." This becomes the throughline of your CV summary and your outreach
  emails.]
- **Contact:** [email] · [LinkedIn URL] · [portfolio/GitHub if relevant]
- **Languages:** [native language, fluency of others]
- **Work authorization:** [citizen / permanent resident / need visa sponsorship
  / have a specific visa that's expiring on DATE, etc. Be precise — this
  directly filters which job postings and which countries are worth pursuing.]

## Career journey

[2-4 sentences narrating your path chronologically: where you started, the
pivots you made and why, and where you're headed next. This is the backbone
of the CV summary's "trajectory" paragraph — the goal is that a recruiter
reading it never has to wonder "why did they change direction?"]

## Key achievements ("hooks")

List 4-8 concrete, quantified accomplishments. Each one should be reusable as
a CV bullet, an interview story, AND an outreach-email opening line. For each,
note which kinds of roles it's most relevant to — this is what `search-jobs`
uses to pick the right hook per offer.

- **[Short title, e.g. "Cut deployment time from 2 days to 40 minutes"]:**
  [1-3 sentences: the situation, what you did, the concrete result/metric.]
  → Best for: [role types this proves, e.g. "DevOps, platform engineering,
  technical presales"]
- **[Achievement 2]:** [...]
  → Best for: [...]
- **[Achievement 3]:** [...]
  → Best for: [...]

[Add as many as you genuinely have. Quality over quantity — three sharp,
quantified stories beat ten vague ones.]

## Technical / professional stack

[Everything you can credibly claim hands-on experience with, grouped
however makes sense for your field — e.g. Languages / Frameworks / Cloud &
Infra / Domain tools / Soft-skill or delivery capabilities. This is the pool
`adapt-cv` draws from when swapping in JD-required keywords.]

- Languages: [...]
- Frameworks & platforms: [...]
- Infrastructure / cloud: [...]
- Domain-specific tools: [...]
- Other relevant capabilities (e.g. client-facing discovery, PoC scoping,
  technical writing, presenting to executives): [...]

## Target roles and priority tiers

Define your own feasibility tiers. This is what `job-market-analysis` and
`search-jobs` use to decide what to search for and how to rank results —
there is no universal P1/P2/P3, it depends entirely on your background.

- **Tier 1 (realistic now):** [role families you can credibly land today,
  given your years of experience and stack — e.g. "Backend Engineer,
  Solutions Engineer, Technical Account Manager"]
- **Tier 2 (stretch, worth trying):** [roles that usually ask for a bit more
  seniority than you have but where you have a real shot — e.g. "Presales
  Engineer (mid-level), Senior-labeled roles open to ~3 years"]
- **Tier 3 (unlikely but sometimes real):** [roles that are a reach but do
  occasionally hire at your level — e.g. "Solutions Architect (entry/associate
  labeled only)"]
- **Roles to exclude:** [seniority tiers or role types clearly out of reach
  right now — e.g. "Staff/Principal/Lead/Director titles, anything requiring
  5+ years"]

## Geography

- **Primary target:** [city/region you're searching first]
- **Secondary targets, in order:** [where you'd expand next]
- **Hard constraints:** [visa sponsorship required? relocation budget?
  remote-only? languages required locally?]

## Feasibility notes (used as a fallback when no market analysis exists yet)

When a skill can't find a market-analysis file for a city and needs to
sanity-check a role you've asked about, it should reason using the tiers
above. Optionally, spell out a few explicit calls here so every skill applies
them consistently, e.g.:

- Realistic now: [...]
- Stretch: [...]
- Not realistic yet, propose this close alternative instead: [X → Y]
