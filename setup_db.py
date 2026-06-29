import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()


CONNECTION_STRING = os.getenv("SUPABASE_CONN")

SQL_CREAR_TABLA = """
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
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_ideas_hash
    ON ideas_negocio (hash_origen);

CREATE INDEX IF NOT EXISTS idx_ideas_status
    ON ideas_negocio (status);
"""

def main():
    if not CONNECTION_STRING:
        print("[ERROR] Falta SUPABASE_CONN en el .env")
        print("  Formato: postgresql://user:password@host:5432/database")
        return

    print("Conectando a Supabase (PostgreSQL directo)...")
    try:
        conn = psycopg2.connect(CONNECTION_STRING)
        conn.autocommit = True
        cur = conn.cursor()

        print("Creando tabla ideas_negocio...")
        cur.execute(SQL_CREAR_TABLA)

        # Verificar que quedó creada
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'ideas_negocio'
            ORDER BY ordinal_position;
        """)
        columnas = cur.fetchall()

        print(f"\n[OK] Tabla creada con {len(columnas)} columnas:")
        for col, tipo in columnas:
            print(f"  - {col}: {tipo}")

        cur.close()
        conn.close()

    except psycopg2.OperationalError as e:
        print(f"[ERROR] No se pudo conectar: {e}")
        print("\nVerifica que SUPABASE_CONN en tu .env tenga usuario, contraseña y base de datos correctos.")


if __name__ == "__main__":
    main()