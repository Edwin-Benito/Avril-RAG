"""

Uso:
    python main.py                  # pipeline completo
    python main.py --solo-destilar  # salta el scraping, usa noticias.json existente
    python main.py --limite 5       # limita noticias a procesar
    python main.py --fuente techcrunch
    python main.py --fuente generic --urls-file urls_fuentes.json
"""

import json
import argparse
import subprocess
import os
import tempfile
import time

from distilador import destilar, validar, tiene_contenido_util
from supabase_client import insertar_idea, contar_ideas


def correr_scraper(fuentes=None, urls_file=None):
    """Ejecuta uno o varios spiders y genera noticias.json combinado."""
    print("\n[FASE 1] Scraping de fuentes...")
    spider_dir = os.path.join(os.path.dirname(__file__), "rag_scraper")
    fuentes = fuentes or ["hackernews"]
    noticias = []
    urls_file_absoluto = os.path.abspath(urls_file) if urls_file else None

    with tempfile.TemporaryDirectory() as temp_dir:
        for fuente in fuentes:
            salida_temporal = os.path.join(temp_dir, f"{fuente}.json")
            comando = ["scrapy", "crawl", fuente]

            if fuente == "generic" and urls_file_absoluto:
                comando.extend(["-a", f"urls_file={urls_file_absoluto}"])

            comando.extend([
                "-o", salida_temporal,
                "--logfile", "../scrapy.log",
            ])

            resultado = subprocess.run(
                comando,
                cwd=spider_dir,
                capture_output=True,
                text=True,
            )

            if resultado.returncode != 0:
                print(f"  [WARN] Spider '{fuente}' terminó con código {resultado.returncode}")
                print("  Revisa scrapy.log para detalles")
                continue

            with open(salida_temporal, encoding="utf-8") as f:
                noticias.extend(json.load(f))

            print(f"  [OK] Spider '{fuente}' completado")

    with open("noticias.json", "w", encoding="utf-8") as f:
        json.dump(noticias, f, ensure_ascii=False, indent=2)

    print(f"  [OK] Scraping completado: {len(noticias)} noticias combinadas")


def main():
    parser = argparse.ArgumentParser(description="Pipeline ")
    parser.add_argument("--solo-destilar", action="store_true",
                        help="Omite el scraping y usa noticias.json existente")
    parser.add_argument("--limite", type=int, default=None,
                        help="Máximo de noticias a destilar")
    parser.add_argument(
        "--fuente",
        choices=["hackernews", "techcrunch", "generic", "ambas"],
        default="hackernews",
        help="Fuente a scrapear en la fase 1",
    )
    parser.add_argument(
        "--urls-file",
        default=None,
        help="Archivo JSON o TXT con URLs para el spider genérico",
    )
    parser.add_argument("--entrada", default="noticias.json")
    args = parser.parse_args()

    print("=" * 60)
    print("  PIPELINE")
    print("=" * 60)

    # ── Fase 1: Scraping ──────────────────────────────────────────
    if not args.solo_destilar:
        if args.fuente == "ambas":
            correr_scraper(["hackernews", "techcrunch"])
        elif args.fuente == "generic":
            correr_scraper(["generic"], urls_file=args.urls_file)
        else:
            correr_scraper([args.fuente])
    else:
        print("\n[FASE 1] Omitida — usando noticias.json existente")

    # ── Fase 2: Cargar noticias ───────────────────────────────────
    print("\n[FASE 2] Cargando noticias...")
    with open(args.entrada, encoding="utf-8") as f:
        noticias = json.load(f)

    noticias_utiles = [n for n in noticias if tiene_contenido_util(n)]
    if args.limite:
        noticias_utiles = noticias_utiles[:args.limite]

    print(f"  Total noticias:     {len(noticias)}")
    print(f"  Con contenido útil: {len(noticias_utiles)}")

    # ── Fase 3: Destilación + Validación ─────────────────────────
    print(f"\n[FASE 3] Destilando con LLM y validando con Pydantic...")
    print("-" * 60)

    ideas_validas = []
    fallidas = 0

    for i, noticia in enumerate(noticias_utiles, 1):
        titulo_corto = noticia["titulo"][:52]
        print(f"  [{i}/{len(noticias_utiles)}] {titulo_corto}...")

        data = destilar(noticia)
        if data is None:
            fallidas += 1
            continue

        contrato = validar(data)
        if contrato is None:
            fallidas += 1
            continue

        idea = contrato.model_dump(mode="json", exclude_none=True)
        idea["_pipeline"] = {
            "status": "borrador",
            "hash_origen": noticia["hash_url"],
            "procesado_en": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        ideas_validas.append(idea)
        print(f"         → {contrato.metadata.nombre} | "
              f"{len(contrato.subagentes)} agentes | "
              f"{contrato.orquestador.tipo_flujo}")

        time.sleep(1.5)

    print("-" * 60)
    print(f"  Válidas: {len(ideas_validas)} | Fallidas: {fallidas}")

    # Guardar borrador local
    with open("ideas_borrador.json", "w", encoding="utf-8") as f:
        json.dump(ideas_validas, f, ensure_ascii=False, indent=2)

    # ── Fase 4: Inserción en Supabase ─────────────────────────────
    print(f"\n[FASE 4] Insertando en Supabase...")
    print("-" * 60)

    insertadas = 0
    duplicadas = 0
    errores = 0

    for idea in ideas_validas:
        nombre = idea["metadata"]["nombre"]
        res = insertar_idea(idea)
        if res["ok"] and res["accion"] == "insertada":
            insertadas += 1
            print(f"  [INSERT] {nombre}")
        elif res["ok"] and res["accion"] == "duplicada":
            duplicadas += 1
            print(f"  [DEDUP]  {nombre} — ya existe")
        else:
            errores += 1
            print(f"  [ERROR]  {nombre} — {res.get('error', '?')}")

    print("-" * 60)
    print(f"  Insertadas:  {insertadas}")
    print(f"  Duplicadas:  {duplicadas}")
    print(f"  Errores:     {errores}")

    # Totales en Supabase
    total_db = contar_ideas()
    borradores = contar_ideas("borrador")
    print(f"\n[SUPABASE] Total en banco: {total_db} ideas ({borradores} borradores)")

    print("\n" + "=" * 60)
    print("  PIPELINE COMPLETADO")
    print("=" * 60)


if __name__ == "__main__":
    main()