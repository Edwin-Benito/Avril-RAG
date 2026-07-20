import os
import logging
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

# Import actualizado a la nueva ruta
from src.embeddings.nvidia_embedder import embeddings_config

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
    Ahora también dispara la ingesta del documento de identidad al sistema RAG.
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

    # Logging detallado del estado del embedding
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
    ON CONFLICT (hash_origen) DO UPDATE SET
        nombre = EXCLUDED.nombre,
        descripcion = EXCLUDED.descripcion,
        embedding = EXCLUDED.embedding
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
            idea_id = resultado[0]
            logger.info(f"[SUPABASE] ✅ Idea insertada con ID: {idea_id}")
            
            # --- INTEGRACIÓN RAG ---
            # Si la idea tiene un documento de identidad, lo procesamos para el RAG
            if documento_identidad and isinstance(documento_identidad, str):
                try:
                    logger.info(f"[RAG] Iniciando ingesta de documento para '{nombre}'...")
                    
                    # Limpiar la fuente para guardar ruta relativa al proyecto
                    # Si la fuente es una ruta absoluta, intentamos extraer solo la parte final
                    fuente_relativa = origen
                    if os.path.isabs(origen):
                        # Buscamos la carpeta 'documentos_identidad' para hacer la ruta relativa desde ahí
                        if "documentos_identidad" in origen:
                            fuente_relativa = "documentos_identidad/" + os.path.basename(origen)
                        else:
                            fuente_relativa = os.path.basename(origen)

                    # 1. Registrar el documento
                    doc_id = insertar_documento(
                        titulo=f"Identidad - {nombre}",
                        fuente=fuente_relativa,
                        tipo_fuente="markdown",
                        metadata={"idea_id": idea_id, "nombre": nombre}
                    )
                    
                    # 2. Chunking simple (por párrafos o longitud)
                    chunks = _dividir_texto_en_chunks(documento_identidad)
                    
                    # 3. Vectorizar e insertar cada chunk
                    for i, chunk_text in enumerate(chunks):
                        vector_chunk = embeddings_config.generar_embedding(chunk_text)
                        if vector_chunk:
                            insertar_chunk(
                                document_id=doc_id,
                                contenido=chunk_text,
                                embedding=vector_chunk,
                                chunk_index=i,
                                metadata={"chunk_index": i}
                            )
                    logger.info(f"[RAG] ✅ Documento '{nombre}' vectorizado e insertado ({len(chunks)} chunks)")
                except Exception as e:
                    logger.error(f"[RAG] ❌ Error en pipeline de ingesta para '{nombre}': {e}")
            # -----------------------

            return {"ok": True, "id": idea_id}
        return {"ok": False, "error": "No se obtuvo ID de retorno"}
    except Exception as e:
        logger.error(f"[SUPABASE] ❌ Error insertando idea: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        if conn:
            conn.close()

def _dividir_texto_en_chunks(texto: str, tamaño_chunk: int = 1000, solapamiento: int = 100) -> list[str]:
    """
    Función auxiliar para dividir el documento de identidad en fragmentos.
    """
    chunks = []
    for i in range(0, len(texto), tamaño_chunk - solapamiento):
        chunk = texto[i : i + tamaño_chunk]
        chunks.append(chunk)
    return chunks


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


def insertar_documento(titulo: str, fuente: str, tipo_fuente: str, metadata: dict) -> int:
    """
    Inserta la metadata de un documento en la tabla public.documents.
    Retorna el ID del documento creado.
    """
    query = """
    INSERT INTO public.documents (title, source, source_type, metadata)
    VALUES (%s, %s, %s, %s)
    RETURNING id;
    """
    conn = None
    try:
        conn = obtener_conexion()
        cur = conn.cursor()
        cur.execute(query, (titulo, fuente, tipo_fuente, Json(metadata)))
        doc_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return doc_id
    except Exception as e:
        logger.error(f"[SUPABASE] ❌ Error insertando documento: {e}")
        raise e
    finally:
        if conn:
            conn.close()


def insertar_chunk(document_id: int, contenido: str, embedding: list[float], chunk_index: int, metadata: dict) -> bool:
    """
    Inserta un fragmento de texto y su vector en la tabla public.document_chunks.
    """
    query = """
    INSERT INTO public.document_chunks (document_id, content, embedding, chunk_index, metadata)
    VALUES (%s, %s, %s, %s, %s);
    """
    conn = None
    try:
        conn = obtener_conexion()
        cur = conn.cursor()
        cur.execute(query, (document_id, contenido, embedding, chunk_index, Json(metadata)))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        logger.error(f"[SUPABASE] ❌ Error insertando chunk: {e}")
        return False
    finally:
        if conn:
            conn.close()