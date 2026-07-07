import json
import argparse
import subprocess
import os
import tempfile
import time
import logging
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed

# Importaciones del ecosistema enriquecido v1.1.0 de Avril-RAG
from distilador import destilar, validar, tiene_contenido_util, evaluar_relevancia, generar_documento_identidad
from supabase_client import insertar_idea, contar_ideas

# Configuración de logs unificada
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  
        logging.FileHandler('avril-rag.log')
    ]
)
logger = logging.getLogger(__name__)

try:
    from systemd.journal import JournalHandler  # type: ignore

    journal_handler = JournalHandler()
    journal_handler.setFormatter(logging.Formatter('%(name)s: %(message)s'))
    logger.addHandler(journal_handler)
except ImportError:
    logger.debug("systemd.journal no disponible (OK si es desarrollo local)")

# Ruta absoluta a la raíz del proyecto
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SPIDER_TIMEOUT = 120


def obtener_todos_los_spiders():
    spider_dir = os.path.join(ROOT_DIR, "rag_scraper", "rag_scraper", "spiders")
    archivos = glob.glob(os.path.join(spider_dir, "*_spider.py"))
    return [os.path.basename(f).replace("_spider.py", "") for f in archivos]


def ejecutar_spider_individual(spider: str, temp_dir: str) -> tuple[str, str, bool]:
    """
    Ejecuta un spider individual en un proceso separado.
    Retorna una tupla (spider_name, ruta_salida, exito).
    """
    spider_dir = os.path.join(ROOT_DIR, "rag_scraper")
    salida = os.path.join(temp_dir, f"{spider}.json")
    comando = ["scrapy", "crawl", spider, "-o", salida, "--logfile", "../scrapy.log"]
    timeout_segundos = GENERIC_SPIDER_TIMEOUT if spider == "generic" else DEFAULT_SPIDER_TIMEOUT
    
    if spider == "generic":
        comando.extend(["-a", f"urls_file={os.path.join(ROOT_DIR, 'urls_fuentes.json')}"])
    
    try:
        resultado = subprocess.run(
            comando, 
            cwd=spider_dir, 
            capture_output=True,
            timeout=timeout_segundos
        )
        exito = resultado.returncode == 0 and os.path.exists(salida)
        return (spider, salida, exito)
    except subprocess.TimeoutExpired:
        logger.error(f"  [TIMEOUT] Spider '{spider}' excedió {timeout_segundos} segundos")
        return (spider, salida, False)
    except Exception as e:
        logger.error(f"  [ERROR] Spider '{spider}' falló: {e}")
        return (spider, salida, False)


def ejecutar_spider_generic_secuencial(temp_dir: str) -> tuple[str, str, bool]:
    """
    Ejecuta el spider generic de forma secuencial y sin timeout.
    Se usa fuera del pool paralelo porque es el spider más pesado del pipeline.
    """
    spider = "generic"
    spider_dir = os.path.join(ROOT_DIR, "rag_scraper")
    salida = os.path.join(temp_dir, f"{spider}.json")
    comando = [
        "scrapy",
        "crawl",
        spider,
        "-o",
        salida,
        "--logfile",
        "../scrapy.log",
        "-a",
        f"urls_file={os.path.join(ROOT_DIR, 'urls_fuentes.json')}",
    ]

    try:
        resultado = subprocess.run(
            comando,
            cwd=spider_dir,
            capture_output=True,
        )
        exito = resultado.returncode == 0 and os.path.exists(salida)
        return (spider, salida, exito)
    except Exception as e:
        logger.error(f"  [ERROR] Spider '{spider}' falló: {e}")
        return (spider, salida, False)


