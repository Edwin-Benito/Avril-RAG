import hashlib
import json
from urllib.parse import urlparse, urljoin
import scrapy
from rag_scraper.items import NoticiaItem

class GenericSpider(scrapy.Spider):
    name = "generic"

    def __init__(self, url=None, urls=None, urls_file=None, fuente=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fuente_manual = fuente
        self.start_urls = self._cargar_urls(url=url, urls=urls, urls_file=urls_file)

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.descubrir_enlaces, meta={"base_url": url})

    def descubrir_enlaces(self, response):
        
        if "text/html" not in response.headers.get(b"Content-Type", b"").decode().lower():
            self.logger.warning(f"Saltando {response.url}: No es HTML.")
            return

        base_url = response.meta["base_url"]
        dominio_base = urlparse(base_url).netloc
        enlaces = response.css("a::attr(href)").getall()
        enlaces_limpios = set()

        for enlace in enlaces:
            url_completa = urljoin(base_url, enlace.strip())
            
            # Filtros de basura
            if any(b in url_completa for b in ['/terms-of-use/', '/privacy-policy/', '/about/', '/team/', '/portfolio/']):
                continue
            
            # Filtro de estructura
            if not any(x in url_completa for x in ['/blog/', '/news/', '/post/', '202']):
                continue
            
            if urlparse(url_completa).netloc == dominio_base:
                enlaces_limpios.add(url_completa)

        for link in enlaces_limpios:
            yield scrapy.Request(link, callback=self.parse_articulo, meta={"fuente": self.fuente_manual or dominio_base})

    def parse_articulo(self, response):
        titulo = self._extraer_titulo(response)
        keywords = ["ai", "agent", "llm", "autonomous", "startup"]
        if not titulo or not any(kw in titulo.lower() for kw in keywords):
            return 

        item = NoticiaItem()
        item["titulo"] = titulo.strip()
        item["resumen"] = self._extraer_resumen(response).strip()[:1000]
        item["url"] = response.url
        item["hash_url"] = hashlib.md5(response.url.encode()).hexdigest()
        item["fuente"] = response.meta["fuente"]
        item["fecha"] = self._extraer_fecha(response)
        yield item

    def _cargar_urls(self, url=None, urls=None, urls_file=None):
        urls_cargadas = []
        if url: urls_cargadas.append(url.strip())
        if urls: urls_cargadas.extend([u.strip() for u in urls.split(",") if u.strip()])
        if urls_file:
            with open(urls_file, encoding="utf-8") as f:
                datos = json.load(f)
                urls_cargadas.extend([f["url"] for f in datos.get("fuentes", []) if "url" in f])
        return list(set(urls_cargadas))

    def _extraer_titulo(self, response):
        return response.css("meta[property='og:title']::attr(content)").get() or response.css("h1::text").get()

    def _extraer_resumen(self, response):
        resumen = response.css("meta[property='og:description']::attr(content)").get()
        if not resumen:
            bloques = response.css("article p::text").getall()
            resumen = " ".join(bloques[:3])
        return resumen or ""

    def _extraer_fecha(self, response):
        return response.css("meta[property='article:published_time']::attr(content)").get() or ""