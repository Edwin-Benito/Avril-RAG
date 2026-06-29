"""
supabase_client.py — INF-RAG-001
Inserta ideas validadas en Supabase.

Prioridad de conexión:
1. `SUPABASE_CONN` para PostgreSQL directo.
2. `SUPABASE_URL` + `SUPABASE_KEY` como respaldo con el SDK.
"""

import json
import os

import psycopg2
from dotenv import load_dotenv
from supabase import Client, create_client


load_dotenv()


def _get_connection_string() -> str | None:
    connection_string = os.getenv("SUPABASE_CONN")
    return connection_string.strip() if connection_string else None


def _get_sdk_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("Faltan SUPABASE_URL o SUPABASE_KEY en el .env")
    return create_client(url, key)


def insertar_idea(idea: dict) -> dict:
    """
    Inserta una idea en Supabase.
    Si ya existe el hash_origen, la ignora (dedup entre semanas).

    Retorna: {"ok": True, "accion": "insertada"|"duplicada", "id": uuid|None}
    """
    pipeline = idea.pop("_pipeline", {})

    fila = {
        "nombre": idea["metadata"]["nombre"],
        "descripcion": idea["metadata"].get("descripcion", ""),
        "origen": idea["metadata"].get("origen", ""),
        "params_json": idea,
        "hash_origen": pipeline.get("hash_origen", ""),
        "fuente": idea["metadata"].get("origen", ""),
        "status": pipeline.get("status", "borrador"),
    }

    try:
        connection_string = _get_connection_string()

        if connection_string:
            with psycopg2.connect(connection_string) as conn:
                conn.autocommit = True
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO ideas_negocio (
                            nombre, descripcion, origen, params_json,
                            hash_origen, fuente, status
                        ) VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s)
                        ON CONFLICT (hash_origen) DO NOTHING
                        RETURNING id;
                        """,
                        (
                            fila["nombre"],
                            fila["descripcion"],
                            fila["origen"],
                            json.dumps(fila["params_json"], ensure_ascii=False),
                            fila["hash_origen"],
                            fila["fuente"],
                            fila["status"],
                        ),
                    )
                    fila_insertada = cur.fetchone()

            if fila_insertada:
                return {"ok": True, "accion": "insertada", "id": fila_insertada[0]}
            return {"ok": True, "accion": "duplicada", "id": None}

        client = _get_sdk_client()
        resultado = (
            client.table("ideas_negocio")
            .upsert(fila, on_conflict="hash_origen", ignore_duplicates=True)
            .execute()
        )
        datos = resultado.data
        if datos:
            return {"ok": True, "accion": "insertada", "id": datos[0].get("id")}
        return {"ok": True, "accion": "duplicada", "id": None}

    except Exception as e:
        return {"ok": False, "accion": "error", "error": str(e)}


def contar_ideas(status: str = None) -> int:
    """Retorna el total de ideas en Supabase, opcionalmente filtradas por status."""
    try:
        connection_string = _get_connection_string()

        if connection_string:
            with psycopg2.connect(connection_string) as conn:
                with conn.cursor() as cur:
                    if status:
                        cur.execute(
                            "SELECT COUNT(*) FROM ideas_negocio WHERE status = %s;",
                            (status,),
                        )
                    else:
                        cur.execute("SELECT COUNT(*) FROM ideas_negocio;")
                    return int(cur.fetchone()[0])

        client = _get_sdk_client()
        query = client.table("ideas_negocio").select("id", count="exact")
        if status:
            query = query.eq("status", status)
        resultado = query.execute()
        return resultado.count or 0

    except Exception:
        return 0