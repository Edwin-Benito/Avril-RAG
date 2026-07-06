"""
supabase_client.py — INF-RAG-001
Inserta ideas validadas en Supabase usando conexión directa PostgreSQL (psycopg2).
Genera el embedding semántico real vía NVIDIA API antes de insertar.

NOTA DE ARQUITECTURA — decisión de proveedor de embeddings:
El requisito original pedía usar el servicio de embeddings NATIVO de Supabase
(modelo gte-small corriendo en Edge Functions, sin API externa). No fue
posible implementarlo porque el acceso otorgado a este proyecto es
únicamente la cadena de conexión a Postgres (sin CLI ni dashboard de
Supabase para desplegar Edge Functions/Database Webhooks — esa capa vive
fuera de Postgres y no es accesible por SQL). Como alternativa funcional
equivalente, el embedding se genera aquí en Python usando la API de NVIDIA
— mismo proveedor que ya se usa para la destilación, sin infraestructura
adicional que desplegar.

Modelo elegido: nvidia/nv-embedqa-e5-v5
  - 1024 dimensiones
  - Licencia: NVIDIA AI Foundation Models Community License + MIT License
  - Explícitamente listado como "ready for commercial use" por NVIDIA
  - (Se descartó nv-embed-v1: aunque es más grande (4096 dims), su licencia
    es "non-commercial use only", inadecuada para un producto como Avril)

Pendiente: migrar al servicio nativo de Supabase (gte-small) si en el
futuro se obtiene acceso de despliegue a Edge Functions del proyecto.
"""

import os
import logging
import psycopg2
import requests
from psycopg2.extras import Json
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

CONNECTION_STRING = os.getenv("SUPABASE_CONN")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")

NVIDIA_EMBED_URL = "https://integrate.api.nvidia.com/v1/embeddings"
NVIDIA_EMBED_MODEL = "nvidia/nv-embedqa-e5-v5"
EMBED_DIMENSIONES = 1024
# Debe coincidir EXACTAMENTE con la columna `embedding vector(N)` en
# setup_db.py — si cambias de modelo, actualiza también esa columna.


def obtener_conexion():
    if not CONNECTION_STRING:
        raise ValueError("Falta la variable de entorno SUPABASE_CONN en el .env")
    return psycopg2.connect(CONNECTION_STRING)


def generar_embedding(texto: str) -> list[float] | None:
    """
    Genera un embedding semántico real vía la API de NVIDIA.
    Retorna None si falla (no bloquea el insert — la idea se guarda sin
    embedding y puede completarse después con un job de backfill).
    """
    if not NVIDIA_API_KEY:
        logger.warning("[EMBEDDING] Falta NVIDIA_API_KEY, se omite el embedding")
        return None

    try:
        respuesta = requests.post(
            NVIDIA_EMBED_URL,
            headers={
                "Authorization": f"Bearer {NVIDIA_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "input": [texto],
                "model": NVIDIA_EMBED_MODEL,
                "input_type": "passage",
                # "passage": estamos indexando contenido para buscarlo después,
                # no haciendo una consulta de búsqueda en este momento.
                "encoding_format": "float",
                "truncate": "END",
            },
            timeout=15,
        )
        respuesta.raise_for_status()
        data = respuesta.json()
        embedding = data["data"][0]["embedding"]

        if len(embedding) != EMBED_DIMENSIONES:
            logger.warning(
                f"[EMBEDDING] Dimensión inesperada: {len(embedding)} "
                f"(se esperaba {EMBED_DIMENSIONES}). Se omite para no romper la columna."
            )
            return None

        return embedding

    except Exception as e:
        logger.warning(f"[EMBEDDING] No se pudo generar: {e}")
        return None


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
    vector_embedding = generar_embedding(texto_semantico)

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

        if resultado:
            return {"ok": True, "accion": "insertada", "id": resultado[0]}
        else:
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
    """
    Busca las N ideas más semánticamente parecidas a un texto dado, usando
    distancia de coseno sobre la columna embedding (pgvector). Útil para
    dedup semántica: antes de insertar una idea nueva, se puede llamar esto
    para ver si ya existe algo muy similar aunque el hash de URL/contenido
    sea distinto.
    """
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