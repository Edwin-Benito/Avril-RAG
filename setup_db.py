"""
setup_db.py — INF-RAG-001
Prepara la tabla ideas_negocio con soporte para pgvector de forma limpia,
eliminando los triggers HTTP para delegar el control al servicio cliente de Supabase.
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

CONNECTION_STRING = os.getenv("SUPABASE_CONN")

SQL_LIMPIAR_Y_CREAR = """
-- 1. Asegurar la extensión de vectores nativa de Supabase
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Asegurar la estructura relacional v1.1.0
CREATE TABLE IF NOT EXISTS ideas_negocio (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre        TEXT NOT NULL,
    descripcion   TEXT,
    origen        TEXT,
    params_json   JSONB NOT NULL,
    hash_origen   TEXT UNIQUE NOT NULL,
    fuente        TEXT,
    status        TEXT NOT NULL DEFAULT 'borrador'
                  CHECK (status IN ('borrador', 'revisada', 'publicada')),
    quality_score FLOAT,
    documento_identidad TEXT,
    score_empresa_agentica FLOAT,
    score_viabilidad       FLOAT,
    score_automatizacion   FLOAT,
    embedding     vector(1536), -- Gestionado de forma nativa por el cliente Supabase
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Eliminar triggers viejos para evitar conflictos de llaves API
DROP TRIGGER IF EXISTS trg_calcular_embedding_nativo ON ideas_negocio;
DROP TRIGGER IF EXISTS trg_generar_embedding ON ideas_negocio;
DROP TRIGGER IF EXISTS trg_calcular_embedding ON ideas_negocio;

-- 4. Asegurar índices tradicionales y semánticos HNSW
CREATE UNIQUE INDEX IF NOT EXISTS idx_ideas_hash ON ideas_negocio (hash_origen);
CREATE INDEX IF NOT EXISTS idx_ideas_status ON ideas_negocio (status);
CREATE INDEX IF NOT EXISTS idx_ideas_embedding_hnsw 
    ON ideas_negocio USING hnsw (embedding vector_cosine_ops);
"""

def main():
    if not CONNECTION_STRING:
        print("[ERROR] Falta SUPABASE_CONN en el .env")
        return

    print("Conectando a Supabase para limpiar topología...")
    try:
        conn = psycopg2.connect(CONNECTION_STRING)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(SQL_LIMPIAR_Y_CREAR)
        print("[✔ OK] Estructura de pgvector lista y limpia en Supabase.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[ERROR] No se pudo configurar: {e}")

if __name__ == "__main__":
    main()