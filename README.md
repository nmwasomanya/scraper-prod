# Email & Facebook Link Crawler

A production-grade Scrapy project designed to crawl a list of websites, extract emails and Facebook links, validate them, and save the results.

## Features

- **High Performance:** Tuned for high concurrency (128 concurrent requests) on standard hardware.
- **Input:** Accepts CSV or XLSX files with a `url` column.
- **Output:**
  - Streaming CSV updates to prevent data loss.
  - Dynamically updates schema (adds columns) if new fields are detected or input changes.
  - Appends to existing files and deduplicates results based on `url` + `email`.
- **Extraction:**
  - Emails (mailto, plain text, obfuscated like `user [at] domain`).
  - Facebook URLs (regex-based extraction).
- **Filtering:** Skips unwanted emails (generic prefixes, specific domains) based on `config/skip_rules.json`.
- **Validation:**
  - Syntax check (using `email-validator`).
  - Optional Asynchronous MX record check (using `dnspython` in a thread pool).
- **Robots.txt:** Ignored by default (`ROBOTSTXT_OBEY = False`). Can be enabled via settings.

## Installation

1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   Note: Requires `pyarrow` for Parquet support (included in requirements).

## Usage

### Basic Crawl

```bash
cd email_crawler
scrapy crawl sites -a input=../data/input.csv -a output=../data/output.csv
```

### Advanced Options

- **MX Check:** Enable MX record validation. This runs asynchronously to avoid blocking the crawler.
  ```bash
  scrapy crawl sites -a input=../data/input.csv -s MX_CHECK=True
  ```
- **Respect Robots.txt:** Enable `robots.txt` compliance.
  ```bash
  scrapy crawl sites -a input=../data/input.csv -s ROBOTSTXT_OBEY=True
  ```
- **Disable Append:** Overwrite output file instead of appending.
  ```bash
  scrapy crawl sites -a input=../data/input.csv -s APPEND=False
  ```
- **Disable Deduplication:** Keep all duplicates.
  ```bash
  scrapy crawl sites -a input=../data/input.csv -s DEDUPE=False
  ```

## Docker

Build the image:
```bash
docker build -t email_crawler .
```

Run the crawler:
```bash
docker run -v $(pwd)/data:/app/data email_crawler scrapy crawl sites -a input=data/input.csv -a output=data/output.csv
```

## Configuration

- **Skip Rules:** Edit `email_crawler/config/skip_rules.json` to manage ignored domains and prefixes.
- **Concurrency:** Adjust settings in `email_crawler/settings.py`.
- **Reactor:** Uses `AsyncioSelectorReactor` to support async MX checks alongside Scrapy's twisted reactor.

## Design Notes

- **Robots.txt:** Disabled by default to ensure maximum coverage. Use `-s ROBOTSTXT_OBEY=True` to enable.
- **Data Safety:** The CSV pipeline streams rows immediately to disk. If the crawler crashes, data crawled up to that point is saved.
- **Schema Merging:** If the crawler is run in append mode and detects new columns (either from a new input file with extra columns or internal logic), it will rewrite the output file header to include these new columns before appending new data.
- **Async Processing:** MX checks use `asyncio` and `ThreadPoolExecutor` to perform DNS lookups without blocking the main Scrapy event loop.

## Ethical Usage

Please respect website terms of service and privacy policies. This tool is for educational and legitimate data gathering purposes.
