"""
supabase_client.py — INF-RAG-001
Inserta ideas validadas en Supabase usando conexión directa PostgreSQL (psycopg2).
Genera el embedding semántico real vía la API de embeddings configurada.

La configuración de embeddings (proveedor, modelo, dimensiones, etc.) se gestiona
ahora en embeddings_config.py, permitiendo cambios sin modificar este módulo.
"""

import os
import logging
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

from embeddings_config import embeddings_config

load_dotenv()

logger = logging.getLogger(__name__)

CONNECTION_STRING = os.getenv("SUPABASE_CONN")


def obtener_conexion():
    if not CONNECTION_STRING:
        raise ValueError("Falta la variable de entorno SUPABASE_CONN en el .env")
    return psycopg2.connect(CONNECTION_STRING)


def insertar_idea(idea: dict) -> dict:
    """
    Inserta una idea enriquecida v1.1.0 junto con su embedding real en Supabase.
    """
    idea_copia = idea.copy()
    pipeline = idea_copia.pop("_pipeline", {})
    metadata = idea_copia.get("metadata", {})

    hash_origen = pipeline.get("hash_origen", "")
    if not hash_origen:
        return {"ok": False, "accion": "error", "error": "Falta hash_origen"}

    nombre = metadata.get("nombre")
    descripcion = metadata.get("descripcion", "")
    origen = metadata.get("origen", "")
    fuente = metadata.get("fuente", origen)
    status = pipeline.get("status", "borrador")
    documento_identidad = pipeline.get("documento_identidad")

    score_empresa_agentica = metadata.get("score_empresa_agentica")
    score_viabilidad = metadata.get("score_viabilidad")
    score_automatizacion = metadata.get("score_automatizacion")

    problema = metadata.get("problema", "") or ""
    solucion = metadata.get("solucion", "") or ""
    texto_semantico = (
        f"Empresa: {nombre}. Descripción: {descripcion}. "
        f"Problema: {problema}. Solución: {solucion}."
    )
    
    vector_embedding = embeddings_config.generar_embedding(texto_semantico)

    # NUEVO: Logging detallado del estado del embedding
    if vector_embedding:
        dims = len(vector_embedding)
        logger.info(f"[EMBEDDING] ✅ {dims}-dims generadas para '{nombre}'")
    else:
        logger.warning(f"[EMBEDDING] ⚠️ NULL para '{nombre}' (Se insertará sin vector)")

    query = """
    INSERT INTO ideas_negocio (
        nombre, descripcion, origen, fuente, status,
        documento_identidad, score_empresa_agentica,
        score_viabilidad, score_automatizacion, embedding, params_json, hash_origen
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    ON CONFLICT (hash_origen) DO NOTHING
    RETURNING id;
    """

    conn = None
    try:
        conn = obtener_conexion()
        cur = conn.cursor()

        cur.execute(query, (
            nombre, descripcion, origen, fuente, status,
            documento_identidad, score_empresa_agentica,
            score_viabilidad, score_automatizacion,
            vector_embedding,
            Json(idea_copia), hash_origen
        ))

        resultado = cur.fetchone()
        conn.commit()
        cur.close()

        # NUEVO: Logging del resultado de Supabase
        if resultado:
            logger.info(
                f"[SUPABASE] INSERT OK - {nombre} (ID: {resultado[0]}) "
                f"| embedding={'✅' if vector_embedding else '❌'}"
            )
            return {"ok": True, "accion": "insertada", "id": resultado[0]}
        else:
            logger.info(f"[SUPABASE] DEDUP - '{nombre}' ya existe en BD")
            return {"ok": True, "accion": "duplicada", "id": None}

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"[SUPABASE DB] Error al insertar: {e}")
        return {"ok": False, "accion": "error", "error": str(e)}
    finally:
        if conn:
            conn.close()


def contar_ideas(status: str | None = None) -> int:
    """Retorna el total de ideas en Supabase, opcionalmente filtradas por status."""
    conn = None
    try:
        conn = obtener_conexion()
        cur = conn.cursor()
        if status:
            cur.execute("SELECT COUNT(*) FROM ideas_negocio WHERE status = %s", (status,))
        else:
            cur.execute("SELECT COUNT(*) FROM ideas_negocio")
        resultado = cur.fetchone()
        cur.close()
        return resultado[0] if resultado else 0
    except Exception as e:
        logger.error(f"[SUPABASE DB] Error al contar: {e}")
        return 0
    finally:
        if conn:
            conn.close()


def buscar_ideas_similares(texto_busqueda: str, limite: int = 5) -> list[dict]:

    vector_busqueda = generar_embedding(texto_busqueda)
    if vector_busqueda is None:
        logger.warning("[EMBEDDING] No se pudo generar embedding de búsqueda")
        return []

    conn = None
    try:
        conn = obtener_conexion()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, nombre, descripcion,
                   1 - (embedding <=> %s::vector) AS similitud
            FROM ideas_negocio
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (vector_busqueda, vector_busqueda, limite),
        )
        filas = cur.fetchall()
        cur.close()
        return [
            {"id": f[0], "nombre": f[1], "descripcion": f[2], "similitud": float(f[3])}
            for f in filas
        ]
    except Exception as e:
        logger.error(f"[SUPABASE DB] Error en búsqueda semántica: {e}")
        return []
    finally:
        if conn:
            conn.close()