#!/usr/bin/env python3
"""
test_config.py — Script de diagnóstico para verificar la configuración

Este script verifica que los nuevos módulos llm_config y embeddings_config
están correctamente configurados y funcionales.

Uso:
    python test_config.py          # Verificar todo
    python test_config.py --quick  # Solo verificaciones básicas
    python test_config.py --llm    # Solo LLM
    python test_config.py --embed  # Solo embeddings
"""

import sys
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# 1. Verificar LLM Config
# ─────────────────────────────────────────────────────────────────────────────

def verificar_llm_config():
    """Verifica la configuración del LLM."""
    try:
        from llm_config import llm_config
        
        logger.info("✅ Módulo llm_config importado correctamente")
        
        estado = llm_config.obtener_estado()
        print(f"\n📋 Estado del LLM:")
        for clave, valor in estado.items():
            print(f"   {clave}: {valor}")
        
        if not estado["api_key_configurada"]:
            logger.warning(
                f"⚠️  API key no configurada para provider '{estado['provider']}'\n"
                f"   Configura la variable de entorno según el proveedor"
            )
            return False
        
        return True
    
    except ImportError as e:
        logger.error(f"❌ No se pudo importar llm_config: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error en llm_config: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# 2. Verificar Embeddings Config
# ─────────────────────────────────────────────────────────────────────────────

def verificar_embeddings_config():
    """Verifica la configuración de embeddings."""
    try:
        from embeddings_config import embeddings_config
        
        logger.info("✅ Módulo embeddings_config importado correctamente")
        
        estado = embeddings_config.obtener_estado()
        print(f"\n🧠 Estado de Embeddings:")
        for clave, valor in estado.items():
            print(f"   {clave}: {valor}")
        
        if not estado["api_key_configurada"]:
            logger.warning(
                f"⚠️  API key no configurada para provider '{estado['provider']}'\n"
                f"   Configura la variable de entorno según el proveedor"
            )
            return False
        
        return True
    
    except ImportError as e:
        logger.error(f"❌ No se pudo importar embeddings_config: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error en embeddings_config: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# 3. Verificar distilador
# ─────────────────────────────────────────────────────────────────────────────

def verificar_distilador():
    """Verifica que distilador.py usa llm_config."""
    try:
        # Leer distilador.py
        ruta = Path("distilador.py")
        if not ruta.exists():
            logger.error("❌ No se encontró distilador.py")
            return False
        
        contenido = ruta.read_text()
        
        if "from llm_config import llm_config" in contenido:
            logger.info("✅ distilador.py usa llm_config correctamente")
            return True
        else:
            logger.error("❌ distilador.py no importa llm_config")
            return False
    
    except Exception as e:
        logger.error(f"❌ Error verificando distilador.py: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# 4. Verificar supabase_client
# ─────────────────────────────────────────────────────────────────────────────

def verificar_supabase_client():
    """Verifica que supabase_client.py usa embeddings_config."""
    try:
        ruta = Path("supabase_client.py")
        if not ruta.exists():
            logger.error("❌ No se encontró supabase_client.py")
            return False
        
        contenido = ruta.read_text()
        
        if "from embeddings_config import embeddings_config" in contenido:
            logger.info("✅ supabase_client.py usa embeddings_config correctamente")
            return True
        else:
            logger.error("❌ supabase_client.py no importa embeddings_config")
            return False
    
    except Exception as e:
        logger.error(f"❌ Error verificando supabase_client.py: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# 5. Verificar main.py (scraping paralelo)
# ─────────────────────────────────────────────────────────────────────────────

def verificar_main():
    """Verifica que main.py usa ThreadPoolExecutor."""
    try:
        ruta = Path("main.py")
        if not ruta.exists():
            logger.error("❌ No se encontró main.py")
            return False
        
        contenido = ruta.read_text()
        
        if "ThreadPoolExecutor" in contenido and "as_completed" in contenido:
            logger.info("✅ main.py implementa scraping paralelo")
            return True
        else:
            logger.error("❌ main.py no usa ThreadPoolExecutor")
            return False
    
    except Exception as e:
        logger.error(f"❌ Error verificando main.py: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# 6. Test de integración (opcional)
# ─────────────────────────────────────────────────────────────────────────────

def test_integracion_llm():
    """Test opcional: intenta generar una completación simple."""
    try:
        from llm_config import llm_config
        
        print("\n🧪 Test de integración LLM (timeout 10s)...")
        
        respuesta = llm_config.client.chat.completions.create(
            model=llm_config.model,
            messages=[
                {"role": "system", "content": "Eres un asistente conciso."},
                {"role": "user", "content": "Responde 'OK' en una palabra."},
            ],
            temperature=0,
            max_tokens=10,
            timeout=10,
        )

        if not respuesta.choices:
            logger.warning("⚠️  LLM respondió sin choices")
            return False

        mensaje = respuesta.choices[0].message
        contenido = getattr(mensaje, "content", None)

        if contenido is None:
            finish_reason = getattr(respuesta.choices[0], "finish_reason", "desconocido")
            logger.warning(
                "⚠️  LLM respondió sin content. "
                f"finish_reason={finish_reason}. "
                "Esto suele pasar si el modelo devolvió una salida vacía o no soportada por el endpoint."
            )
            return False

        contenido = contenido.strip()
        logger.info(f"✅ LLM responde correctamente: '{contenido}'")
        return True
    
    except Exception as e:
        logger.warning(f"⚠️  Test LLM falló (puede ser timeout o API key): {e}")
        return False


def test_integracion_embeddings():
    """Test opcional: intenta generar un embedding."""
    try:
        from embeddings_config import embeddings_config
        
        print("\n🧪 Test de integración Embeddings (timeout 10s)...")
        
        vector = embeddings_config.generar_embedding("test")
        
        if vector:
            logger.info(f"✅ Embeddings generados: {len(vector)} dimensiones")
            return True
        else:
            logger.warning("⚠️  Embeddings retornó None (posiblemente API key)")
            return False
    
    except Exception as e:
        logger.warning(f"⚠️  Test Embeddings falló: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    """Ejecuta todos los tests."""
    print("=" * 70)
    print("🔍 Avril-RAG v2.0 — Verificación de Configuración")
    print("=" * 70)
    
    modo_quick = "--quick" in sys.argv
    test_llm_only = "--llm" in sys.argv
    test_embed_only = "--embed" in sys.argv
    
    resultados = {}
    
    # Tests básicos (siempre)
    if not test_embed_only:
        resultados["LLM Config"] = verificar_llm_config()
        resultados["distilador.py"] = verificar_distilador()
    
    if not test_llm_only:
        resultados["Embeddings Config"] = verificar_embeddings_config()
        resultados["supabase_client.py"] = verificar_supabase_client()
    
    resultados["main.py (paralelo)"] = verificar_main()
    
    # Tests de integración (opcional, omitir con --quick)
    if not modo_quick and not test_embed_only:
        print()
        test_integracion_llm()
    
    if not modo_quick and not test_llm_only:
        print()
        test_integracion_embeddings()
    
    # Resumen
    print("\n" + "=" * 70)
    print("📊 Resumen:")
    print("=" * 70)
    
    total = len(resultados)
    exitosos = sum(1 for v in resultados.values() if v)
    
    for nombre, resultado in resultados.items():
        estado = "✅" if resultado else "❌"
        print(f"{estado} {nombre}")
    
    print(f"\nResultado: {exitosos}/{total} componentes OK")
    
    if exitosos == total:
        print("\n🎉 ¡Todo está configurado correctamente!")
        return 0
    else:
        print("\n⚠️  Revisa los errores anteriores")
        return 1


if __name__ == "__main__":
    sys.exit(main())
