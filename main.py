import json
import argparse
import subprocess
import os
import tempfile
import time
import logging
import glob

from distilador import destilar, validar, tiene_contenido_util
from supabase_client import insertar_idea, contar_ideas

# Configuración de logs
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # stdout → journalctl en systemd
        logging.FileHandler('avril-rag.log')  # También guardar localmente
    ]
)
logger = logging.getLogger(__name__)

# Integrar journalctl si está disponible (producción)
try:
    from systemd.journal import JournalHandler
    journal_handler = JournalHandler()
    journal_handler.setFormatter(logging.Formatter('%(name)s: %(message)s'))
    logger.addHandler(journal_handler)
except ImportError:
    logger.debug("systemd.journal no disponible (OK si es desarrollo local)")

# Ruta absoluta a la raíz del proyecto
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def obtener_todos_los_spiders():
    spider_dir = os.path.join(ROOT_DIR, "rag_scraper", "rag_scraper", "spiders")
    archivos = glob.glob(os.path.join(spider_dir, "*_spider.py"))
    return [os.path.basename(f).replace("_spider.py", "") for f in archivos]

def ejecutar_pipeline_completo(limite_noticias):
    spiders = obtener_todos_los_spiders()
    logger.info(f"Detectados {len(spiders)} spiders: {', '.join(spiders)}")
    
    # --- FASE 1: Scraping ---
    logger.info("[FASE 1] Ejecutando todos los scrapers...")
    spider_dir = os.path.join(ROOT_DIR, "rag_scraper")
    noticias_totales = []
    
    with tempfile.TemporaryDirectory() as temp_dir:
        for spider in spiders:
            salida = os.path.join(temp_dir, f"{spider}.json")
            comando = ["scrapy", "crawl", spider, "-o", salida, "--logfile", "../scrapy.log"]
            
            if spider == "generic":
                comando.extend(["-a", f"urls_file={os.path.join(ROOT_DIR, 'urls_fuentes.json')}"])
            
            subprocess.run(comando, cwd=spider_dir, capture_output=True)
            
            if os.path.exists(salida):
                with open(salida, encoding="utf-8") as f:
                    noticias_totales.extend(json.load(f))
                logger.info(f"  [OK] Spider '{spider}' terminó.")

    # Guardar noticias.json en la raíz absoluta
    ruta_noticias = os.path.join(ROOT_DIR, "noticias.json")
    with open(ruta_noticias, "w", encoding="utf-8") as f:
        json.dump(noticias_totales, f, ensure_ascii=False, indent=2)

    # --- FASE 2 y 3: Destilación ---
    logger.info(f"[FASE 2/3] Destilando...")
    noticias_utiles = [n for n in noticias_totales if tiene_contenido_util(n)]
    if limite_noticias:
        noticias_utiles = noticias_utiles[:limite_noticias]
        
    ideas_validas = []
    for noticia in noticias_utiles:
        data = destilar(noticia)
        contrato = validar(data)
        if contrato:
            idea = contrato.model_dump(mode="json", exclude_none=True)
            idea["_pipeline"] = {"status": "borrador", "hash_origen": noticia["hash_url"]}
            ideas_validas.append(idea)
            logger.info(f"    [OK] Destilada: {contrato.metadata.nombre}")
            time.sleep(1.5)

    # ---  Guardar borrador local ---
    ruta_borrador = os.path.join(ROOT_DIR, "ideas_borrador.json")
    with open(ruta_borrador, "w", encoding="utf-8") as f:
        json.dump(ideas_validas, f, ensure_ascii=False, indent=2)
    logger.info(f"[ARCHIVO] Borrador guardado en: {ruta_borrador}")

    # --- FASE 4: Inserción ---
    logger.info("[FASE 4] Insertando en Supabase...")
    for idea in ideas_validas:
        res = insertar_idea(idea)
        status = "INSERT" if res.get("accion") == "insertada" else "DEDUP"
        logger.info(f"    [{status}] {idea['metadata']['nombre']}")

    logger.info("Pipeline completado.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limite", type=int, default=10, help="Max noticias a procesar")
    args = parser.parse_args()
    
    ejecutar_pipeline_completo(args.limite)