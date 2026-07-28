# Role Taxonomy — role families for the market analysis

This file drives TWO things:
1. **Scrape queries** (which titles to search for on LinkedIn).
2. **Normalization** of raw titles into "families" for aggregation
   (`scripts/aggregate.py` reads the same rules).

Keep this file in sync with `scripts/aggregate.py`: the `family` values
below must match the keys of the script's `FAMILIES` dictionary.

**This is an example taxonomy**, built around a technical, client-facing
career track (solutions engineering / presales / technical consulting)
plus a general tech-market scan. It's a solid, broadly useful starting
point, but the whole point of `Candidate-Profile.md`'s "target roles and
priority tiers" section is that YOUR tiers may look nothing like the
defaults here. Edit the search terms, add/remove families, and change the
default Tier column freely to match your own target roles — just keep
`aggregate.py`'s `FAMILIES`/`BROAD_FAMILIES` dictionaries matching whatever
you change here.

---

## A. NICHE layer — your target families (Tier 1/2/3 priority)

For each family: `family` (canonical key), the **search terms** to send to
the scraper (`--search`), and the **synonyms** that should match during
normalization.

| family | Search terms | Synonyms to normalize | Default tier |
|---|---|---|---|
| `TAM` | "Technical Account Manager", "Technical Account Management" | tam, technical account | Tier 1 |
| `CustomerEngineer` | "Customer Engineer", "Customer Success Engineer", "Customer Success Manager technical" | customer engineer, customer success engineer, sales engineer (cloud), field engineer | Tier 1 |
| `DeliveryConsultant` | "Delivery Consultant", "Professional Services Consultant", "Professional Services Engineer" | delivery consultant, professional services, ps consultant, engagement manager (delivery) | Tier 1 |
| `ImplementationConsultant` | "Implementation Consultant", "Implementation Engineer", "Onboarding Engineer", "Integration Consultant" | implementation, onboarding engineer, integration consultant | Tier 1 |
| `ITConsultant` | "IT Consultant", "Technology Consultant", "Application Consultant", "ERP Consultant" | it consultant, technology consultant, application consultant, erp consultant, functional consultant | Tier 1 |
| `PresalesEngineer` | "Presales Engineer", "Pre-Sales Consultant", "Sales Engineer", "Solution Consultant" | presales, pre-sales, sales engineer, solution consultant, solutions consultant | Tier 2 |
| `SolutionsArchitect` | "Solutions Architect", "Solution Architect", "Cloud Solution Architect" | solutions architect, solution architect, sa (cloud), cloud architect | Tier 3 |
| `SolutionsEngineer` | "Solutions Engineer", "Solution Engineer" | solutions engineer, solution engineer, se (presales) | Tier 2 |
| `CloudEngineer` | "Cloud Engineer", "Cloud Consultant", "Cloud Service Engineer", "Site Reliability" | cloud engineer, cloud consultant, devops, sre, platform engineer | Tier 1 |
| `SoftwareEngineer` | "Software Engineer", "Backend Engineer", "Fullstack Engineer" | software engineer, swe, backend, fullstack, full stack, developer | Tier 1 (technical fallback) |
| `AppModernization` | "Application Modernization", "Migration Consultant", "Modernization Consultant" | modernization, migration consultant, app modernization, legacy modernization | Tier 1 |

> The tiers above are **defaults**. A posting's real tier also depends on
> the detected seniority (see `output-template.md` -> tiering rule). A
> `SolutionsArchitect` labeled **entry/associate** can move up to a direct
> target; a `TAM` labeled Mid-Senior stays Tier 1 by family but "stretch" by
> seniority.

---

## B. BROAD-SCAN layer — general tech-market pulse

Purpose: answer "what roles are most in demand **overall**," beyond your
own niche. More generic queries, volume only (no Tier curation).

| family | Search terms |
|---|---|
| `SoftwareEngineer_broad` | "Software Engineer", "Developer" |
| `DataEngineer` | "Data Engineer", "Data Scientist", "Analytics Engineer" |
| `DevOpsSRE` | "DevOps Engineer", "Site Reliability Engineer", "Platform Engineer" |
| `AIMLEngineer` | "Machine Learning Engineer", "AI Engineer", "GenAI Engineer" |
| `ProductManager` | "Product Manager", "Technical Product Manager" |
| `CyberSecurity` | "Security Engineer", "Cybersecurity", "SOC Analyst" |

These families ONLY feed the "General market trends" section of the output
doc. They don't generate Tier-1 entries and `search-jobs` ignores them.

---

## C. EXCLUSION list — false positives to drop at normalization time

Some titles match a target term but are NOT the right role. If the title OR
the description contains one of these signals, drop the posting from that
family (mark it `family = "EXCLUDED"`).

| Signal (keyword in title/description) | Reason |
|---|---|
| semiconductor, wafer, lithography, fab, etch, deposition, "process engineer" | in hardware-heavy markets, "Customer Engineer" often means a semiconductor field role (Applied Materials, ASML, Lam, KLA) — a different job entirely |
| field service technician, repair, installation (HVAC, hardware) | "Engineer" here means a hardware field technician |
| insurance sales, financial advisor, wealth, mortgage | "Consultant" here means insurance/finance sales, not tech |
| recruiter, talent acquisition (in the TITLE) | an HR role, not a target position |
| teacher, tutor, lecturer | "Consultant"/"Engineer" in an education context |
| graphic, UX/UI only (without dev) | pure design, outside a technical scope |

Edit this list to match whatever false positives show up for YOUR search
terms — it will differ by market and by the roles you're targeting.

---

## D. "Accessibility" flags applied after normalization

Flags computed per posting (see `aggregate.py`), used for tiering and the
"focus score":

- **`local_language_required`**: the description contains a local-language
  signal (see `market-config.md` for the per-city list — e.g. Mandarin:
  `中文`, `普通话`, `mandarin`, `native chinese`, `cantonese`, `粤语`).
  → penalizes the score.
- **`seniority_bucket`**: `graduate` / `associate` (0-2 years) / `mid`
  (3-5) / `senior` (5+). Inferred from the title
  (junior/associate/graduate/senior/lead/principal/head) then from a
  years-of-experience regex in the description (`(\d+)\+?\s*years?`).
- **`visa_friendly_guess`**: a company heuristic (known multinational =
  likely). Never a hard filter, just a signal.
