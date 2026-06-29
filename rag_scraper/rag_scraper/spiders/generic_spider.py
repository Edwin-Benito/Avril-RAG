import hashlib
import json
from urllib.parse import urlparse

import scrapy

from rag_scraper.items import NoticiaItem


class GenericSpider(scrapy.Spider):
    name = "generic"

    def __init__(self, url=None, urls=None, urls_file=None, fuente=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fuente = fuente
        self.start_urls = self._cargar_urls(url=url, urls=urls, urls_file=urls_file)

        if not self.start_urls:
            raise ValueError("Debes pasar una URL con -a url=..., -a urls=... o -a urls_file=...")

        if not self.fuente:
            self.fuente = self._inferir_fuente(self.start_urls[0])

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        titulo = self._extraer_titulo(response)
        resumen = self._extraer_resumen(response)
        fecha = self._extraer_fecha(response)

        if not titulo:
            titulo = response.url

        if not resumen:
            resumen = titulo

        hash_url = hashlib.md5(response.url.encode()).hexdigest()

        item = NoticiaItem()
        item["titulo"] = titulo.strip()
        item["resumen"] = resumen.strip()[:1000]
        item["url"] = response.url
        item["fecha"] = fecha
        item["fuente"] = self.fuente
        item["hash_url"] = hash_url

        yield item

    def _cargar_urls(self, url=None, urls=None, urls_file=None):
        urls_cargadas = []

        if url:
            urls_cargadas.append(url.strip())

        if urls:
            for candidato in urls.split(","):
                candidato = candidato.strip()
                if candidato:
                    urls_cargadas.append(candidato)

        if urls_file:
            with open(urls_file, encoding="utf-8") as archivo:
                contenido = archivo.read().strip()

            if not contenido:
                return urls_cargadas

            if urls_file.lower().endswith(".json"):
                datos = json.loads(contenido)
                if isinstance(datos, list):
                    for item in datos:
                        if isinstance(item, str):
                            item = item.strip()
                            if item:
                                urls_cargadas.append(item)
                        elif isinstance(item, dict):
                            url_item = str(item.get("url", "")).strip()
                            if url_item:
                                urls_cargadas.append(url_item)
                elif isinstance(datos, dict):
                    for clave in ("urls", "links"):
                        valor = datos.get(clave)
                        if isinstance(valor, list):
                            for item in valor:
                                if isinstance(item, str):
                                    item = item.strip()
                                    if item:
                                        urls_cargadas.append(item)
                                elif isinstance(item, dict):
                                    url_item = str(item.get("url", "")).strip()
                                    if url_item:
                                        urls_cargadas.append(url_item)
                    fuentes = datos.get("fuentes")
                    if isinstance(fuentes, list):
                        for item in fuentes:
                            if isinstance(item, str):
                                item = item.strip()
                                if item:
                                    urls_cargadas.append(item)
                            elif isinstance(item, dict):
                                url_item = str(item.get("url", "")).strip()
                                if url_item:
                                    urls_cargadas.append(url_item)
            else:
                for linea in contenido.splitlines():
                    linea = linea.strip()
                    if linea and not linea.startswith("#"):
                        urls_cargadas.append(linea)

        urls_limpias = []
        vistos = set()
        for candidato in urls_cargadas:
            if candidato and candidato not in vistos:
                vistos.add(candidato)
                urls_limpias.append(candidato)

        return urls_limpias

    def _inferir_fuente(self, url):
        dominio = urlparse(url).netloc.replace("www.", "")
        return dominio or "Fuente genérica"

    def _extraer_titulo(self, response):
        candidatos = [
            response.css("meta[property='og:title']::attr(content)").get(),
            response.css("meta[name='twitter:title']::attr(content)").get(),
            response.css("title::text").get(),
            response.css("h1::text").get(),
        ]
        for candidato in candidatos:
            if candidato and candidato.strip():
                return candidato.strip()
        return ""

    def _extraer_resumen(self, response):
        candidatos = [
            response.css("meta[property='og:description']::attr(content)").get(),
            response.css("meta[name='description']::attr(content)").get(),
            response.css("meta[name='twitter:description']::attr(content)").get(),
        ]

        for candidato in candidatos:
            if candidato and candidato.strip():
                return candidato.strip()

        bloques = response.css("article p, main p, .content p, .post p, p")
        parrafos = []
        for bloque in bloques:
            texto = " ".join(bloque.css("::text").getall()).strip()
            texto = " ".join(texto.split())
            if len(texto) >= 80:
                parrafos.append(texto)
            if len(" ".join(parrafos)) >= 1000:
                break

        return "\n\n".join(parrafos)

    def _extraer_fecha(self, response):
        candidatos = [
            response.css("meta[property='article:published_time']::attr(content)").get(),
            response.css("meta[name='pubdate']::attr(content)").get(),
            response.css("meta[name='date']::attr(content)").get(),
            response.css("time::attr(datetime)").get(),
            response.css("time::text").get(),
        ]
        for candidato in candidatos:
            if candidato and candidato.strip():
                return candidato.strip()
        return ""