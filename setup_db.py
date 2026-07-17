import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

CONNECTION_STRING = os.getenv("SUPABASE_CONN")

EMBED_DIMENSIONES = 1024  # nvidia/nv-embedqa-e5-v5

SQL_LIMPIAR_Y_CREAR = f"""
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
    embedding     vector({EMBED_DIMENSIONES}),
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Eliminar el índice semántico ANTES de tocar la columna de la que
--    depende (si no, Postgres rechaza el DROP COLUMN por dependencia).
DROP INDEX IF EXISTS idx_ideas_embedding_hnsw;

-- 4. Recrear la columna embedding con la dimensión correcta. Los valores
--    existentes (si los hay) vienen del vector "simulado" (hash SHA-256)
--    de un intento anterior — no son embeddings semánticos reales, así
--    que no hay pérdida de información válida al recrearla desde cero.
ALTER TABLE ideas_negocio DROP COLUMN IF EXISTS embedding;
ALTER TABLE ideas_negocio ADD COLUMN embedding vector({EMBED_DIMENSIONES});

-- 5. Eliminar triggers viejos de intentos anteriores (enfoque de Trigger +
--    Vault que se descartó por complejidad — el embedding ahora se genera
--    en Python antes del insert, ver supabase_client.py)
DROP TRIGGER IF EXISTS trg_calcular_embedding_nativo ON ideas_negocio;
DROP TRIGGER IF EXISTS trg_generar_embedding ON ideas_negocio;
DROP TRIGGER IF EXISTS trg_calcular_embedding ON ideas_negocio;

-- 6. Índices tradicionales y semántico HNSW
CREATE UNIQUE INDEX IF NOT EXISTS idx_ideas_hash ON ideas_negocio (hash_origen);
CREATE INDEX IF NOT EXISTS idx_ideas_status ON ideas_negocio (status);
CREATE INDEX IF NOT EXISTS idx_ideas_embedding_hnsw
    ON ideas_negocio USING hnsw (embedding vector_cosine_ops);
"""

def main():
    if not CONNECTION_STRING:
        print("[ERROR] Falta SUPABASE_CONN en el .env")
        return

    print("Conectando a Supabase para preparar la tabla...")
    try:
        conn = psycopg2.connect(CONNECTION_STRING)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(SQL_LIMPIAR_Y_CREAR)
        print(f"[OK] Estructura lista con embedding vector({EMBED_DIMENSIONES}) — nv-embedqa-e5-v5.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[ERROR] No se pudo configurar: {e}")

if __name__ == "__main__":
    main()