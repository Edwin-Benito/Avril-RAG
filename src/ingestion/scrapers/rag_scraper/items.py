import scrapy


class NoticiaItem(scrapy.Item):
    titulo = scrapy.Field()
    resumen = scrapy.Field()
    url = scrapy.Field()
    fecha = scrapy.Field()
    fuente = scrapy.Field()
    hash_url = scrapy.Field()
