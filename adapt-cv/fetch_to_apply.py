#!/usr/bin/env python3
"""
fetch_to_apply.py — autonomous Notion fetch + writeback for the adapt-cv batch mode.

Pure standard library (urllib). Talks to the Notion API directly so the raw JSON
never has to enter Claude's context.

Subcommands
-----------
  (default / fetch)        : query the database, keep rows whose status carries
                             the "To Apply" tag, write one clean job file per
                             offer + a batch_manifest.json, print a compact JSON
                             summary.
      --batch-dir PATH     : where to write work/ + output/ + batch_manifest.json
                             (default: ./Batch_Applications/<YYYY-MM-DD>)
      --config PATH        : config file (default: config.json next to this script)

  --mark-created PAGE_ID   : append the "CV created" tag to that page's status
                             (multi-select) WITHOUT removing "To Apply".
                             Idempotent: no-op if already present.

  --selftest               : run offline logic tests (no network, no token).

Config (config.json next to the script, or environment variables which override):
  NOTION_TOKEN, NOTION_DB_ID, STATUS_PROP, TO_APPLY_TAG, CV_CREATED_TAG,
  JD_PROP, COMPANY_PROP, ROLE_PROP, URL_PROP
Empty optional *_PROP values trigger auto-detection.
"""
import os, sys, json, re, argparse, datetime
import urllib.request, urllib.error

NOTION_VERSION = "2022-06-28"
API = "https://api.notion.com/v1"

DEFAULTS = {
    "NOTION_TOKEN": "", "NOTION_DB_ID": "",
    "STATUS_PROP": "Status", "TO_APPLY_TAG": "To Apply", "CV_CREATED_TAG": "CV created",
    "JD_PROP": "", "COMPANY_PROP": "", "ROLE_PROP": "", "URL_PROP": "",
}


# ----------------------------- config -----------------------------------------
def load_config(script_dir, cli_config=None):
    cfg = dict(DEFAULTS)
    path = cli_config or os.path.join(script_dir, "config.json")
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                for k, v in json.load(f).items():
                    if v is not None:
                        cfg[k] = v
        except Exception as e:
            print(json.dumps({"error": "bad_config", "detail": str(e)}))
            sys.exit(2)
    for k in list(cfg):
        env = os.environ.get(k)
        if env:
            cfg[k] = env
    return cfg


def token_ok(cfg):
    t, db = cfg.get("NOTION_TOKEN", ""), cfg.get("NOTION_DB_ID", "")
    if not t or not db:
        return False
    if t.startswith("secret_xxx") or db.startswith("xxxx"):
        return False
    return True


# ----------------------------- http -------------------------------------------
def api(method, path, token, body=None):
    url = path if path.startswith("http") else API + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Notion-Version", NOTION_VERSION)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError("Notion %s %s -> HTTP %s %s"
                           % (method, url, e.code, e.read().decode("utf-8")[:300]))


def query_all(token, db_id):
    cursor, out = None, []
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        r = api("POST", "/databases/%s/query" % db_id, token, body)
        out.extend(r.get("results", []))
        if r.get("has_more"):
            cursor = r.get("next_cursor")
        else:
            break
    return out


def page_blocks_text(token, page_id):
    cursor, out = None, []
    while True:
        path = "/blocks/%s/children?page_size=100" % page_id
        if cursor:
            path += "&start_cursor=" + cursor
        r = api("GET", path, token)
        for b in r.get("results", []):
            bt = b.get("type")
            rt = (b.get(bt) or {}).get("rich_text") if isinstance(b.get(bt), dict) else None
            if rt:
                out.append(rt_plain(rt))
        if r.get("has_more"):
            cursor = r.get("next_cursor")
        else:
            break
    return "\n".join(t for t in out if t.strip())


# ----------------------------- notion field helpers ---------------------------
def rt_plain(rt):
    return "".join(x.get("plain_text", "") for x in (rt or []))


def prop_text(prop):
    if not prop:
        return ""
    t = prop.get("type")
    if t == "title":
        return rt_plain(prop.get("title"))
    if t == "rich_text":
        return rt_plain(prop.get("rich_text"))
    if t == "url":
        return prop.get("url") or ""
    if t == "email":
        return prop.get("email") or ""
    if t == "select":
        s = prop.get("select")
        return s.get("name", "") if s else ""
    if t == "formula":
        f = prop.get("formula") or {}
        return str(f.get("string") or f.get("number") or "")
    return ""


def status_tags(prop):
    if not prop:
        return []
    t = prop.get("type")
    if t == "multi_select":
        return [o.get("name") for o in prop.get("multi_select", [])]
    if t == "status":
        s = prop.get("status")
        return [s.get("name")] if s else []
    if t == "select":
        s = prop.get("select")
        return [s.get("name")] if s else []
    return []


def _find_named(props, substrings):
    for name, prop in props.items():
        low = name.lower()
        if any(s in low for s in substrings):
            return name, prop
    return None, None


def _title_prop(props):
    for name, prop in props.items():
        if prop.get("type") == "title":
            return name, prop
    return None, None


