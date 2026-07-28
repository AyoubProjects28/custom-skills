# Notion schema — Applications + People databases

This file is the schema contract the `search-jobs` and `adapt-cv` (batch
mode) skills rely on. It ships with **placeholder IDs** — follow the root
`README.md`'s "Set up your Notion CRM" section to create the two databases
with a template, then paste your own IDs into the block below before your
first run. Both skills read this file before their first Notion call, so
keeping it accurate matters.

> Writing convention: to create a page, use `notion-create-pages` with the
> `data_source_url` (`collection://...`) of the target database. To update
> a page, use `notion-update-page`. To search/filter (anti-duplicate check),
> use `notion-query-data-sources` in SQL against the collection.

---

## Your workspace IDs (fill in after setup)

```
Parent page (e.g. "Job Applications"):  <PARENT_PAGE_ID>
Applications database (page):           <APPLICATIONS_DB_PAGE_ID>
Applications data source (collection):  collection://<APPLICATIONS_DATA_SOURCE_ID>
People database (page):                 <PEOPLE_DB_PAGE_ID>          (optional)
People data source (collection):        collection://<PEOPLE_DATA_SOURCE_ID>  (optional)
```

How to get these IDs: open each database as a full page in Notion, copy the
32-character ID out of the URL. The data-source (collection) ID is
returned by `notion-search` or `notion-fetch` the first time you query the
database through the connector — call `notion-search` for your database's
name once, and copy the `collection://...` URL it returns into this file.

---

## Database: Applications

### Properties

| Property | Type | Values / notes |
|---|---|---|
| **Position** | title | job title (the database's title field) |
| **Company** | text | employer |
| **Location** | text | target city (e.g. "Hong Kong") |
| **Job URL** | url | direct posting URL — **anti-duplicate key** |
| **Job Description** | text | full description (text) |
| **Status** | multi_select | `To Apply`, `Applied`, `Emailed`, `Interview`, `Offer`, `Rejected`, `Withdrawn`, `Ghosted`, `Skipped (not qualified)`, `Skipped (keyword mismatch)`, `Skipped (staffing)` |
| **Source** | select | `LinkedIn`, `LinkedIn Manual`, `LinkedIn Easy Apply (Auto)`, `Indeed`, `Company Website`, `Other` |
| **Date Applied** | date | today's date (ISO-8601) |
| **Outreach Email** | text | body of the generated email |
| **Contacts** | relation -> People | array of People page URLs (optional feature) |
| **Keywords Matched** | text | keywords matching the posting (never overwrite) |
| **Notes** | text | free notes (never overwrite) |
| **Salary** | text | range if available |
| **Tailored CV** | text | note about which tailored CV version applies, if any |

**Status must be a multi-select**, not a single-select or the built-in
"status" type — `adapt-cv`'s batch mode needs to hold `To Apply` and
`CV created` on the same row at once.

### Example page creation
```
notion-create-pages
  parent: data_source_url = collection://<APPLICATIONS_DATA_SOURCE_ID>
  properties:
    Position        = "Customer Engineer, Cloud Platform"
    Company         = "Example Corp"
    Location        = "Hong Kong"
    Job URL         = "https://www.linkedin.com/jobs/view/1234567890"
    Job Description = "<full text>"
    Status          = ["To Apply"]
    Source          = "LinkedIn"
    Date Applied    = 2026-06-24
```

### Anti-duplicate check (SQL)
```sql
SELECT url, "Position", "Company" FROM "collection://<APPLICATIONS_DATA_SOURCE_ID>"
WHERE "Job URL" = ?
```
Fallback if there's no URL: same `Position` + same `Company`.

---

## Database: People (optional)

Only needed if you plan to track named recruiter/hiring-manager contacts.
The default free pipeline leaves `Contacts` empty and skips this database
entirely — see `search-jobs/SKILL.md` Step 2.

### Properties

| Property | Type | Values / notes |
|---|---|---|
| **Full Name** | title | full name (title field) |
| **Company** | text | employer |
| **Job Title** | text | that person's title |
| **LinkedIn URL** | url | profile — **anti-duplicate key** |
| **Email** | email | if known |
| **Department** | select | `Exec`, `HR & Recruiting`, `Engineering`, `Product`, `Management`, `Sales`, `Other` |
| **Message Type** | select | `HR Template`, `Referral Request`, `General Interest`, `Alumni`, `Personal contact`, `None` |
| **Outreach Status** | select | `Connection Sent`, `Connected`, `Note Sent`, `Message Sent`, `Replied`, `Not Interested` |
| **Actively Hiring** | multi_select | `Hiring now` |
| **Date Contacted** | date | |
| **Date Replied** | date | |
| **Notes** | text | why this contact is relevant |
| **Related to Applications (Contacts)** | relation -> Applications | array of Application page URLs |

### Anti-duplicate check (SQL)
```sql
SELECT url, "Full Name", "Company" FROM "collection://<PEOPLE_DATA_SOURCE_ID>"
WHERE "LinkedIn URL" = ?
```
Fallback if there's no URL: same `Full Name` + same `Company`.

> Bidirectional relation: `Applications.Contacts` <-> `People.Related to
> Applications (Contacts)`. To link, create the Application first, then the
> People page with the Application's URL, then fill `Contacts` on the
> Application side (append, never replace the existing array).
