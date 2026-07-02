# Avril RAG

Pipeline RAG para detectar noticias y señales sobre negocios agénticos, convertirlas en ideas estructuradas y guardarlas en Supabase para revisión humana.

Documentación técnica completa: [DOCUMENTACION_DEL_PROYECTO.md](DOCUMENTACION_DEL_PROYECTO.md)

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

### Spiders especializados (3):

1. **Hacker News** - API Algolia Search, filtrado por keywords (agentic, ai agent, autonomous agent, etc.)
2. **TechCrunch AI** - RSS feed oficial de TechCrunch categoria AI
3. **Product Hunt** - API GraphQL oficial, lanzamientos recientes

### Spider genérico con link discovery (24 URLs):

4. **Blogs de VCs y empresas:**
   - a16z Blog, Sequoia Capital, Bessemer Venture Partners, NFX, Conviction, Lightspeed Venture Partners
   - OpenAI Blog, Anthropic News, Google AI Blog, Google Research

5. **Blogs de frameworks AI:**
   - CrewAI Blog, LangChain Blog, LlamaIndex Blog, AutoGen

6. **Plataformas de desarrollo:**
   - GitHub Trending, Y Combinator Companies, Hugging Face (Spaces + Models)
   - Replit Blog, Cursor Blog, Devin/OpenHands, Cognition AI

El spider genérico descubre automáticamente artículos dentro de cada sitio:

- Busca enlaces a artículos (/blog/, /news/, /post/, 202x)
- Filtra basura (terms, privacy, team, portfolio)
- Extrae solo links internos del dominio
- Valida que el contenido tenga keywords (ai, agent, llm, autonomous, startup)

**Total:** 27 URLs configuradas en `urls_fuentes.json`, 4 spiders independientes

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

## Ejecución automática (systemd)

En producción, el pipeline se ejecuta automáticamente:

**Timing:** Cada viernes a las 12:00 PM (UTC)  
**Mecanismo:** systemd timer + service  
**Recuperación:** Si el servidor estaba apagado a esa hora, se ejecuta después de reiniciar (Persistent=true)  
**Logs:** `sudo journalctl -u avril-rag.service -f`

### Instalación en VPS

Copiar archivos:

```bash
sudo cp avril-rag.service avril-rag.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable avril-rag.timer
sudo systemctl start avril-rag.timer
```

Verificar:

```bash
sudo systemctl list-timers avril-rag.timer
sudo journalctl -u avril-rag.service -n 50
```

### Ejecutar manualmente (desarrollo)

```bash
# Pipeline completa
python3 main.py

# Con límite de noticias (testing)
python3 main.py --limite 5

# Solo Hacker News
scrapy crawl hackernews

# Solo TechCrunch
scrapy crawl techcrunch

# Solo Product Hunt
scrapy crawl producthunt

# Generic spider con todas las 27 URLs
scrapy crawl generic -a urls_file=urls_fuentes.json
```
