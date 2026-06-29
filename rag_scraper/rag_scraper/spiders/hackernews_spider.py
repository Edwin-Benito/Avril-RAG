import hashlib
import scrapy
from rag_scraper.items import NoticiaItem

ALGOLIA_URL = (
    "https://hn.algolia.com/api/v1/search"
    "?query={query}&tags=story&hitsPerPage=30"
)

KEYWORDS = ["agentic", "ai agent", "autonomous agent", "multi-agent", "llm agent"]


class HackerNewsSpider(scrapy.Spider):
    """
    Consulta la API oficial de Algolia (Hacker News Search) — sin scraping directo.
    Devuelve stories que mencionan agentes de IA, filtrando por keywords.
    """

    name = "hackernews"
    custom_settings = {
        "ROBOTSTXT_OBEY": False,  # Es API oficial, no scraping HTML
    }

    def start_requests(self):
        queries = ["agentic AI", "AI agents startup", "autonomous agents business"]
        for q in queries:
            url = ALGOLIA_URL.format(query=q.replace(" ", "+"))
            yield scrapy.Request(url, callback=self.parse, cb_kwargs={"query": q})

    def parse(self, response, query=""):
        data = response.json()
        hits = data.get("hits", [])
        self.logger.info(f"[HN] Query '{query}' → {len(hits)} resultados")

        for hit in hits:
            titulo = hit.get("title", "")
            url = hit.get("url") or hit.get("story_url") or ""
            fecha = hit.get("created_at", "")
            resumen = hit.get("story_text") or titulo

            # Filtrar por keywords en título
            titulo_lower = titulo.lower()
            if not any(kw in titulo_lower for kw in KEYWORDS):
                continue

            if not url:
                continue

            hash_url = hashlib.md5(url.encode()).hexdigest()

            item = NoticiaItem()
            item["titulo"] = titulo
            item["resumen"] = resumen[:1000]
            item["url"] = url
            item["fecha"] = fecha
            item["fuente"] = "Hacker News"
            item["hash_url"] = hash_url

            yield item