def extract_offer(page, cfg, blocks_fetcher):
    props = page.get("properties", {})
    page_id = page.get("id", "")

    # role / title
    if cfg["ROLE_PROP"] and cfg["ROLE_PROP"] in props:
        role = prop_text(props[cfg["ROLE_PROP"]])
    else:
        _, tp = _title_prop(props)
        role = prop_text(tp)

    # company
    if cfg["COMPANY_PROP"] and cfg["COMPANY_PROP"] in props:
        company = prop_text(props[cfg["COMPANY_PROP"]])
    else:
        _, cp = _find_named(props, ["compan", "entreprise", "employer", "societe", "société"])
        company = prop_text(cp)
    if not company.strip():
        company = "NA"

    # url
    if cfg["URL_PROP"] and cfg["URL_PROP"] in props:
        url = prop_text(props[cfg["URL_PROP"]])
    else:
        url = ""
        for name, prop in props.items():
            if prop.get("type") == "url" and prop.get("url"):
                url = prop["url"]; break
        if not url:
            _, lp = _find_named(props, ["url", "link", "lien"])
            url = prop_text(lp)

    # JD: configured prop -> longest rich_text prop -> page body blocks
    jd = ""
    if cfg["JD_PROP"] and cfg["JD_PROP"] in props:
        jd = prop_text(props[cfg["JD_PROP"]])
    if not jd.strip():
        best = ""
        for name, prop in props.items():
            if prop.get("type") == "rich_text":
                txt = rt_plain(prop.get("rich_text"))
                if len(txt) > len(best):
                    best = txt
        if len(best.strip()) >= 120:
            jd = best
    if not jd.strip() and blocks_fetcher is not None:
        jd = blocks_fetcher(page_id)

    return {"company": company.strip(), "role": role.strip(),
            "jd": jd.strip(), "url": (url or "").strip(), "page_id": page_id}


def slug(s):
    s = re.sub(r"[^A-Za-z0-9]+", "_", s or "").strip("_")
    return s[:40] or "offer"


def render_jd_md(off):
    lines = [
        "# %s — %s" % (off["company"] or "NA", off["role"] or "Role"),
        "",
        "- Company: %s" % (off["company"] or "NA"),
        "- Role: %s" % (off["role"] or ""),
        "- URL: %s" % (off["url"] or ""),
        "- Notion page_id: %s" % off["page_id"],
        "",
        "## Job description",
        "",
        off["jd"],
        "",
    ]
    return "\n".join(lines)


def process_to_apply(pages, cfg, blocks_fetcher):
    """Pure: returns (manifest_entries, {filename: content}). No I/O."""
    to_apply = [p for p in pages
                if cfg["TO_APPLY_TAG"] in status_tags(p.get("properties", {}).get(cfg["STATUS_PROP"]))]
    manifest, files = [], {}
    for i, p in enumerate(to_apply, 1):
        off = extract_offer(p, cfg, blocks_fetcher)
        base = {"index": i, "company": off["company"], "role": off["role"],
                "page_id": off["page_id"], "url": off["url"]}
        if not off["jd"].strip():
            base.update({"jd_file": None, "status": "skipped", "reason": "empty_jd"})
            manifest.append(base)
            continue
        fn = "job_%02d_%s.md" % (i, slug(off["company"]))
        files[fn] = render_jd_md(off)
        base.update({"jd_file": "work/" + fn, "status": "ok"})
        manifest.append(base)
    return manifest, files


# ----------------------------- writeback --------------------------------------
def compute_marked(tags, cv_tag):
    if cv_tag in tags:
        return "noop", list(tags)
    return "marked", list(tags) + [cv_tag]


# ----------------------------- commands ---------------------------------------
def cmd_fetch(cfg, batch_dir):
    if not token_ok(cfg):
        print(json.dumps({"error": "no_token",
                          "hint": "fill config.json (NOTION_TOKEN, NOTION_DB_ID) or set the env vars; "
                                  "the skill will fall back to a single MCP connector call"}))
        return 3
    work = os.path.join(batch_dir, "work")
    os.makedirs(work, exist_ok=True)
    os.makedirs(os.path.join(batch_dir, "output"), exist_ok=True)
    pages = query_all(cfg["NOTION_TOKEN"], cfg["NOTION_DB_ID"])
    manifest, files = process_to_apply(pages, cfg, lambda pid: page_blocks_text(cfg["NOTION_TOKEN"], pid))
    for fn, content in files.items():
        with open(os.path.join(work, fn), "w", encoding="utf-8") as f:
            f.write(content)
    mpath = os.path.join(batch_dir, "batch_manifest.json")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump({"generated": datetime.datetime.now().isoformat(timespec="seconds"),
                   "batch_dir": batch_dir, "offers": manifest}, f, ensure_ascii=False, indent=2)
    ok = sum(1 for m in manifest if m["status"] == "ok")
    skip = sum(1 for m in manifest if m["status"] == "skipped")
    print(json.dumps({"fetched": ok, "skipped": skip, "total": len(manifest), "manifest": mpath},
                     ensure_ascii=False))
    return 0


