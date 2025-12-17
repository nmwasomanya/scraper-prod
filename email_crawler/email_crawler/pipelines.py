import pandas as pd
import os
import csv
import asyncio
from concurrent.futures import ThreadPoolExecutor
from email_crawler.utils.email_utils import EmailUtils
from typing import List, Set, Any, Dict, Optional, Union
from scrapy import Spider, Item

class EmailValidationPipeline:
    def __init__(self, mx_check: bool):
        self.mx_check = mx_check
        self.email_utils = EmailUtils()
        self.executor = ThreadPoolExecutor(max_workers=10)

    @classmethod
    def from_crawler(cls, crawler) -> 'EmailValidationPipeline':
        mx_check = crawler.settings.getbool('MX_CHECK', False)
        return cls(mx_check)

    async def process_item(self, item: Dict[str, Any], spider: Spider) -> Dict[str, Any]:
        if item.get('email') and self.mx_check:
            loop = asyncio.get_running_loop()
            mx_ok = await loop.run_in_executor(
                self.executor,
                self.email_utils.check_mx_record,
                item['email']
            )
            item['mx_ok'] = mx_ok
        else:
            item['mx_ok'] = None
        return item

    def close_spider(self, spider: Spider) -> None:
        self.executor.shutdown()


class CsvWriterPipeline:
    def __init__(self, output_file: str, dedupe: bool, append: bool):
        self.output_file = output_file
        self.dedupe = dedupe
        self.append = append
        self.seen_keys: Set[tuple] = set()
        self.buffer: List[Dict[str, Any]] = []
        self.is_csv = output_file.endswith('.csv')
        self.file_handle = None
        self.writer = None
        # Default core headers
        self.core_headers = ['url', 'email', 'facebook', 'valid_syntax', 'mx_ok', 'extracted_from_url']
        self.csv_columns: List[str] = []
        self.write_header = False

    @classmethod
    def from_crawler(cls, crawler) -> 'CsvWriterPipeline':
        output_file = getattr(crawler.spider, 'output_file', 'output.csv') or 'output.csv'
        dedupe = crawler.settings.getbool('DEDUPE', True)
        append = crawler.settings.getbool('APPEND', True)
        return cls(output_file, dedupe, append)

    def open_spider(self, spider: Spider) -> None:
        if self.dedupe and os.path.exists(self.output_file):
            try:
                if self.is_csv:
                    df = pd.read_csv(self.output_file)
                else:
                    df = pd.read_parquet(self.output_file)

                if 'url' in df.columns and 'email' in df.columns:
                    df['email'] = df['email'].fillna('')
                    self.seen_keys = set(zip(df['url'], df['email']))
                    spider.logger.info(f"Loaded {len(self.seen_keys)} existing records for deduplication.")
            except Exception as e:
                spider.logger.warning(f"Could not read existing file for deduplication: {e}")

        if self.is_csv:
            # Check for column merging needs
            existing_columns = []
            if self.append and os.path.exists(self.output_file) and os.path.getsize(self.output_file) > 0:
                try:
                    with open(self.output_file, 'r', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        existing_columns = next(reader)
                except:
                    pass

            # Identify all possible columns from input file to prepare header
            input_file = getattr(spider, 'input_file', None)
            input_columns = []
            if input_file:
                try:
                    if input_file.endswith('.csv'):
                        input_columns = list(pd.read_csv(input_file, nrows=0).columns)
                    elif input_file.endswith('.xlsx'):
                        input_columns = list(pd.read_excel(input_file, nrows=0).columns)
                except:
                    pass

            # Combine columns
            all_columns = list(existing_columns)

            # Add input columns if not present
            for col in input_columns:
                if col not in all_columns:
                    all_columns.append(col)

            # Add core headers if not present
            for col in self.core_headers:
                if col not in all_columns:
                    all_columns.append(col)

            self.csv_columns = all_columns

            # If we have new columns and we are appending, we might need to rewrite the file to add headers
            if self.append and existing_columns and set(existing_columns) != set(all_columns):
                 spider.logger.info("Schema change detected. Rewriting existing file to include new columns.")
                 try:
                     # Read all data
                     df = pd.read_csv(self.output_file)
                     # Add missing columns
                     for col in self.csv_columns:
                         if col not in df.columns:
                             df[col] = ''
                     # Re-save with new columns
                     df.to_csv(self.output_file, index=False, columns=self.csv_columns)
                 except Exception as e:
                     spider.logger.error(f"Failed to rewrite file for schema update: {e}")

            # Open file
            mode = 'a' if self.append and os.path.exists(self.output_file) else 'w'
            self.file_handle = open(self.output_file, mode, newline='', encoding='utf-8')
            self.writer = csv.writer(self.file_handle)

            # Write header if new file
            if mode == 'w' or os.path.getsize(self.output_file) == 0:
                self.write_header = True

    def process_item(self, item: Dict[str, Any], spider: Spider) -> Dict[str, Any]:
        flat_item = item.get('original_data', {}).copy()
        flat_item.update({
            'email': item.get('email'),
            'facebook': item.get('facebook'),
            'valid_syntax': item.get('valid_syntax'),
            'mx_ok': item.get('mx_ok'),
            'extracted_from_url': item.get('extracted_from_url')
        })
        flat_item['url'] = item['url']

        key = (flat_item['url'], flat_item.get('email') or '')
        if self.dedupe:
            if key in self.seen_keys:
                return item
            self.seen_keys.add(key)

        if self.is_csv:
            self._write_csv_row(flat_item, spider)
        else:
            self.buffer.append(flat_item)

        return item

    def _write_csv_row(self, flat_item: Dict[str, Any], spider: Spider) -> None:
        if not self.file_handle:
            return

        if self.write_header:
            if self.writer:
                self.writer.writerow(self.csv_columns)
            self.write_header = False

        row = [flat_item.get(col, '') for col in self.csv_columns]
        if self.writer:
            self.writer.writerow(row)
            self.file_handle.flush()

    def close_spider(self, spider: Spider) -> None:
        if self.is_csv:
            if self.file_handle:
                self.file_handle.close()
        else:
            if not self.buffer:
                return

            new_df = pd.DataFrame(self.buffer)

            if self.append and os.path.exists(self.output_file):
                try:
                    existing_df = pd.read_parquet(self.output_file)
                    combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                except Exception as e:
                    spider.logger.error(f"Error reading existing parquet file: {e}. Overwriting/Creating new.")
                    combined_df = new_df
            else:
                combined_df = new_df

            combined_df.to_parquet(self.output_file, index=False)
            spider.logger.info(f"Saved {len(combined_df)} rows to {self.output_file}")
