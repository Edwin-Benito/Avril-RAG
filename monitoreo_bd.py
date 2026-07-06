"""monitoreo_bd.py — Dashboard de salud de BD vectorial después de pipeline"""
import os
import json
from datetime import datetime
import psycopg2
from dotenv import load_dotenv

load_dotenv()
CONNECTION_STRING = os.getenv("SUPABASE_CONN")

def generar_reporte():
    """Genera reporte de estado de la BD vectorial"""
    conn = psycopg2.connect(CONNECTION_STRING)
    cur = conn.cursor()
    
    # Métricas
    cur.execute("SELECT COUNT(*) FROM ideas_negocio;")
    total = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM ideas_negocio WHERE status='borrador';")
    borradores = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM ideas_negocio WHERE status='revisada';")
    revisadas = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM ideas_negocio WHERE embedding IS NOT NULL;")
    con_embedding = cur.fetchone()[0]
    
    # Últimas ideas insertadas
    cur.execute("""
        SELECT id, nombre, created_at, status, (embedding IS NOT NULL) as tiene_embedding
        FROM ideas_negocio
        ORDER BY created_at DESC
        LIMIT 5;
    """)
    ultimas = cur.fetchall()
    
    cur.close()
    conn.close()
    
    # Generar reporte JSON
    reporte = {
        "timestamp": datetime.now().isoformat(),
        "estadisticas": {
            "total_ideas": total,
            "borradores": borradores,
            "revisadas": revisadas,
            "con_embedding": con_embedding,
            "porcentaje_embedding": f"{(con_embedding/total*100):.1f}%" if total > 0 else "0%"
        },
        "ultimas_5_ideas": [
            {
                "nombre": u[1],
                "status": u[3],
                "embedding": "✅" if u[4] else "❌",
                "creada": u[2].isoformat()
            }
            for u in ultimas
        ]
    }
    
    return reporte

if __name__ == "__main__":
    reporte = generar_reporte()
    print(json.dumps(reporte, indent=2, ensure_ascii=False))
    
    # Guardar reporte
    with open("monitoreo_bd_ultimo.json", "w") as f:
        json.dump(reporte, f, indent=2, ensure_ascii=False)