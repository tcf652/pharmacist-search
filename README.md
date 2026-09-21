# HK Registered Pharmacists Search

Modern, responsive web application for searching the official list of Registered Pharmacists published by the **Pharmacy and Poisons Board of Hong Kong (PPBHK)**.

**Official source:** https://www.ppbhk.org.hk/eng/list_pharmacists/list.php

## Features

- **Full scrape** of all letter pages (A–Z) with polite delays & retries
- **Local JSON cache** with last-updated timestamp
- **On-demand re-sync** button / API
- Real-time search by English name, Chinese name, or Registration No.
- Filters: Registration year, Qualification keyword (e.g. CUHK, HKU, London)
- Sorting: Name A–Z / Z–A, Registration Date newest/oldest, Reg. No.
- Pagination, keyword highlighting
- Export current results to **CSV** or **JSON**
- Mandatory PPBHK Personal Data (Privacy) Ordinance disclaimer
- Pure Python 3 stdlib (no external dependencies) + Tailwind CDN frontend

## Quick Start

```bash
# 1. Clone
git clone https://github.com/tcf652/pharmacist-search.git
cd pharmacist-search

# 2. Scrape data (first time or when you want a fresh copy)
python3 scraper.py
# → creates data/pharmacists.json (~4,000+ records, takes ~30–40 s)

# 3. Start the server
python3 server.py
# → http://localhost:8080

# Optional: custom port
PORT=3000 python3 server.py
```

### Scripts

| Command | Description |
|---------|-------------|
| `python3 scraper.py` | Full re-scrape A–Z and overwrite cache |
| `python3 server.py`  | Start web UI + API on port 8080 |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/pharmacists?q=&year=&qual=&sort=&page=&per_page=` | Search / filter / paginate |
| `GET /api/meta` | Last-updated timestamp & record count |
| `GET /api/export?format=csv\|json&q=&…` | Download filtered results |
| `GET /api/resync` | Trigger live re-scrape (blocking, ~30 s) |

### Sort values
- `name_asc` (default), `name_desc`
- `date_newest`, `date_oldest`
- `reg_asc`

## Data Schema

```json
{
  "reg_no": "P00581",
  "name": "GAN, SIANG HWA LISA\n顏聖華",
  "qualifications": "2021: Bachelor of Pharmacy, …",
  "reg_date": "05/07/2022"
}
```

## Project Structure

```
pharmacist-search/
├── scraper.py          # A–Z scraper + JSON cache writer
├── server.py           # HTTP server + REST API (stdlib)
├── public/
│   └── index.html      # Modern responsive UI (Tailwind)
├── data/               # Generated (gitignored)
│   ├── pharmacists.json
│   └── meta.json
└── README.md
```

## Legal Notice

The purpose of publishing the list of registered pharmacists is to inform the public that each person named in the list is entitled to practise pharmacy in Hong Kong under the Pharmacy and Poisons Ordinance (Chapter 138).  
Persons using the personal data therein for an unrelated purpose render themselves liable to action under the Personal Data (Privacy) Ordinance (Chapter 486).

This project is an **unofficial convenience mirror**. Always verify critical information against the official PPBHK website.

## License

MIT (code only). Source data remains the property of the Pharmacy and Poisons Board of Hong Kong.
