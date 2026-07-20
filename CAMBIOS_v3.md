# Documentación de Cambios Avril-RAG v2.3

Este documento consolida todas las mejoras implementadas en el proyecto, basándose en la versión 2.2 y añadiendo las actualizaciones más recientes.

---

## 1. ✨ Scraping Paralelo y Optimizado (`main.py`)

### Arquitectura de Ejecución

Se ha implementado un sistema híbrido de ejecución para maximizar la velocidad sin comprometer la estabilidad:

- **Ejecución en Paralelo**: Los spiders rápidos (ej. `hackernews`, `producthunt`, `techcrunch`) se ejecutan simultáneamente utilizando `ThreadPoolExecutor`. El tiempo total de esta fase es el del spider más lento.
- **Ejecución Secuencial**: El spider `generic` se ejecuta fuera del pool paralelo y **sin timeout**, ya que es el proceso más pesado y requiere recorrer múltiples fuentes y enlaces internos.

### Beneficios

- **Reducción de tiempo**: Hasta 3-4x más rápido en la fase de recolección.
- **Estabilidad**: El spider genérico ya no falla por timeout, permitiendo una ingesta completa de fuentes HTML de alta señal.
- **Logging**: Trazabilidad completa del tiempo de ejecución y cantidad de artículos recolectados por cada spider.

---

## 2. 🔐 LLM Modular y Multi-Proveedor (`src/llm/nvidia_client.py`)

Se ha eliminado la configuración hardcodeada en favor de una clase `LLMConfig` que centraliza la gestión del modelo.

### Proveedores Soportados

El sistema ahora es compatible con cualquier API compatible con OpenAI:

- **NVIDIA** (Default)
- **OpenAI**
- **Gemini** (vía OpenAI compatible endpoint)
- **Groq**
- **Custom** (Local, Ollama, etc.)

### Configuración vía `.env`

```bash
LLM_PROVIDER=nvidia | openai | gemini | groq | custom
LLM_MODEL=meta/llama-3.1-70b-instruct
NVIDIA_API_KEY=tu_clave_nvidia
OPENAI_API_KEY=tu_clave_openai
GOOGLE_API_KEY=tu_clave_gemini
GROQ_API_KEY=tu_clave_groq
LLM_BASE_URL=http://localhost:8000/v1 # Solo para custom
```

### Capacidades Dinámicas

Es posible cambiar el proveedor o el modelo en tiempo de ejecución mediante los métodos `cambiar_provider()` y `cambiar_modelo()`.

---

## 3. 🧠 Embeddings Modular y Vectorización (`src/embeddings/nvidia_embedder.py`)

Se ha implementado `EmbeddingsConfig` para desacoplar la generación de vectores de la lógica de base de datos.

### Proveedores y Modelos

- **NVIDIA**: `nvidia/nv-embedqa-e5-v5` (1024 dims) - Optimizado para QA.
- **OpenAI**: `text-embedding-3-small` (1536 dims) o `text-embedding-3-large` (3072 dims).

### Integración con Supabase (`src/vectordb/client.py`)

- **Soporte de Fallback**: Si la generación de un embedding falla, el sistema inserta la idea con el campo `embedding` como `NULL`, evitando que el pipeline se detenga.
- **Validación de Dimensiones**: El sistema verifica que el vector retornado coincida con las dimensiones configuradas antes de insertarlo.

---

## 4. 🏗️ Pipeline de Ingesta RAG Avanzado

Se ha integrado un flujo automático desde la inserción de la idea hasta la vectorización de su identidad:

1. **Inserción de Idea**: Se guarda la idea de negocio en `ideas_negocio`.
2. **Procesamiento de Identidad**: Si la idea posee un `documento_identidad` (Markdown), se dispara el pipeline RAG.
3. **Registro de Documento**: Se crea una entrada en la tabla `public.documents`.
4. **Chunking Semántico**: El documento se divide en fragmentos (chunks) de ~1000 caracteres con solapamiento.
5. **Vectorización de Chunks**: Cada fragmento se convierte en un vector y se almacena en la base de datos, permitiendo búsquedas semánticas precisas sobre la identidad de la empresa.

---

## 5. 🛠️ Resumen Técnico de Archivos

| Archivo                             | Función Principal        | Cambio Clave                                                                                                  |
| :---------------------------------- | :----------------------- | :------------------------------------------------------------------------------------------------------------ |
| `main.py`                           | Orquestador del pipeline | Implementación de `ThreadPoolExecutor` y flujo secuencial para `generic`.                                     |
| `src/llm/nvidia_client.py`          | Configuración LLM        | Clase `LLMConfig` con soporte multi-proveedor (NVIDIA, OpenAI, Gemini, Groq).                                 |
| `src/embeddings/nvidia_embedder.py` | Configuración Embeddings | Clase `EmbeddingsConfig` con validación de dimensiones y soporte multi-proveedor.                             |
| `src/vectordb/client.py`            | Interfaz Supabase        | Implementación de pipeline RAG: `insertar_documento` $\rightarrow$ `chunking` $\rightarrow$ `insertar_chunk`. |
| `src/llm/distilador.py`             | Lógica de filtrado       | Uso de `llm_config` global y prompts externalizados.                                                          |

---

## 🚀 Guía de Configuración Rápida (`.env`)

```bash
# --- LLM ---
LLM_PROVIDER=nvidia
LLM_MODEL=meta/llama-3.1-70b-instruct
NVIDIA_API_KEY=sk-nvidia-...

# --- EMBEDDINGS ---
EMBEDDINGS_PROVIDER=nvidia
EMBEDDINGS_MODEL=nvidia/nv-embedqa-e5-v5
EMBEDDINGS_DIMENSIONS=1024

# --- DATABASE ---
SUPABASE_CONN=postgresql://postgres:password@db.supabase.co:5432/postgres
```

**Fecha de actualización:** 2026-07-19
**Versión:** 2.3
