#!/usr/bin/env python3
"""Download 10-K annual reports from SEC EDGAR."""

import argparse
import sys
import time
from pathlib import Path

import requests

BASE_URL = "https://data.sec.gov"
EDGAR_ARCHIVES = "https://www.sec.gov/Archives/edgar/data"
COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

HEADERS = {
    "User-Agent": "SEC10KDownloader/1.0 (your-email@example.com)",
    "Accept-Encoding": "gzip, deflate",
}

# SEC rate limit: 10 requests per second
RATE_LIMIT_DELAY = 0.15


def get_cik_by_ticker(ticker: str) -> str | None:
    """Look up CIK number by stock ticker."""
    resp = requests.get(COMPANY_TICKERS_URL, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()

    ticker_upper = ticker.upper()
    for entry in data.values():
        if entry["ticker"] == ticker_upper:
            return str(entry["cik_str"]).zfill(10)
    return None


def get_10k_filings(cik: str, count: int = 5) -> list[dict]:
    """Get list of 10-K filing metadata for a company."""
    url = f"{BASE_URL}/submissions/CIK{cik}.json"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()

    recent = data["filings"]["recent"]
    filings = []

    for i, form in enumerate(recent["form"]):
        if form == "10-K" and len(filings) < count:
            accession = recent["accessionNumber"][i].replace("-", "")
            filings.append({
                "accessionNumber": recent["accessionNumber"][i],
                "accession_nodash": accession,
                "filingDate": recent["filingDate"][i],
                "primaryDocument": recent["primaryDocument"][i],
                "cik": cik,
            })

    return filings


def download_filing(filing: dict, output_dir: Path) -> Path:
    """Download a single 10-K filing document."""
    cik = filing["cik"].lstrip("0")
    accession = filing["accession_nodash"]
    doc = filing["primaryDocument"]

    url = f"{EDGAR_ARCHIVES}/{cik}/{accession}/{doc}"

    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()

    date = filing["filingDate"]
    ext = Path(doc).suffix or ".html"
    filename = f"10K_{date}{ext}"
    filepath = output_dir / filename

    filepath.write_bytes(resp.content)
    return filepath


def main():
    parser = argparse.ArgumentParser(description="Download 10-K filings from SEC EDGAR")
    parser.add_argument("ticker", help="Stock ticker symbol (e.g. AAPL)")
    parser.add_argument("-n", "--count", type=int, default=5,
                        help="Number of filings to download (default: 5)")
    parser.add_argument("-o", "--output", default="./10k_filings",
                        help="Output directory (default: ./10k_filings)")
    parser.add_argument("--email",
                        help="Your email for SEC User-Agent (required by SEC fair access policy)")
    args = parser.parse_args()

    if args.email:
        HEADERS["User-Agent"] = f"SEC10KDownloader/1.0 ({args.email})"

    print(f"Looking up CIK for {args.ticker}...")
    cik = get_cik_by_ticker(args.ticker)
    if not cik:
        print(f"Error: Could not find CIK for ticker '{args.ticker}'", file=sys.stderr)
        sys.exit(1)
    print(f"Found CIK: {cik}")

    print("Fetching 10-K filings...")
    time.sleep(RATE_LIMIT_DELAY)
    filings = get_10k_filings(cik, args.count)
    if not filings:
        print("No 10-K filings found.", file=sys.stderr)
        sys.exit(1)
    print(f"Found {len(filings)} filing(s)")

    output_dir = Path(args.output) / args.ticker.upper()
    output_dir.mkdir(parents=True, exist_ok=True)

    for filing in filings:
        time.sleep(RATE_LIMIT_DELAY)
        print(f"  Downloading 10-K filed {filing['filingDate']}...")
        path = download_filing(filing, output_dir)
        print(f"    Saved to {path}")

    print("Done.")


if __name__ == "__main__":
    main()
