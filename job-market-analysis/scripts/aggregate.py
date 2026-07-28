#!/usr/bin/env python3
"""
aggregate.py — quantitative engine for the job-market analysis skill.

Reads the scraped JSON dataset(s), deduplicates, normalizes titles into
role families, infers seniority, detects the local-language barrier, and
prints Markdown tables ready to paste into the output document.

No external dependencies (stdlib only).

Usage:
    python3 aggregate.py <input> [--lang-keywords "mandarin,中文,粤语"] \
        [--city "Hong Kong"] [--out stats.md]

<input> = a single .json file (array of postings) OR a folder containing
several .json files. Field names vary by scraper/site, so the script tries
several aliases for each field.
"""

import sys, os, json, re, argparse
from collections import Counter, defaultdict

# --- Target families (niche layer): keep in sync with role-taxonomy.md ---
# family -> list of regexes (on the lowercase title). First match wins.
FAMILIES = {
    "TAM": [r"technical account manager", r"\btam\b", r"technical account management"],
    "CustomerEngineer": [r"customer engineer", r"customer success engineer",
                          r"customer success manager.*tech", r"field engineer"],
    "DeliveryConsultant": [r"delivery consultant", r"professional services",
                           r"\bps consultant\b"],
    "ImplementationConsultant": [r"implementation consultant", r"implementation engineer",
                                 r"onboarding engineer", r"integration consultant"],
    "ITConsultant": [r"it consultant", r"technology consultant", r"application consultant",
                     r"erp consultant", r"functional consultant"],
    "PresalesEngineer": [r"presales", r"pre-sales", r"sales engineer",
                         r"solution consultant", r"solutions consultant"],
    "SolutionsArchitect": [r"solutions architect", r"solution architect",
                           r"cloud architect"],
    "SolutionsEngineer": [r"solutions engineer", r"solution engineer"],
    "CloudEngineer": [r"cloud engineer", r"cloud consultant", r"cloud service engineer"],
    "AppModernization": [r"modernization", r"migration consultant", r"app modernization"],
    "SoftwareEngineer": [r"software engineer", r"\bswe\b", r"backend engineer",
                         r"fullstack", r"full stack", r"\bdeveloper\b"],
}

# --- Broad-scan families (general market volume only) ---
BROAD_FAMILIES = {
    "DataEngineer": [r"data engineer", r"data scientist", r"analytics engineer"],
    "DevOpsSRE": [r"devops", r"site reliability", r"\bsre\b", r"platform engineer"],
    "AIMLEngineer": [r"machine learning engineer", r"\bai engineer\b", r"genai", r"\bml engineer\b"],
    "ProductManager": [r"product manager"],
    "CyberSecurity": [r"security engineer", r"cybersecurity", r"soc analyst"],
}

# --- Exclusion signals (title OR description) ---
EXCLUDE_SIGNALS = [
    r"semiconductor", r"\bwafer\b", r"lithograph", r"\bfab\b", r"\betch\b",
    r"deposition", r"process engineer", r"field service technician",
    r"insurance sales", r"financial advisor", r"\bwealth\b", r"mortgage",
    r"\btutor\b", r"\bteacher\b", r"lecturer",
]

# --- Local language (default: Mandarin/Cantonese). Overridden by --lang-keywords ---
DEFAULT_LANG_KEYWORDS = ["mandarin", "中文", "普通话", "粤语", "繁體中文", "國語",
                         "native chinese", "fluent chinese", "cantonese"]

# --- Known multinationals (visa-friendly heuristic) ---
VISA_FRIENDLY = {
    "aws", "amazon", "google", "microsoft", "ibm", "cisco", "splunk", "oracle",
    "sap", "servicenow", "salesforce", "checkout.com", "bloomberg", "alibaba",
    "tencent", "bytedance", "deloitte", "accenture", "stripe", "gitlab",
    "dassault", "ntt", "iqvia", "tomtom", "dell", "trend micro", "grab", "sea",
    "shopee", "binance", "airwallex",
}

SENIOR_TOKENS = [r"\bsenior\b", r"\bsr\.?\b", r"\bprincipal\b", r"\blead\b",
                 r"\bstaff\b", r"\bhead of\b", r"\bdirector\b", r"\bmanager iii\b"]
