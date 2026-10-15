"""Download every USAID prime transaction performed in Haiti, FY2010-FY2025, from USAspending.gov.

Uses the public USAspending custom-download endpoint (no key needed). The request
filters are written next to the zip so anyone can see exactly what was asked for.

    python fetch.py                     # writes data/raw/<dated zip> + request json
"""
import datetime as dt
import hashlib
import json
import pathlib
import time

import requests

API = "https://api.usaspending.gov/api/v2/download/transactions/"
RAW = pathlib.Path(__file__).parent / "data" / "raw"

FILTERS = {
    "agencies": [{"type": "awarding", "tier": "toptier",
                  "name": "Agency for International Development"}],
    "place_of_performance_locations": [{"country": "HTI"}],
    # FY2010 (starts Oct 1, 2009, the year of the earthquake response) through FY2025
    "time_period": [{"start_date": "2009-10-01", "end_date": "2025-09-30"}],
    # contracts (A-D) and all assistance types; IDVs excluded (vehicles, not obligations)
    "award_type_codes": ["A", "B", "C", "D",
                         "02", "03", "04", "05", "06", "07", "08", "09", "10", "11"],
}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()
    job = requests.post(API, json={"filters": FILTERS, "file_format": "csv", "limit": 500000},
                        timeout=120)
    job.raise_for_status()
    job = job.json()
    (RAW / f"download_request_{today}.json").write_text(json.dumps(job, indent=1))

    while True:
        status = requests.get(job["status_url"], timeout=60).json()
        print(f"  {status['status']}: {status.get('total_rows')} rows")
        if status["status"] == "finished":
            break
        if status["status"] == "failed":
            raise SystemExit(status.get("message"))
        time.sleep(15)

    blob = requests.get(job["file_url"], timeout=600).content
    out = RAW / f"usaspending_usaid_haiti_fy2010-2025_pulled-{today}.zip"
    out.write_bytes(blob)
    print(f"wrote {out} ({len(blob):,} bytes, sha256 {hashlib.sha256(blob).hexdigest()[:16]})")


if __name__ == "__main__":
    main()
