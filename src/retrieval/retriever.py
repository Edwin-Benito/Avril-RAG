import logging
from src.embeddings.nvidia_embedder import embeddings_config
from src.vectordb.client import obtener_conexion

logger = logging.getLogger(__name__)

def buscar_ideas_similares(texto_busqueda: str, limite: int = 5) -> list[dict]:
    vector_busqueda = embeddings_config.generar_embedding(texto_busqueda)
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