import hashlib
import json
import scrapy
from rag_scraper.items import NoticiaItem

KEYWORDS = ["agentic", "agent", "ai agent", "autonomous", "llm"]

class ProductHuntSpider(scrapy.Spider):
    
    name = "producthunt"
    
    # Endpoint público/oficial de la API v2 de Product Hunt
    API_URL = "https://api.producthunt.com/v2/api/graphql"
    
    
    custom_settings = {
        "ROBOTSTXT_OBEY": False
    }

    def start_requests(self):
        # Query de GraphQL para obtener los posts más recientes
        query = """
        {
          posts(first: 20) {
            edges {
              node {
                id
                name
                tagline
                description
                url
                createdAt
              }
            }
          }
        }
        """
       
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.settings.get('PRODUCTHUNT_TOKEN')}",
            "Accept": "application/json"
        }
        
        yield scrapy.Request(
            url=self.API_URL,
            method="POST",
            headers=headers,
            body=json.dumps({"query": query}),
            callback=self.parse
        )

    def parse(self, response):
        try:
            data = response.json()
            posts = data.get("data", {}).get("posts", {}).get("edges", [])
            self.logger.info(f"[PH] {len(posts)} posts obtenidos de GraphQL")
        except json.JSONDecodeError:
            self.logger.error("[PH] Error al decodificar la respuesta JSON de Product Hunt.")
            return

        for edge in posts:
            node = edge.get("node", {})
            titulo = node.get("name", "")
            tagline = node.get("tagline", "")
            descripcion = node.get("description", "") or tagline
            url = node.get("url", "")
            fecha = node.get("createdAt", "")

            # Unir título y descripción para buscar nuestras keywords
            texto_completo = f"{titulo} {descripcion}".lower()
            
            if not any(kw in texto_completo for kw in KEYWORDS):
                continue

            if not url:
                continue

            hash_url = hashlib.md5(url.encode()).hexdigest()

            item = NoticiaItem()
            item["titulo"] = titulo
            item["resumen"] = descripcion[:1000]
            item["url"] = url
            item["fecha"] = fecha
            item["fuente"] = "Product Hunt"
            item["hash_url"] = hash_url

            yield item