def cmd_mark_created(cfg, page_id):
    if not token_ok(cfg):
        print(json.dumps({"error": "no_token"}))
        return 3
    page = api("GET", "/pages/" + page_id, cfg["NOTION_TOKEN"])
    prop = page.get("properties", {}).get(cfg["STATUS_PROP"])
    if not prop or prop.get("type") != "multi_select":
        print(json.dumps({"error": "not_multi_select", "prop": cfg["STATUS_PROP"],
                          "type": prop.get("type") if prop else None}))
        return 4
    tags = [o.get("name") for o in prop.get("multi_select", [])]
    action, new = compute_marked(tags, cfg["CV_CREATED_TAG"])
    if action == "noop":
        print(json.dumps({"status": "noop", "page_id": page_id, "tags": tags}, ensure_ascii=False))
        return 0
    api("PATCH", "/pages/" + page_id, cfg["NOTION_TOKEN"],
        {"properties": {cfg["STATUS_PROP"]: {"multi_select": [{"name": t} for t in new]}}})
    print(json.dumps({"status": "marked", "page_id": page_id, "tags": new}, ensure_ascii=False))
    return 0


# ----------------------------- selftest ---------------------------------------
def _fake_pages():
    def status(*tags):
        return {"type": "multi_select", "multi_select": [{"name": t} for t in tags]}

    def rich(txt):
        return {"type": "rich_text", "rich_text": [{"plain_text": txt}]}

    def title(txt):
        return {"type": "title", "title": [{"plain_text": txt}]}

    long_jd = "We need a backend engineer with Python, AWS and Neptune graph experience. " * 4
    return [
        {"id": "pageA", "properties": {
            "Status": status("To Apply"), "Company": rich("Acme"),
            "Name": title("Backend Engineer"), "JD": rich(long_jd),
            "URL": {"type": "url", "url": "https://jobs.example/acme"}}},
        {"id": "pageB", "properties": {  # same company, empty JD -> skipped
            "Status": status("To Apply"), "Company": rich("Acme"),
            "Name": title("Data Engineer"), "JD": rich("")}},
        {"id": "pageC", "properties": {  # JD only in page body blocks
            "Status": status("To Apply"), "Company": rich("Beta"),
            "Name": title("ML Engineer")}},
        {"id": "pageD", "properties": {  # not To Apply -> ignored
            "Status": status("Applied"), "Company": rich("Gamma"),
            "Name": title("SRE"), "JD": rich("x" * 200)}},
    ]


def selftest():
    cfg = dict(DEFAULTS)
    body_text = ("Beta is hiring an ML engineer. You will build training pipelines "
                 "and deploy models on Kubernetes. " * 4)
    blocks = lambda pid: body_text if pid == "pageC" else ""
    manifest, files = process_to_apply(_fake_pages(), cfg, blocks)

    ok = [m for m in manifest if m["status"] == "ok"]
    sk = [m for m in manifest if m["status"] == "skipped"]
    fns = list(files.keys())
    results = []

    results.append(("only To Apply rows processed (3)", len(manifest) == 3))
    results.append(("2 ok offers (prop JD + body JD)", len(ok) == 2))
    results.append(("1 skipped for empty_jd",
                    len(sk) == 1 and sk[0]["reason"] == "empty_jd" and sk[0]["company"] == "Acme"))
    results.append(("body-block JD recovered for Beta",
                    any(m["company"] == "Beta" and m["status"] == "ok" for m in manifest)))
    results.append(("filenames unique (dup company safe)", len(fns) == len(set(fns))))
    results.append(("index prefix in filename", all(re.match(r"job_\d{2}_", f) for f in fns)))
    results.append(("Gamma (not To Apply) excluded",
                    all(m["company"] != "Gamma" for m in manifest)))

    a1, n1 = compute_marked(["To Apply"], "CV created")
    a2, n2 = compute_marked(["To Apply", "CV created"], "CV created")
    results.append(("mark adds CV created, keeps To Apply",
                    a1 == "marked" and n1 == ["To Apply", "CV created"]))
    results.append(("mark idempotent when already tagged",
                    a2 == "noop" and n2 == ["To Apply", "CV created"]))

    print("=== fetch_to_apply.py selftest ===")
    allok = True
    for label, passed in results:
        allok = allok and passed
        print(("PASS" if passed else "FAIL") + "  " + label)
    print("\n--- sample manifest ---")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print("\n--- sample JD file (%s) ---" % fns[0])
    print(files[fns[0]][:400])
    return 0 if allok else 1


# ----------------------------- entrypoint -------------------------------------
def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-dir")
    ap.add_argument("--config")
    ap.add_argument("--mark-created", metavar="PAGE_ID")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    cfg = load_config(script_dir, args.config)

    if args.mark_created:
        sys.exit(cmd_mark_created(cfg, args.mark_created))

    batch_dir = args.batch_dir or os.path.join(
        ".", "Batch_Applications", datetime.date.today().isoformat())
    batch_dir = os.path.abspath(batch_dir)
    sys.exit(cmd_fetch(cfg, batch_dir))


if __name__ == "__main__":
    main()
