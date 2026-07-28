# Market Config — parameters per city/market

For each target city, this file gives: **location aliases** (for the
`location_search` scrape parameter + the output filename), the **local
language barrier severity** (+ keywords to detect), **visa-friendliness**,
and **known hubs/companies** that sponsor.

If a city isn't listed, the skill applies the `DEFAULT` block and fills the
gaps with a quick web search (official business language, typical visa
sponsorship).

This file ships with a handful of pre-filled example cities so the skill is
usable out of the box. Add, edit, or remove entries freely to match the
cities you're actually targeting — none of this data is specific to any one
person.

---

## Entry format

```
city_key        : canonical key (output filename prefix, e.g. "Taiwan", "HK", "Singapore")
location_search : exact value(s) for the scraper's --location (LinkedIn geo)
file_prefix     : output .md filename prefix
local_language  : { name, severity (low/medium/high), keywords[] }
visa            : visa-friendliness note
known_hubs      : multinational companies known to hire + sponsor in the area
```

---

## Hong Kong (example)

- **city_key**: `HK`
- **location_search**: `"Hong Kong"`
- **file_prefix**: `HK`
- **local_language**: name=Cantonese/Mandarin, **severity=low** (English is
  the business language). Keywords to detect anyway: `cantonese`,
  `mandarin`, `中文`, `粤语`, `native chinese`.
- **visa**: very favorable. Most multinationals sponsor; a relocation-friendly
  city for foreign hires.
- **known_hubs**: AWS, Google Cloud, Microsoft, IBM, Cisco/Splunk, Alibaba
  Cloud, Tencent Cloud, Checkout.com, ServiceNow, Oracle, SAP, HKT,
  Deloitte, Bloomberg.

## Mainland China — Shanghai / Beijing (example)

- **city_key**: `China` (or `Shanghai` / `Beijing`)
- **location_search**: `"Shanghai, China"`, `"Beijing, China"`
- **file_prefix**: `China`
- **local_language**: name=Mandarin, **severity=high**. Keywords: `mandarin`,
  `普通话`, `中文`, `native chinese`, `fluent chinese`, `流利中文`.
- **visa**: restricted. Only multinationals with an APAC-Shanghai HQ are
  realistically accessible to a non-Mandarin speaker.
- **known_hubs**: Bloomberg (English-first), Checkout.com, NTT DATA, IQVIA,
  Accenture, Deloitte, Dassault Systèmes, TomTom.
- **note**: roughly 85% of postings from Chinese companies require Mandarin
  in practice, even when the posting is written in English. Always flag
  this at the market level.

## Singapore (example)

- **city_key**: `Singapore`
- **location_search**: `"Singapore"`
- **file_prefix**: `Singapore`
- **local_language**: name=English, **severity=low** (English is the
  official working language). No barrier.
- **visa**: favorable but subject to Employment Pass (COMPASS) quotas and
  salary thresholds; multinationals sponsor routinely.
- **known_hubs**: AWS, Google, Microsoft, Stripe, Grab, Sea/Shopee, Binance,
  GitLab, Salesforce, ServiceNow, Temus, Alibaba Cloud APAC.

## Taiwan — Taipei (example)

- **city_key**: `Taiwan`
- **location_search**: `"Taipei, Taiwan"`, `"Taiwan"`
- **file_prefix**: `Taiwan`
- **local_language**: name=Mandarin (Traditional), **severity=high**.
  Keywords: `mandarin`, `中文`, `國語`, `native chinese`, `繁體中文`,
  `fluent chinese`.
- **visa**: a Gold Card is possible for qualified tech profiles; otherwise
  standard sponsorship via multinationals. Smaller market, heavily
  hardware/semiconductor-skewed.
- **known_hubs**: Google (large Taipei site), Microsoft, AWS, TSMC
  (semiconductors — often out of scope for software roles), Trend Micro,
  Appier, Gogolook, IBM, Dell.
- **note**: strong semiconductor/hardware bias — the EXCLUSION list in
  `role-taxonomy.md` is important here (many "Customer Engineer" postings
  are actually semiconductor field roles).

## DEFAULT (unlisted city)

- **location_search**: the raw value you provided (e.g. "Dubai", "Toronto").
- **local_language**: determine via a quick web search (business language).
  English-speaking -> severity=low; otherwise medium/high depending on the
  market.
- **visa**: check quickly (does the country routinely sponsor foreign tech
  hires?). When in doubt, don't drop it, just flag "to confirm".
- **known_hubs**: infer from the top companies surfaced by the scrape.
