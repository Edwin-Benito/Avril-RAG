import hashlib
import scrapy
from rag_scraper.items import NoticiaItem

KEYWORDS = ["agentic", "ai agent", "autonomous agent", "multi-agent", "llm agent"]

# RSS de TechCrunch AI — más estable que scraping HTML directo
TC_RSS = "https://techcrunch.com/category/artificial-intelligence/feed/"


class TechCrunchSpider(scrapy.Spider):
    """
    Lee el RSS de TechCrunch AI y filtra artículos sobre agentes.
    Usa feedparser-style parsing sobre el XML del RSS.
    """

    name = "techcrunch"

    def start_requests(self):
        yield scrapy.Request(
            TC_RSS,
            callback=self.parse_rss,
            headers={"Accept": "application/rss+xml, application/xml"},
        )

    def parse_rss(self, response):
        # Parsear items del RSS con XPath
        items = response.xpath("//item")
        self.logger.info(f"[TC] {len(items)} artículos en el feed RSS")

        for item in items:
            titulo = item.xpath("title/text()").get("").strip()
            url = item.xpath("link/text()").get("").strip()
            fecha = item.xpath("pubDate/text()").get("").strip()
            resumen = item.xpath("description/text()").get("").strip()

            titulo_lower = titulo.lower()
            resumen_lower = resumen.lower()

            if not any(kw in titulo_lower or kw in resumen_lower for kw in KEYWORDS):
                continue

            if not url:
                continue

            hash_url = hashlib.md5(url.encode()).hexdigest()

            noticia = NoticiaItem()
            noticia["titulo"] = titulo
            noticia["resumen"] = resumen[:1000]
            noticia["url"] = url
            noticia["fecha"] = fecha
            noticia["fuente"] = "TechCrunch"
            noticia["hash_url"] = hash_url

            yield noticia
