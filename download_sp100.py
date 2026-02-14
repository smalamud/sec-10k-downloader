#!/usr/bin/env python3
"""Download 10-K filings for all S&P 100 companies."""

import time
import sys
from pathlib import Path

from downloader import get_cik_by_ticker, get_10k_filings, download_filing, HEADERS, RATE_LIMIT_DELAY

# S&P 100 tickers (as of early 2025)
SP100_TICKERS = [
    "AAPL", "ABBV", "ABT", "ACN", "ADBE", "AIG", "AMD", "AMGN", "AMT", "AMZN",
    "AVGO", "AXP", "BA", "BAC", "BK", "BKNG", "BLK", "BMY", "BRK.B", "C",
    "CAT", "CHTR", "CL", "CMCSA", "COF", "COP", "COST", "CRM", "CSCO", "CVS",
    "CVX", "DE", "DHR", "DIS", "DOW", "DUK", "EMR", "EXC", "F", "FDX",
    "GD", "GE", "GILD", "GM", "GOOG", "GS", "HD", "HON", "IBM", "INTC",
    "INTU", "JNJ", "JPM", "KHC", "KO", "LIN", "LLY", "LMT", "LOW", "MA",
    "MCD", "MDLZ", "MDT", "MET", "META", "MMM", "MO", "MRK", "MS", "MSFT",
    "NEE", "NFLX", "NKE", "NVDA", "ORCL", "PEP", "PFE", "PG", "PM", "PYPL",
    "QCOM", "RTX", "SBUX", "SCHW", "SO", "SPG", "T", "TGT", "TMO", "TMUS",
    "TXN", "UNH", "UNP", "UPS", "USB", "V", "VZ", "WFC", "WMT", "XOM",
]

OUTPUT_DIR = Path("./10k_filings")
COUNT = 5


def main():
    email = sys.argv[1] if len(sys.argv) > 1 else None
    if email:
        HEADERS["User-Agent"] = f"SEC10KDownloader/1.0 ({email})"

    # Find which tickers already have filings downloaded
    existing = {d.name for d in OUTPUT_DIR.iterdir() if d.is_dir()} if OUTPUT_DIR.exists() else set()
    remaining = [t for t in SP100_TICKERS if t not in existing]

    print(f"S&P 100: {len(SP100_TICKERS)} companies total")
    print(f"Already downloaded: {len(existing)} ({', '.join(sorted(existing))})")
    print(f"Remaining: {len(remaining)}")
    print()

    failed = []

    for i, ticker in enumerate(remaining):
        print(f"[{i+1}/{len(remaining)}] {ticker}...")

        try:
            cik = get_cik_by_ticker(ticker)
            time.sleep(RATE_LIMIT_DELAY)

            if not cik:
                print(f"  WARNING: Could not find CIK for {ticker}, skipping")
                failed.append((ticker, "CIK not found"))
                continue

            filings = get_10k_filings(cik, COUNT)
            time.sleep(RATE_LIMIT_DELAY)

            if not filings:
                print(f"  WARNING: No 10-K filings found for {ticker}")
                failed.append((ticker, "No 10-K filings"))
                continue

            ticker_dir = OUTPUT_DIR / ticker
            ticker_dir.mkdir(parents=True, exist_ok=True)

            for filing in filings:
                time.sleep(RATE_LIMIT_DELAY)
                path = download_filing(filing, ticker_dir)
                print(f"  {filing['filingDate']} -> {path.name}")

        except Exception as e:
            print(f"  ERROR: {e}")
            failed.append((ticker, str(e)))
            continue

    print(f"\nDone! Downloaded {len(remaining) - len(failed)}/{len(remaining)} companies.")
    if failed:
        print(f"\nFailed ({len(failed)}):")
        for ticker, reason in failed:
            print(f"  {ticker}: {reason}")


if __name__ == "__main__":
    main()
