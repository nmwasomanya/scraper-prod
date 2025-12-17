FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if needed (e.g. for playwright or building deps)
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install playwright browsers if using playwright
# RUN playwright install chromium

COPY . .

# Default command (overridden by docker run arguments)
CMD ["scrapy", "crawl", "sites"]
