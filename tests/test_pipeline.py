import unittest
from unittest.mock import MagicMock
import pandas as pd
import os
import sys
import csv

# Adjust path so we can import 'email_crawler' as a package
sys.path.append(os.path.join(os.getcwd(), 'email_crawler'))

from email_crawler.pipelines import CsvWriterPipeline

class TestCsvWriterPipeline(unittest.TestCase):
    def setUp(self):
        self.output_file = "test_output.csv"
        if os.path.exists(self.output_file):
            os.remove(self.output_file)

    def tearDown(self):
        if os.path.exists(self.output_file):
            os.remove(self.output_file)

    def test_process_item_and_streaming_save(self):
        pipeline = CsvWriterPipeline(self.output_file, dedupe=True, append=False)
        spider = MagicMock()
        spider.logger = MagicMock()

        pipeline.open_spider(spider)

        item1 = {
            'url': 'http://example.com',
            'email': 'test@example.com',
            'facebook': None,
            'original_data': {'url': 'http://example.com', 'name': 'Example'}
        }

        pipeline.process_item(item1, spider)

        with open(self.output_file, 'r') as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 2)
            self.assertIn('test@example.com', lines[1])

        pipeline.close_spider(spider)

    def test_column_merging_on_append(self):
        # 1. Create an initial CSV with some columns
        initial_data = pd.DataFrame([
            {'url': 'http://old.com', 'email': 'old@old.com', 'col_A': 'A'}
        ])
        initial_data.to_csv(self.output_file, index=False)

        # 2. Configure pipeline to append
        pipeline = CsvWriterPipeline(self.output_file, dedupe=True, append=True)
        spider = MagicMock()
        spider.logger = MagicMock()
        spider.input_file = None # No input file simulation for this test

        # 3. Open spider - this should detect schema mismatch if we were passing new columns from input
        # But here pipeline detects from process_item? No, open_spider logic handles rewriting
        # based on input file columns + core columns.
        # Let's verify open_spider adds core columns if missing.
        # 'col_A' is in file. Core columns (e.g. 'facebook') are NOT.
        # So open_spider should trigger a rewrite to add 'facebook', 'mx_ok', etc.

        pipeline.open_spider(spider)

        # Check if file was rewritten to include core columns
        df = pd.read_csv(self.output_file)
        self.assertIn('facebook', df.columns)
        self.assertIn('col_A', df.columns)
        self.assertEqual(len(df), 1) # Should still have the old row

        # 4. Process a new item
        item = {
            'url': 'http://new.com',
            'email': 'new@new.com',
            'facebook': 'fb.com/new',
            'original_data': {'url': 'http://new.com', 'col_A': 'B'}
        }
        pipeline.process_item(item, spider)

        # 5. Verify output
        df = pd.read_csv(self.output_file)
        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[1]['email'], 'new@new.com')
        self.assertEqual(df.iloc[1]['col_A'], 'B')
        self.assertEqual(df.iloc[1]['facebook'], 'fb.com/new')

        pipeline.close_spider(spider)

if __name__ == '__main__':
    unittest.main()
