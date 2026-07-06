"""
supabase_client.py — INF-RAG-001
Inserta ideas validadas en Supabase con upsert por hash_origen.
Las ideas repetidas entre semanas se ignoran silenciosamente.
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


def get_client() -> Client:
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
    client = get_client()
    pipeline = idea.pop("_pipeline", {})

    fila = {
        "nombre":       idea["metadata"]["nombre"],
        "descripcion":  idea["metadata"].get("descripcion", ""),
        "origen":       idea["metadata"].get("origen", ""),
        "params_json":  idea,
        "hash_origen":  pipeline.get("hash_origen", ""),
        "fuente":       idea["metadata"].get("origen", ""),
        "status":       pipeline.get("status", "borrador"),
        "documento_identidad": pipeline.get("documento_identidad"),
        # Markdown narrativo (squads + cadencia operativa) generado sobre
        # el contrato ya validado. Vive en su propia columna porque NO es
        # parte del contrato estricto INF-RAG-000 — es un artefacto de
        # lectura humana / contexto adicional para OpenClaw al desplegar.
    }

    try:
        resultado = (
            client.table("ideas_negocio")
            .upsert(fila, on_conflict="hash_origen", ignore_duplicates=True)
            .execute()
        )
        datos = resultado.data
        if datos:
            return {"ok": True, "accion": "insertada", "id": datos[0].get("id")}
        else:
            return {"ok": True, "accion": "duplicada", "id": None}

    except Exception as e:
        return {"ok": False, "accion": "error", "error": str(e)}


def contar_ideas(status: str = None) -> int:
    """Retorna el total de ideas en Supabase, opcionalmente filtradas por status."""
    client = get_client()
    query = client.table("ideas_negocio").select("id", count="exact")
    if status:
        query = query.eq("status", status)
    resultado = query.execute()
    return resultado.count or 0