import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

CONNECTION_STRING = os.getenv("SUPABASE_CONN")
# Asegúrate de tener esta variable en tu .env o cámbiala por la variable de tu clave correspondiente
API_KEY_VALOR = os.getenv("NVIDIA_API_KEY") 

SQL_INSERTAR_SECRETO = """
-- Insertar la llave en la bóveda de seguridad de Supabase de forma encriptada
INSERT INTO vault.secrets (name, secret, description)
VALUES (
    'OPENAI_API_KEY', 
    %s, 
    'Clave de acceso para el Trigger automático de embeddings de Avril-RAG'
)
ON CONFLICT (name) 
DO UPDATE SET secret = EXCLUDED.secret;
"""

def main():
    if not CONNECTION_STRING or not API_KEY_VALOR:
        print("[ERROR] Falta SUPABASE_CONN o OPENAI_API_KEY en tu archivo .env")
        return

    print("Conectando a la Bóveda de Seguridad de Supabase...")
    try:
        conn = psycopg2.connect(CONNECTION_STRING)
        conn.autocommit = True
        cur = conn.cursor()

        print("Guardando secreto en vault.secrets...")
        cur.execute(SQL_INSERTAR_SECRETO, (API_KEY_VALOR,))

        print("\n[✔ OK] ¡Clave autorizada y resguardada con éxito en Supabase Vault!")
        print("A partir de este momento, el Trigger ya puede generar vectores autónomos.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[ERROR] No se pudieron otorgar los permisos en la bóveda: {e}")
        print("Verifica si tu usuario de la cadena de conexión tiene permisos de Administrador (postgres).")

if __name__ == "__main__":
    main()