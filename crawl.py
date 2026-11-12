"""The family's `crawl` task (see scrape.json). Try it without the hub: python crawl.py --local [url] The pool worker runs it with the assignment's env and:
SCRAPE_POOL_PROJECT (which project), SCRAPE_JOB_INDEX / SCRAPE_TOTAL_JOBS (this worker's slice), SCRAPE_MAX_HOURS (time budget).

It claims queue items from the hub, fetches each page politely (threads and delay come from the hub on every call), keeps the
raw page in the family's bucket (the hub signs the upload; this code never holds a storage key), stores one record per book,
and reports the standard counters (n_http, t_http_s, http_error, http_<code>) the hub uses for politeness and tracking.
"""
import gzip
import html
import json
import os
import re
import sys
import time

import requests
from scrape_hub_client import HubClient, LocalHub, timed_get

PROJECT = os.environ.get("SCRAPE_POOL_PROJECT", "")
SITE = os.environ.get("SITE", "https://books.toscrape.com")
DEADLINE = time.time() + float(os.environ.get("SCRAPE_MAX_HOURS", "1")) * 3600 - 120
UA = "s1d-labs scraper (https://github.com/s1d-labs)"
BOOK = re.compile(r'<article class="product_pod">.*?<a href="([^"]+)" title="([^"]+)".*?<p class="price_color">([^<]+)</p>.*?'
                  r'<p class="instock availability">\s*(?:<i[^>]*></i>)?\s*([^<]+?)\s*</p>', re.S)


def parse(page):
    """[(record_id, data)] for the books on one catalogue page. Pure: test it on saved pages."""
    out = []
    for href, title, price, stock in BOOK.findall(page):
        slug = href.rsplit("/", 2)[-2]
        out.append((slug, {"title": html.unescape(title), "price": price.strip(), "availability": stock.strip(),
                           "url": SITE + "/catalogue/" + href.lstrip("./")}))
    return out


def local(url):
    hub = LocalHub()
    page = fetch(hub, requests.Session(), url)
    rows = parse(page) if page else []
    for rid, data in rows:
        print(json.dumps({"record_id": rid, "data": data}, ensure_ascii=False))
    print(f"{len(rows)} records, counters {hub.counts}", file=sys.stderr)


def fetch(hub, session, url):
    r = timed_get(hub, session, url, timeout=30, headers={"User-Agent": UA})    # counts n_http, t_http_s, http_<code>, http_error
    if r is None or r.status_code != 200:
        return None
    if not r.encoding or r.encoding.lower() == "iso-8859-1":     # no charset declared: requests guesses Latin-1; trust the content
        r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def main():
    hub = HubClient(PROJECT, job_index=int(os.environ.get("SCRAPE_JOB_INDEX", "0")), total_jobs=int(os.environ.get("SCRAPE_TOTAL_JOBS", "1")))
    session = requests.Session()
    try:
        while time.time() < DEADLINE:
            if hub.settings.get("paused"):
                time.sleep(30)                          # the hub holds us (site down, or the family owner paused it)
                continue
            items = hub.claim(1, steal=True, retry_failed=True)
            if not items:
                break                                   # nothing left for this project: exit, the worker asks the hub for more
            item = items[0]
            page = fetch(hub, session, item["payload"]["url"])
            if page is None:
                hub.complete([item["key"]], "failed", error="page did not load")
                continue
            hub.upload_many([(f"pages/{item['key']}.html.gz", gzip.compress(page.encode()), "application/gzip")])
            rows = parse(page)
            for rid, data in rows:
                hub.record(rid, {**data, "page": item["key"]})
            hub.complete([item["key"]], "done", fetched=len(rows))
            time.sleep(max(0.5, hub.settings.get("delay_ms", 0) / 1000))
        hub.close()
    except BaseException as e:
        hub.close("failed", f"{type(e).__name__}: {e}"[:200])
        raise


if __name__ == "__main__":
    if sys.argv[1:2] == ["--local"]:
        local(sys.argv[2] if len(sys.argv) > 2 else SITE + "/catalogue/page-1.html")
    else:
        main()
