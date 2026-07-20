import scrapy.exceptions


class DedupPipeline:
    """
    Descarta noticias cuyo hash_url ya fue procesado en esta ejecución.
    La deduplicación persistente entre semanas se hace en Supabase
    (campo url_hash con índice único).
    """

    def __init__(self):
        self.vistos = set()

    def process_item(self, item, spider):
        if item["hash_url"] in self.vistos:
            raise scrapy.exceptions.DropItem(
                f"[DEDUP] Duplicado descartado: {item['titulo'][:60]}"
            )
        self.vistos.add(item["hash_url"])
        return item
