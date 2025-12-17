BOT_NAME = 'email_crawler'

SPIDER_MODULES = ['email_crawler.spiders']
NEWSPIDER_MODULE = 'email_crawler.spiders'

# Obey robots.txt rules
# Default is False as per requirements.
# To enable, run with: scrapy crawl sites -s ROBOTSTXT_OBEY=True
ROBOTSTXT_OBEY = False

# Reactor Configuration for Asyncio (required for async pipeline)
TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'

# Concurrency & Performance
CONCURRENT_REQUESTS = 128
CONCURRENT_REQUESTS_PER_DOMAIN = 8
REACTOR_THREADPOOL_MAXSIZE = 32

# AutoThrottle
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.1
AUTOTHROTTLE_MAX_DELAY = 1.5
AUTOTHROTTLE_TARGET_CONCURRENCY = 64

# Timeouts & Retries
DOWNLOAD_TIMEOUT = 15
RETRY_TIMES = 3

# DNS
DNSCACHE_ENABLED = True

# Cookies (Disabled for performance unless needed)
COOKIES_ENABLED = False

# Telemetry
TELNETCONSOLE_ENABLED = False

# Pipelines
ITEM_PIPELINES = {
   'email_crawler.pipelines.EmailValidationPipeline': 300,
   'email_crawler.pipelines.CsvWriterPipeline': 500,
}

# Middlewares
# Enable common middlewares.
# Optional: Proxy middleware could be added here.

# Logging
LOG_LEVEL = 'INFO'

# Custom Settings Defaults
MX_CHECK = False
APPEND = True
DEDUPE = True
