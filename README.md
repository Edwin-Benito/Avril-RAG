# Avril RAG

Pipeline RAG para detectar noticias y señales sobre negocios agénticos, convertirlas en ideas estructuradas y guardarlas en Supabase para revisión humana.

## Qué hace

- Recolecta noticias desde fuentes externas con Scrapy.
- Normaliza cada fuente al mismo esquema de noticia.
- Destila las noticias con un LLM para producir ideas de negocio agénticas.
- Valida la salida contra un contrato Pydantic.
- Inserta las ideas en Supabase con deduplicación por URL o hash.
- Mantiene el estado de cada idea como `borrador`, `revisada` o `publicada`.

## Estructura del proyecto

- `main.py`: Orquestador del pipeline completo.
- `distilador.py`: Llamada al modelo y validación del JSON generado.
- `contrato_models.py`: Esquemas Pydantic del contrato de salida.
- `supabase_client.py`: Inserción y conteo de ideas en Supabase.
- `setup_db.py`: Creación de la tabla `ideas_negocio` en PostgreSQL/Supabase.
- `rag_scraper/`: Proyecto de Scrapy con spiders y configuración.
- `urls_fuentes.json`: Banco de URLs base para el spider genérico.

## Fuentes actuales

- Hacker News mediante Algolia Search.
- TechCrunch AI RSS.
- Spider genérico para URLs individuales o un banco JSON de URLs.

## Requisitos

- Python 3.12 o superior.
- Una cuenta de Supabase.
- Una API key para NVIDIA API.

## Instalación

1. Crear y activar el entorno virtual.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Instalar dependencias.

```bash
pip install -r requirements.txt
```

3. Crear el archivo `.env` a partir de `.env.example` y completar las credenciales.

## Variables de entorno

El proyecto usa estas variables:

- `NVIDIA_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SUPABASE_CONN`

## Preparar la base de datos

Crear la tabla en Supabase con:

```bash
python3 setup_db.py
```

## Ejecutar el pipeline

Pipeline completo con Hacker News por defecto:

```bash
python3 main.py
```

Usar TechCrunch:

```bash
python3 main.py --fuente techcrunch
```

Usar el spider genérico con el banco de URLs:

```bash
python3 main.py --fuente generic --urls-file urls_fuentes.json
```

Destilar sin volver a scrapear:

```bash
python3 main.py --solo-destilar
```

## Salidas del proceso

- `noticias.json`: salida del scraping.
- `ideas_borrador.json`: ideas validadas antes de Supabase.
- `scrapy.log`: registro del scraper.

## Notas de operación

- El proyecto ya usa Scrapy como capa de ingesta.
- El banco de ideas en Supabase guarda las ideas en estado `borrador` por defecto.
- La revisión humana puede mover una idea a `revisada` o `publicada`.
- El botón "Voy a tener suerte" debe consumir solo ideas publicadas.