def ejecutar_pipeline_completo(limite_noticias):
    spiders = obtener_todos_los_spiders()
    logger.info(f"Detectados {len(spiders)} spiders: {', '.join(spiders)}")
    
    # ─── FASE 1: Scraping en PARALELO ────────────────────────────────────────
    logger.info("[FASE 1] Ejecutando scrapers en PARALELO (excepto generic)...")
    spider_dir = os.path.join(ROOT_DIR, "rag_scraper")
    noticias_totales = []
    
    tiempo_inicio = time.time()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        spiders_paralelos = [spider for spider in spiders if spider != "generic"]
        spider_generic_presente = "generic" in spiders

        # Ejecutar los spiders rápidos en paralelo
        with ThreadPoolExecutor(max_workers=max(1, len(spiders_paralelos))) as executor:
            futures = {
                executor.submit(ejecutar_spider_individual, spider, temp_dir): spider
                for spider in spiders_paralelos
            }
            
            # Procesar resultados conforme se completen
            completados = 0
            for future in as_completed(futures):
                spider_name, salida, exito = future.result()
                
                if exito:
                    try:
                        with open(salida, encoding="utf-8") as f:
                            datos = json.load(f)
                            noticias_totales.extend(datos)
                            logger.info(
                                f"  [✓] Spider '{spider_name}' completado "
                                f"({len(datos)} artículos)"
                            )
                    except (json.JSONDecodeError, IOError) as e:
                        logger.warning(
                            f"  [✗] No se pudo leer resultado de '{spider_name}': {e}"
                        )
                else:
                    logger.warning(f"  [✗] Spider '{spider_name}' falló")
                
                completados += 1

        # Ejecutar generic en secuencia y sin timeout
        if spider_generic_presente:
            logger.info("[FASE 1] Ejecutando spider 'generic' en secuencia y sin timeout...")
            spider_name, salida, exito = ejecutar_spider_generic_secuencial(temp_dir)
            completados += 1

            if exito:
                try:
                    with open(salida, encoding="utf-8") as f:
                        datos = json.load(f)
                        noticias_totales.extend(datos)
                        logger.info(
                            f"  [✓] Spider '{spider_name}' completado "
                            f"({len(datos)} artículos)"
                        )
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(
                        f"  [✗] No se pudo leer resultado de '{spider_name}': {e}"
                    )
            else:
                logger.warning(f"  [✗] Spider '{spider_name}' falló")
        
        tiempo_paralelo = time.time() - tiempo_inicio
        logger.info(
            f"[FASE 1 COMPLETADA] {completados}/{len(spiders)} spiders "
            f"ejecutados en {tiempo_paralelo:.1f}s (paralelo + generic secuencial)"
        )

        # Guardar noticias.json histórico/local
        ruta_noticias = os.path.join(ROOT_DIR, "noticias.json")
        with open(ruta_noticias, "w", encoding="utf-8") as f:
            json.dump(noticias_totales, f, ensure_ascii=False, indent=2)
        logger.info(f"  Noticias totales guardadas: {len(noticias_totales)}")

    # ─── FASE 2 y 3: Evaluación y Destilación ───────────────────────────────
    logger.info(f"[FASE 2/3] Evaluando y Destilando noticias útiles...")
    noticias_utiles = [n for n in noticias_totales if tiene_contenido_util(n)]
    if limite_noticias:
        noticias_utiles = noticias_utiles[:limite_noticias]
        
    ideas_validas = []
    
    for noticia in noticias_utiles:
        logger.info(f"Procesando noticia: '{noticia['titulo'][:50]}...'")
        
        # Filtro de relevancia inicial (Paso 1 del Destilador)
        evaluacion = evaluar_relevancia(noticia)
        if not evaluacion["es_negocio_viable"]:
            logger.info(f"    [DESCARTADA] {evaluacion['razon']}")
            continue
            
        # Destilación rica mediante LLM (Paso 2 del Destilador)
        data = destilar(noticia)
        if data is None:
            # NUEVO: Logging de error si falla la destilación
            logger.error(f"    [DESTILACION FALLIDA] '{noticia['titulo'][:40]}...' - Revisar logs de API")
            continue
            
        # Validación estricta del contrato contra Pydantic
        contrato = validar(data)
        if not contrato:
            # NUEVO: Logging de error de schema Pydantic
            logger.error(f"    [VALIDACION FALLIDA] Pydantic rechazó el JSON de: '{noticia['titulo'][:40]}...'")
            logger.debug(f"    Datos rechazados: {json.dumps(data, indent=2)[:200]}...")
            continue
            
        # Generación de la Identidad Operativa en Markdown para el Frontend
        documento_identidad = generar_documento_identidad(contrato)
        
        # Volcado a diccionario y preparación de metadatos de control del pipeline
        idea = contrato.model_dump(mode="json", exclude_none=True)
        idea["_pipeline"] = {
            "status": "borrador",
            "hash_origen": noticia["hash_url"],
            "procesado_en": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "evaluacion_confianza": evaluacion["confianza"],
            "documento_identidad": documento_identidad
        }
        ideas_validas.append(idea)
        logger.info(f"    [CONTRATO OK] → {contrato.metadata.nombre} validado.")
        
        # Exportar archivo Markdown físico complementario de respaldo
        if documento_identidad:
            os.makedirs("documentos_identidad", exist_ok=True)
            nombre_archivo = contrato.metadata.nombre.replace(" ", "_").replace("/", "-")
            ruta_md = f"documentos_identidad/{nombre_archivo}_{noticia['hash_url'][:8]}.md"
            with open(ruta_md, "w", encoding="utf-8") as f:
                f.write(documento_identidad)
        
        time.sleep(1.5)

    # ─── FASE 4: Persistencia e Inserción Directa ───────────────────────────
    logger.info("[FASE 4] Insertando registros válidos en Supabase...")
    for idea in ideas_validas:
        res = insertar_idea(idea)
        if res.get("ok"):
            status = "INSERT" if res.get("accion") == "insertada" else "DEDUP"
            logger.info(f"    [{status}] {idea['metadata']['nombre']} (ID: {res.get('id')})")
        else:
            logger.error(f"    [ERROR DB] Falló inserción de {idea['metadata']['nombre']}: {res.get('error')}")

    # Guardar borrador local histórico
    ruta_borrador = os.path.join(ROOT_DIR, "ideas_borrador.json")
    with open(ruta_borrador, "w", encoding="utf-8") as f:
        json.dump(ideas_validas, f, ensure_ascii=False, indent=2)
    logger.info(f"[ARCHIVO COPIA] Respaldo borrador guardado en: {ruta_borrador}")
    
    logger.info("Pipeline completado exitosamente.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limite", type=int, default=10, help="Max noticias a procesar")
    args = parser.parse_args()
    
    ejecutar_pipeline_completo(args.limite)