JUNIOR_TOKENS = [r"\bjunior\b", r"\bjr\.?\b", r"\bgraduate\b", r"\bgrad\b",
                 r"\bentry\b", r"\bintern\b", r"\bapprentice\b", r"\bcampus\b",
                 r"\bassociate\b", r"\btrainee\b", r"\bfresh\b"]


def get(item, *keys, default=""):
    for k in keys:
        v = item.get(k)
        if v:
            return v
    return default


def load_dataset(path):
    items = []
    files = []
    if os.path.isdir(path):
        for f in os.listdir(path):
            if f.endswith(".json"):
                files.append(os.path.join(path, f))
    else:
        files = [path]
    for fp in files:
        try:
            with open(fp, encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                # some scrapers wrap results as {"items": [...]} or a single object
                data = data.get("items", [data])
            items.extend(data)
        except Exception as e:
            print(f"# WARN: could not read {fp}: {e}", file=sys.stderr)
    return items


def dedup(items):
    seen, out = set(), []
    for it in items:
        key = (get(it, "id", "jobId", "job_id") or
               get(it, "url", "jobUrl", "job_url", "link") or
               (get(it, "title") + "|" + get(it, "organization", "company", "companyName")))
        key = str(key).strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(it)
    return out


def match_family(title, desc, table):
    t = title.lower()
    blob = (title + " " + desc).lower()
    for sig in EXCLUDE_SIGNALS:
        if re.search(sig, blob):
            return "EXCLUDED"
    for fam, pats in table.items():
        for p in pats:
            if re.search(p, t):
                return fam
    return None


def seniority_bucket(title, desc):
    t = title.lower()
    for p in JUNIOR_TOKENS:
        if re.search(p, t):
            # campus/graduate/intern/fresh -> graduate ; associate/junior -> associate
            if re.search(r"graduate|grad|intern|campus|fresh|trainee|apprentice", t):
                return "graduate"
            return "associate"
    for p in SENIOR_TOKENS:
        if re.search(p, t):
            return "senior"
    # otherwise: years-of-experience regex in the description
    yrs = [int(x) for x in re.findall(r"(\d+)\+?\s*years?", desc.lower())]
    if yrs:
        m = min(yrs)
        if m <= 1:
            return "graduate"
        if m <= 2:
            return "associate"
        if m <= 5:
            return "mid"
        return "senior"
    return "mid"  # conservative default when nothing is detected


def has_local_language(desc, keywords):
    d = desc.lower()
    return any(k.lower() in d for k in keywords)


def is_visa_friendly(company):
    c = company.lower()
    return any(v in c for v in VISA_FRIENDLY)


def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--lang-keywords", default="")
    ap.add_argument("--city", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    lang_kw = ([k.strip() for k in args.lang_keywords.split(",") if k.strip()]
               if args.lang_keywords else DEFAULT_LANG_KEYWORDS)

    raw = load_dataset(args.input)
    items = dedup(raw)

    # per-posting enrichment
    niche = []        # postings in the target niche
    broad_counter = Counter()
    for it in items:
        title = str(get(it, "title", "jobTitle", "position", "name"))
        desc = str(get(it, "description", "description_text", "descriptionText",
                       "jobDescription", "text"))
        company = str(get(it, "organization", "company", "companyName", "employer"))
        loc = str(get(it, "location", "jobLocation", "city", "locationName"))
        url = str(get(it, "url", "jobUrl", "job_url", "link"))

        fam = match_family(title, desc, FAMILIES)
        if fam == "EXCLUDED":
            continue
        if fam is None:
            bfam = match_family(title, desc, BROAD_FAMILIES)
            if bfam and bfam != "EXCLUDED":
                broad_counter[bfam] += 1
            continue
        # also count the niche family in the general pulse
        broad_counter[fam] += 1
        niche.append({
            "family": fam, "title": title, "company": company, "loc": loc, "url": url,
            "seniority": seniority_bucket(title, desc),
            "lang": has_local_language(desc, lang_kw),
            "visa": is_visa_friendly(company),
        })

    total = len(items)
    n_niche = len(niche)

    # ---- Markdown assembly ----
    L = []
    city = args.city or "(city)"
    L.append(f"## 0. Market snapshot — {city} (auto-generated)\n")
    lang_share = (sum(1 for j in niche if j["lang"]) / n_niche * 100) if n_niche else 0
    L.append(f"- Raw postings scraped: {len(raw)} → deduplicated: {total}")
    L.append(f"- Postings kept in your target niche: {n_niche}")
    L.append(f"- Postings mentioning the local language: {lang_share:.0f}% of the niche")
    visa_share = (sum(1 for j in niche if j["visa"]) / n_niche * 100) if n_niche else 0
    L.append(f"- Postings at a known visa-friendly multinational: {visa_share:.0f}%\n")

    # 1. General trends
    L.append("## 1. General market trends (broad scan)\n")
    rows = [[fam, c, f"{c/total*100:.0f}%"] for fam, c in broad_counter.most_common(12)]
    L.append(md_table(["Family", "Postings", "% of total scraped"], rows) + "\n")

    # 2a. Volume by target family + top companies
    L.append("## 2a. Volume by target family (niche)\n")
    by_fam = defaultdict(list)
    for j in niche:
        by_fam[j["family"]].append(j)
    rows = []
    for fam, js in sorted(by_fam.items(), key=lambda kv: -len(kv[1])):
        top_co = ", ".join(f"{c}({n})" for c, n in
                           Counter(j["company"] for j in js if j["company"]).most_common(3))
        rows.append([fam, len(js), top_co or "—"])
    L.append(md_table(["Family", "Postings", "Top 3 companies"], rows) + "\n")

    # 2b. Role x seniority matrix
    L.append("## 2b. Role × seniority matrix  ← flagship deliverable\n")
    buckets = ["graduate", "associate", "mid", "senior"]
    rows = []
    for fam, js in sorted(by_fam.items(), key=lambda kv: -len(kv[1])):
        c = Counter(j["seniority"] for j in js)
        rows.append([fam] + [c.get(b, 0) for b in buckets])
    L.append(md_table(["Family", "Graduate", "Associate(0-2)", "Mid(3-5)", "Senior(5+)"],
                      rows) + "\n")
    L.append("> Left columns (Graduate/Associate) = the most accessible at ~0-2 years exp.\n")

    # 2c. Focus score
    L.append("## 2c. Focus score — where to concentrate effort (auto)\n")
    rows = []
    score_rows = []
    maxvol = max((len(js) for js in by_fam.values()), default=1)
    for fam, js in by_fam.items():
        n = len(js)
        acc = sum(1 for j in js if j["seniority"] in ("graduate", "associate")) / n
        visa = sum(1 for j in js if j["visa"]) / n
        nolang = 1 - (sum(1 for j in js if j["lang"]) / n)
        vol_norm = n / maxvol
        score = round(vol_norm * (0.4 + 0.6 * acc) * (0.5 + 0.5 * visa) * (0.4 + 0.6 * nolang), 3)
        score_rows.append((fam, score, n, acc, visa, nolang))
    for fam, score, n, acc, visa, nolang in sorted(score_rows, key=lambda r: -r[1]):
        rows.append([fam, score, n, f"{acc*100:.0f}%", f"{visa*100:.0f}%", f"{nolang*100:.0f}%"])
    L.append(md_table(["Family", "Score", "Volume", "% accessible (grad/assoc)",
                       "% visa-friendly", "% without a language barrier"], rows) + "\n")
    L.append("> Score = normalized_volume × accessibility × visa × (1−language barrier). "
             "Higher = better place to concentrate effort.\n")

    # raw listing of niche postings (for Tier 1/2/3 curation)
    L.append("## Appendix — kept niche postings (for Tier 1/2/3 curation)\n")
    rows = [[j["title"][:60], j["company"][:30], j["family"], j["seniority"],
             "lang!" if j["lang"] else "", "visa" if j["visa"] else "", j["url"][:60]]
            for j in niche]
    L.append(md_table(["Title", "Company", "Family", "Seniority", "Lang", "Visa", "URL"], rows))

    output = "\n".join(L)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(output)
        print(f"# Stats written to {args.out} ({n_niche} niche postings / {total} deduplicated)")
    else:
        print(output)


if __name__ == "__main__":
    main()
