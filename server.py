#!/usr/bin/env python3
"""
Simple HTTP server + API for HK Pharmacist Search.
Serves static frontend and provides JSON API with search/filter/export.
Uses stdlib only (http.server, json, urllib).
"""

import json
import os
import re
import csv
import io
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
PUBLIC_DIR = BASE_DIR / "public"
CACHE_FILE = DATA_DIR / "pharmacists.json"
META_FILE = DATA_DIR / "meta.json"

PORT = int(os.environ.get("PORT", 8080))


def load_data():
    if not CACHE_FILE.exists():
        return [], {"last_updated": None, "count": 0}
    with open(CACHE_FILE, encoding="utf-8") as f:
        records = json.load(f)
    meta = {"last_updated": None, "count": len(records)}
    if META_FILE.exists():
        with open(META_FILE, encoding="utf-8") as f:
            meta = json.load(f)
    return records, meta


def parse_date(d: str):
    """DD/MM/YYYY -> sortable YYYYMMDD int or 0"""
    try:
        parts = d.strip().split("/")
        if len(parts) == 3:
            return int(parts[2]) * 10000 + int(parts[1]) * 100 + int(parts[0])
    except Exception:
        pass
    return 0


def filter_records(records, q="", year="", qual="", sort="name_asc"):
    q = (q or "").strip().lower()
    year = (year or "").strip()
    qual = (qual or "").strip().lower()

    results = []
    for r in records:
        name_l = r.get("name", "").lower()
        reg_l = r.get("reg_no", "").lower()
        qual_l = r.get("qualifications", "").lower()
        date = r.get("reg_date", "")

        if q and not (q in name_l or q in reg_l):
            continue
        if year and year not in date:
            continue
        if qual and qual not in qual_l:
            continue
        results.append(r)

    reverse = False
    key_fn = lambda x: x.get("name", "").lower()
    if sort == "name_desc":
        reverse = True
    elif sort == "date_newest":
        key_fn = lambda x: parse_date(x.get("reg_date", ""))
        reverse = True
    elif sort == "date_oldest":
        key_fn = lambda x: parse_date(x.get("reg_date", ""))
        reverse = False
    elif sort == "reg_asc":
        key_fn = lambda x: x.get("reg_no", "")
    results.sort(key=key_fn, reverse=reverse)
    return results


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {args[0]}")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/api/pharmacists" or path == "/api/search":
            self.handle_search(qs)
            return
        if path == "/api/meta":
            self.handle_meta()
            return
        if path == "/api/export":
            self.handle_export(qs)
            return
        if path == "/api/resync":
            self.handle_resync()
            return
        # Static files
        if path == "/" or path == "":
            self.path = "/index.html"
        return super().do_GET()

    def handle_meta(self):
        _, meta = load_data()
        self.send_json(meta)

    def handle_search(self, qs):
        records, meta = load_data()
        q = qs.get("q", [""])[0]
        year = qs.get("year", [""])[0]
        qual = qs.get("qual", [""])[0]
        sort = qs.get("sort", ["name_asc"])[0]
        page = int(qs.get("page", ["1"])[0] or 1)
        per_page = min(int(qs.get("per_page", ["50"])[0] or 50), 200)

        filtered = filter_records(records, q, year, qual, sort)
        total = len(filtered)
        start = (page - 1) * per_page
        end = start + per_page
        page_data = filtered[start:end]

        self.send_json({
            "data": page_data,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if per_page else 0,
            "meta": meta,
        })

    def handle_export(self, qs):
        records, _ = load_data()
        q = qs.get("q", [""])[0]
        year = qs.get("year", [""])[0]
        qual = qs.get("qual", [""])[0]
        sort = qs.get("sort", ["name_asc"])[0]
        fmt = qs.get("format", ["csv"])[0].lower()

        filtered = filter_records(records, q, year, qual, sort)

        if fmt == "json":
            body = json.dumps(filtered, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="pharmacists.json"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=["reg_no", "name", "qualifications", "reg_date"])
            writer.writeheader()
            for r in filtered:
                writer.writerow(r)
            body = output.getvalue().encode("utf-8-sig")  # BOM for Excel
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="pharmacists.csv"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def handle_resync(self):
        """Trigger on-demand re-scrape (runs in foreground; may take ~30s)."""
        try:
            from scraper import scrape_all, save_cache
            records = scrape_all(delay_between=0.8)
            if records:
                meta = save_cache(records)
                self.send_json({"ok": True, "meta": meta})
            else:
                self.send_json({"ok": False, "error": "No records scraped"}, 500)
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, 500)

    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def main():
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    records, meta = load_data()
    print(f"Loaded {meta.get('count', 0)} pharmacists (last updated: {meta.get('last_updated')})")
    print(f"Serving on http://localhost:{PORT}")
    print("API: /api/pharmacists?q=&year=&qual=&sort=&page=&per_page=")
    print("     /api/meta  /api/export?format=csv|json  /api/resync")
    httpd = HTTPServer(("", PORT), Handler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")


if __name__ == "__main__":
    main()
