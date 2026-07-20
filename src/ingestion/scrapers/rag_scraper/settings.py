BOT_NAME = "rag_scraper"
SPIDER_MODULES = ["rag_scraper.spiders"]
NEWSPIDER_MODULE = "rag_scraper.spiders"

# Respetar robots.txt
ROBOTSTXT_OBEY = True

# Rate limiting — no saturar fuentes
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 2

# Headers para identificarse correctamente
DEFAULT_REQUEST_HEADERS = {
    "Accept": "application/json, text/html;q=0.9",
    "Accept-Language": "en-US,en;q=0.9",
}

# Pipeline activo: primero dedup, luego guarda
ITEM_PIPELINES = {
    "rag_scraper.pipelines.DedupPipeline": 100,
}

# Logs solo nivel WARNING en consola
LOG_LEVEL = "WARNING"

# Formato de salida
FEED_EXPORT_ENCODING = "utf-8"

PRODUCTHUNT_TOKEN = "1SfEbPrZwHrSgFWVpNSC9bGri98c-LKBpzvvw2UyDe0"

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
