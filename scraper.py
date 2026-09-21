#!/usr/bin/env python3
"""
Scraper for HK Registered Pharmacists from PPBHK.
Fetches all letter pages (A-Z), parses table, caches to JSON + SQLite-like JSON.
"""

import urllib.request
import urllib.error
import json
import re
import time
import os
from html.parser import HTMLParser
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
CACHE_FILE = DATA_DIR / "pharmacists.json"
META_FILE = DATA_DIR / "meta.json"
BASE_URL = "https://www.ppbhk.org.hk/eng/list_pharmacists/list.php?key={}"

USER_AGENT = "Mozilla/5.0 (compatible; HKPharmacistSearch/1.0; +https://github.com/tcf652/pharmacist-search)"


class PharmacistTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_row = False
        self.in_td = False
        self.current_row = []
        self.current_cell = []
        self.rows = []
        self.td_count = 0
        self.capture = False

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        if tag == "tr" and attrs_d.get("valign") == "top":
            self.in_row = True
            self.current_row = []
            self.td_count = 0
        elif tag == "td" and self.in_row:
            self.in_td = True
            self.current_cell = []
            self.td_count += 1
        elif tag == "br" and self.in_td:
            self.current_cell.append("\n")

    def handle_endtag(self, tag):
        if tag == "td" and self.in_td:
            text = "".join(self.current_cell).strip()
            # Normalize whitespace
            text = re.sub(r"[ \t]+", " ", text)
            text = re.sub(r"\n+", "\n", text).strip()
            self.current_row.append(text)
            self.in_td = False
        elif tag == "tr" and self.in_row:
            if len(self.current_row) >= 6:
                # cols: reg, name, null, qual, null, date
                reg = self.current_row[0]
                name = self.current_row[1]
                qual = self.current_row[3]
                date = self.current_row[5]
                if reg and reg.startswith("P"):
                    self.rows.append({
                        "reg_no": reg,
                        "name": name,
                        "qualifications": qual,
                        "reg_date": date,
                    })
            self.in_row = False

    def handle_data(self, data):
        if self.in_td:
            self.current_cell.append(data)


def fetch_with_retry(url, retries=3, delay=2.0):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == retries - 1:
                raise
            print(f"  Retry {attempt+1}/{retries} after error: {e}")
            time.sleep(delay * (attempt + 1))
    return None


def scrape_letter(letter: str) -> list:
    url = BASE_URL.format(letter)
    print(f"Scraping {letter} ...")
    html = fetch_with_retry(url)
    parser = PharmacistTableParser()
    parser.feed(html)
    print(f"  Found {len(parser.rows)} records")
    return parser.rows


def scrape_all(delay_between=1.0) -> list:
    all_records = []
    seen = set()
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        try:
            rows = scrape_letter(letter)
            for r in rows:
                if r["reg_no"] not in seen:
                    seen.add(r["reg_no"])
                    all_records.append(r)
            time.sleep(delay_between)
        except Exception as e:
            print(f"Failed letter {letter}: {e}")
    return all_records


def save_cache(records: list):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    meta = {
        "last_updated": now,
        "count": len(records),
        "source": "https://www.ppbhk.org.hk/eng/list_pharmacists/list.php",
    }
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"Saved {len(records)} records to {CACHE_FILE}")
    return meta


def load_cache() -> tuple[list, dict]:
    if not CACHE_FILE.exists():
        return [], {}
    with open(CACHE_FILE, encoding="utf-8") as f:
        records = json.load(f)
    meta = {}
    if META_FILE.exists():
        with open(META_FILE, encoding="utf-8") as f:
            meta = json.load(f)
    return records, meta


def main():
    print("Starting full scrape of PPBHK Registered Pharmacists...")
    records = scrape_all()
    if records:
        meta = save_cache(records)
        print(f"Done. Last updated: {meta['last_updated']}, total: {meta['count']}")
    else:
        print("No records scraped.")


if __name__ == "__main__":
    main()
