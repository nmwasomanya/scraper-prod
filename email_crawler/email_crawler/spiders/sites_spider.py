import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
import pandas as pd
from email_crawler.items import SiteInfoItem
from email_crawler.utils.email_utils import EmailUtils
import json
import os
from urllib.parse import urlparse
from typing import Any, Dict, Generator, List, Optional, Union

class SitesSpider(scrapy.Spider):
    name = "sites"

    # Keywords to identify relevant pages for contact info
    RELEVANT_PATH_KEYWORDS = [
        'contact', 'about', 'team', 'staff', 'people', 'leadership',
        'career', 'job', 'support', 'help', 'impressum', 'privacy',
        'legal', 'imprint', 'touch', 'connect'
    ]

    def __init__(self, input: Optional[str] = None, output: Optional[str] = None, *args: Any, **kwargs: Any):
        super(SitesSpider, self).__init__(*args, **kwargs)
        self.input_file = input
        self.output_file = output

        # Load skip rules
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'skip_rules.json')
        try:
            with open(config_path, 'r') as f:
                self.skip_rules = json.load(f)
        except Exception as e:
            self.logger.warning(f"Could not load skip rules: {e}")
            self.skip_rules = {}

        self.email_utils = EmailUtils(self.skip_rules)
        self.start_urls_map: Dict[str, Any] = {}

    def start_requests(self) -> Generator[scrapy.Request, None, None]:
        if not self.input_file:
            self.logger.error("No input file provided. Usage: scrapy crawl sites -a input=file.csv")
            return

        try:
            if self.input_file.endswith('.csv'):
                df = pd.read_csv(self.input_file)
            elif self.input_file.endswith('.xlsx'):
                df = pd.read_excel(self.input_file)
            else:
                self.logger.error("Unsupported file format.")
                return
        except Exception as e:
            self.logger.error(f"Error reading input file: {e}")
            return

        if 'url' not in df.columns:
            self.logger.error("Input file must contain a 'url' column.")
            return

        for index, row in df.iterrows():
            url = row['url']
            if not isinstance(url, str):
                continue
            if not url.startswith('http'):
                url = 'http://' + url

            # Store original data for passing through
            meta = {
                'original_data': row.to_dict(),
                'start_url': url,
                'depth': 0
            }

            yield scrapy.Request(url, callback=self.parse, meta=meta, errback=self.errback)

    def parse(self, response: scrapy.http.Response) -> Generator[Union[SiteInfoItem, scrapy.Request], None, None]:
        # Extract Emails
        text_body = response.text
        extracted_emails = self.email_utils.extract_emails(text_body)

        # Extract Facebook
        extracted_fb = self.email_utils.extract_facebook_urls(text_body)

        # Process Emails
        for email in extracted_emails:
            should_skip, reason = self.email_utils.should_skip(email)
            if should_skip:
                self.logger.debug(f"Skipping email {email}: {reason}")
                continue

            item = SiteInfoItem()
            item['url'] = response.meta['start_url']
            item['original_data'] = response.meta['original_data']
            item['email'] = email

            fb_links = [self.email_utils.normalize_facebook_url(fb) for fb in extracted_fb]
            fb_str = fb_links[0] if fb_links else None

            item['facebook'] = fb_str
            item['extracted_from_url'] = response.url
            item['valid_syntax'] = self.email_utils.is_valid_syntax(email)
            item['mx_ok'] = None

            yield item

        if not extracted_emails and extracted_fb:
            item = SiteInfoItem()
            item['url'] = response.meta['start_url']
            item['original_data'] = response.meta['original_data']
            item['email'] = None

            fb_links = [self.email_utils.normalize_facebook_url(fb) for fb in extracted_fb]
            item['facebook'] = fb_links[0] if fb_links else None
            item['extracted_from_url'] = response.url
            item['valid_syntax'] = None
            item['mx_ok'] = None
            yield item

        # Crawl Logic: Depth <= 2, Smart Filtering
        depth = response.meta.get('depth', 0)
        if depth < 2:
            le = LinkExtractor(allow_domains=urlparse(response.url).netloc)
            links = le.extract_links(response)

            for link in links:
                # Smart filtering: Check if link matches keywords
                # We check URL and Text
                lower_url = link.url.lower()
                lower_text = link.text.lower()

                is_relevant = False
                for kw in self.RELEVANT_PATH_KEYWORDS:
                    if kw in lower_url or kw in lower_text:
                        is_relevant = True
                        break

                # Special case: If depth is 0 (Home Page), we might want to be slightly more lenient
                # or strictly enforce keywords. The user said "crawl the home page and then it smartly crawls..."
                # This implies from home page we only go to relevant pages.

                if is_relevant:
                    yield scrapy.Request(
                        link.url,
                        callback=self.parse,
                        meta={
                            'original_data': response.meta['original_data'],
                            'start_url': response.meta['start_url'],
                            'depth': depth + 1
                        }
                    )

    def errback(self, failure: Any) -> None:
        self.logger.error(f"Request failed: {failure.request.url}, {failure.value}")
