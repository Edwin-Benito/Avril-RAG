import psycopg2
import os
from dotenv import load_dotenv

# Importamos la configuración centralizada para obtener la dimensión dinámicamente
from src.embeddings.nvidia_embedder import embeddings_config

load_dotenv()

CONNECTION_STRING = os.getenv("SUPABASE_CONN")

# Tomamos la dimensión directo de la instancia
EMBED_DIMENSIONES = embeddings_config.dimensions

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

-- 3. Eliminar el índice semántico ANTES de tocar la columna
DROP INDEX IF EXISTS idx_ideas_embedding_hnsw;

-- 4. Recrear la columna embedding con la dimensión correcta.
ALTER TABLE ideas_negocio DROP COLUMN IF EXISTS embedding;
ALTER TABLE ideas_negocio ADD COLUMN embedding vector({EMBED_DIMENSIONES});

-- 5. Eliminar triggers viejos
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
        print(f"[OK] Estructura lista con embedding vector({EMBED_DIMENSIONES}) — {embeddings_config.model}.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[ERROR] No se pudo configurar: {e}")

if __name__ == "__main__":
    main()