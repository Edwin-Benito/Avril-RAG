"""
test_carga_final.py — Validación Final de Pipeline RAG
Carga ideas de ideas_borrador.json e inserta en Supabase disparando el RAG.
"""

import json
import logging
from supabase_client import insertar_idea

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def main():
    try:
        # 1. Cargar el archivo de ideas borrador
        with open("ideas_borrador.json", "r", encoding="utf-8") as f:
            ideas = json.load(f)
        
        logger.info(f"🚀 Iniciando carga de {len(ideas)} ideas en Supabase...")

        exitos = 0
        fallos = 0

        for i, idea in enumerate(ideas, 1):
            nombre = idea.get("metadata", {}).get("nombre", "Desconocida")
            logger.info(f"[{i}/{len(ideas)}] Procesando: {nombre}...")
            
            resultado = insertar_idea(idea)
            
            if resultado.get("ok"):
                logger.info(f"✅ {nombre} insertada y vectorizada con éxito.")
                exitos += 1
            else:
                logger.error(f"❌ Error con {nombre}: {resultado.get('error')}")
                fallos += 1

        logger.info(f"\n{'─'*40}")
        logger.info(f"Carga finalizada: {exitos} exitosas, {fallos} fallidas.")
        logger.info(f"{'─'*40}")

    except Exception as e:
        logger.exception(f"💥 Error crítico en la carga: {e}")

if __name__ == "__main__":
    main()
