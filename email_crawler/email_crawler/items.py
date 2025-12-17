import scrapy
from typing import Dict, Any, Optional

class SiteInfoItem(scrapy.Item):
    url: scrapy.Field = scrapy.Field()
    original_data: scrapy.Field = scrapy.Field()  # Store original columns as a dict

    # New columns
    email: scrapy.Field = scrapy.Field()
    facebook: scrapy.Field = scrapy.Field()
    valid_syntax: scrapy.Field = scrapy.Field()
    mx_ok: scrapy.Field = scrapy.Field()
    extracted_from_url: scrapy.Field = scrapy.Field()
