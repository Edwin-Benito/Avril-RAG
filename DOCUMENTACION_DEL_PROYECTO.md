# MANUAL DE ARQUITECTURA E INGENIERÍA DE SOFTWARE — AVRIL RAG PIPELINE
**Versión del Documento:** 1.1.0  
**Fecha de Publicación:** Lunes 6 de Julio de 2026  
**Autor:** VIERNES (Asistente de Inteligencia Artificial Avanzada)  
**Proyecto:** Avril RAG — Automated News Pipeline for Agentic Business Ideas  
**Universidad Politécnica de Pachuca — TIID (Estadio Profesional)**

---

## ÍNDICE DE CONTENIDOS
1.  **VISIÓN GENERAL Y DECLARACIÓN DE PROPÓSITOS**
    *   1.1. Introducción al Proyecto
    *   1.2. El Paradigma de las "Empresas Agénticas"
    *   1.3. Problema y Solución
2.  **ARQUITECTURA DETALLADA DEL SISTEMA**
    *   2.1. Arquitectura de Cuatro Fases
    *   2.2. Diagramas de Flujo y Control de Datos
    *   2.3. Topología de Red y Comunicaciones
3.  **EL CONTRATO DE DATOS INF-RAG-000 V1.1.0**
    *   3.1. Filosofía del Contrato Único de Verdad
    *   3.2. Desglose Detallado de Campos y Tipos de Datos (Pydantic)
    *   3.3. Nuevos Bloques de Contexto y Scores de Viabilidad
    *   3.4. Reglas Críticas de Validación Semántica
4.  **MÓDULO DE INGESTA Y RASTREO (RAG_SCRAPER)**
    *   4.1. Filosofía de Ingesta Híbrida
    *   4.2. Spider 1: HackerNewsSpider (Algolia Query)
    *   4.3. Spider 2: TechCrunchSpider (RSS Feed Parsing)
    *   4.4. Spider 3: ProductHuntSpider (GraphQL API Integration)
    *   4.5. Spider 4: GenericSpider (Link Discovery y Filtro por Keywords)
5.  **MÓDULO DE DESTILACIÓN SEMÁNTICA (DISTILADOR.PY)**
    *   5.1. Fase de Evaluación de Viabilidad (Paso 1)
    *   5.2. Fase de Destilación de Ideas (Paso 2)
    *   5.3. Fase de Validación Estricta (Paso 3)
    *   5.4. Normalización de Datos y Fechas
    *   5.5. Generación de Documentos de Identidad Operativa (Paso 4)
6.  **CAPA DE PERSISTENCIA Y EMBEDDINGS VECTORIALES**
    *   6.1. Integración con Supabase y pgvector
    *   6.2. Decisión del Modelo de Embeddings: `nvidia/nv-embedqa-e5-v5`
    *   6.3. Generación de Vectores e Inserción Directa
    *   6.4. Estrategia de Deduplicación y Búsqueda Semántica
7.  **ORQUESTACIÓN DE PIPELINE (MAIN.PY)**
    *   7.1. Ciclo de Vida del Pipeline
    *   7.2. Manejo de Almacenamiento Temporal
    *   7.3. Registro y Logging Unificado (systemd-journald)
8.  **GUÍA DE DESPLIEGUE EN PRODUCCIÓN (VPS)**
    *   8.1. Requisitos de Infraestructura
    *   8.2. Variables de Entorno Seguras (.env)
    *   8.3. Configuración de Systemd Service y Timer
    *   8.4. Comandos de Administración de Systemd
9.  **PROTOCOLO DE ONBOARDING PARA DESARROLLADORES**
    *   9.1. Configuración de Entorno Local
    *   9.2. Flujo para Crear y Agregar un Nuevo Spider
    *   9.3. Ciclo de Modificación y Despliegue de Cambios
10. **GUÍA DE SOLUCIÓN DE PROBLEMAS (TROUBLESHOOTING)**
    *   10.1. Errores de API de NVIDIA y Quotas
    *   10.2. Problemas con pgvector y Cambio de Dimensiones
    *   10.3. Errores de Conexión de Supabase
    *   10.4. Diagnóstico de Fails en Systemd
11. **GLOSARIO DE TÉRMINOS Y ANEXOS**

---

## 1. VISIÓN GENERAL Y DECLARACIÓN DE PROPÓSITOS

### 1.1. Introducción al Proyecto
**Avril RAG** es una plataforma de software de nivel industrial diseñada para resolver el problema de la identificación automática de señales de mercado sobre empresas agénticas. El pipeline se encarga de monitorear la web global de startups, recopilar menciones de nuevos proyectos y destilarlos mediante modelos de lenguaje avanzados en "Planos de Negocios Agénticos" listos para ser desplegados.

### 1.2. El Paradigma de las "Empresas Agénticas"
Una **Empresa Agéntica** (Agentic Business) es aquella cuya operación principal y flujos de valor se realizan a través de agentes de inteligencia artificial coordinados de forma autónoma. No son simples wrappers o aplicaciones que consumen LLMs, sino estructuras de negocio complejas donde los roles tradicionales (ventas, atención al cliente, operaciones, análisis técnico) se delegan a subagentes de IA especializados.

### 1.3. Problema y Solución
-   **El Problema:** La velocidad del desarrollo de la IA agéntica es tan alta que para los investigadores de mercado y desarrolladores es imposible analizar manualmente cientos de lanzamientos diarios en Hacker News, Product Hunt, blogs de VC y portales de noticias. La gran mayoría de las noticias son "ruido" (anuncios de modelos masivos, mejoras marginales de empresas gigantes, papers académicos abstractos).
-   **La Solución:** **Avril RAG** ofrece un sistema de filtrado automatizado por IA en 4 capas. El sistema no solo recolecta noticias, sino que actúa como un analista de venture capital evaluando la viabilidad operativa y la autenticidad agéntica de cada proyecto, traduciéndolo a un contrato de datos Pydantic unificado de nivel empresarial y persistiendo el conocimiento semántico en Supabase para búsquedas vectoriales avanzadas.

---

## 2. ARQUITECTURA DETALLADA DEL SISTEMA

### 2.1. Arquitectura de Cuatro Fases
El sistema está construido siguiendo un patrón de tubería de datos desacoplada en cuatro fases distintas:

```
[ INGESTA (Scrapy) ] ──> [ EVALUACIÓN / FILTRADO ] ──> [ DESTILACIÓN / VALIDACIÓN ] ──> [ PERSISTENCIA (Supabase) ]
```

1.  **Fase de Ingesta:** Scrapy ejecuta rastreadores web especializados y consultas a APIs estructuradas. Se minimiza el uso de peticiones pesadas y renderizado de JavaScript utilizando endpoints oficiales y feeds RSS para mayor eficiencia y estabilidad.
2.  **Fase de Evaluación:** Un modelo de lenguaje clasifica preliminarmente si la noticia representa una empresa real que puede autosustentarse. De ser rechazada, el pipeline termina ahí, ahorrando tokens de inferencia costosos de la siguiente fase.
3.  **Fase de Destilación:** La noticia seleccionada es estructurada como un contrato técnico estricto, modelando sus procesos internos, sus subagentes requeridos, sus límites de costos y su flujo operativo en formato JSON.
4.  **Fase de Persistencia:** Se calcula el vector semántico (embedding) del plano de negocio y se realiza la transacción en la base de datos Supabase, garantizando que no se repitan ideas duplicadas mediante hashing criptográfico.

### 2.2. Diagramas de Flujo y Control de Datos
A continuación, se detalla el flujo de datos que sigue una sola noticia en el sistema desde su descubrimiento hasta su indexación semántica:

```
+--------------------------------------------------------+
|                   Inicio del Timer                     |
+--------------------------------------------------------+
                           |
                           v
+--------------------------------------------------------+
| FASE 1: Scrapy Spiders                                 |
| - hnews, techcrunch, phunt, generic                    |
+--------------------------------------------------------+
                           |
                           v
+--------------------------------------------------------+
| noticias.json (Arreglo de noticias crudas)             |
+--------------------------------------------------------+
                           |
                           | Para cada noticia...
                           v
+--------------------------------------------------------+
| tiene_contenido_util()                                 |
| (Filtro por longitud e identidad del texto)            |
+--------------------------------------------------------+
        |                               |
        | No                            | Sí
        v                               v
+-------------------+      +-----------------------------+
|    Descartada     |      | evaluar_relevancia() (Paso 1|
+-------------------+      | LLM decide viabilidad)      |
                           +-----------------------------+
                                   |             |
                       es_negocio  |             | No viable
                       viable = No |             v
                                   |     +---------------+
                                   |     |  Descartada   |
                                   |     +---------------+
                                   | Sí
                                   v
                           +-----------------------------+
                           | destilar() (Paso 2: LLM     |
                           | genera JSON contrato v1.1.0)|
                           +-----------------------------+
                                   |
                                   v
                           +-----------------------------+
                           | validar() (Paso 3: Pydantic |
                           | parsea ContratoEmpresaAgent)|
                           +-----------------------------+
                                   |             |
                                   | OK          | Error Schema
                                   v             v
+---------------------------------------+   +------------+
| generar_documento_identidad() (Paso 4)|   | Descarta / |
| (Markdown Report para Frontend)       |   | Log Error  |
+---------------------------------------+   +------------+
                           |
                           v
+--------------------------------------------------------+
| generar_embedding() (NVIDIA nv-embedqa-e5-v5 1024-dims) |
+--------------------------------------------------------+
                           |
                           v
+--------------------------------------------------------+
| insertar_idea() (PostgreSQL Transaction en Supabase)   |
| - ON CONFLICT (hash_origen) DO NOTHING (Deduplicación) |
+--------------------------------------------------------+
                           |
                           v
+--------------------------------------------------------+
|                   Fin del Proceso                      |
+--------------------------------------------------------+
```

### 2.3. Topología de Red y Comunicaciones
El sistema reside en un servidor Linux (VPS). El pipeline no mantiene puertos abiertos al exterior más que para el flujo de salida hacia las APIs de servicios externos:
-   **NVIDIA API Gateway (Puerto 443, HTTPS):** Tránsito de tokens cifrados para inferencias de destilación y cálculo de embeddings.
-   **Supabase PostgreSQL Pooler (Puerto 5432, TCP Directo):** Conexión segura usando SSL/TLS de psycopg2 hacia la nube de Supabase.
-   **Product Hunt API (Puerto 443, HTTPS):** Acceso a la API GraphQL.
-   **Hacker News Algolia Gateway (Puerto 443, HTTPS):** Consumo de REST API.

---

## 3. EL CONTRATO DE DATOS INF-RAG-000 V1.1.0

### 3.1. Filosofía del Contrato Único de Verdad
En sistemas de IA multi-agente, la mayor fuente de errores radica en la ambigüedad de los datos de entrada y salida entre diferentes agentes y sistemas externos. El contrato de datos `contrato_models.py` (especificación **INF-RAG-000 v1.1.0**) actúa como el esquema único y obligatorio que garantiza que cualquier idea de negocio descubierta en la web tenga una estructura idéntica y libre de errores antes de ser almacenada.

### 3.2. Desglose Detallado de Campos y Tipos de Datos (Pydantic)
El archivo `contrato_models.py` utiliza Pydantic v2 para garantizar tipos de datos estrictos y validaciones en tiempo de ejecución. A continuación, se detalla el esquema lógico y su equivalencia en JSON Schema:

1.  **`Skill`**:
    -   `nombre` (`str`): Identificador único del skill.
    -   `descripcion` (`str`, opcional): Detalle del propósito del skill.
    -   `parametros` (`dict`, opcional): Parámetros de inicialización requeridos.
    -   *Configuración:* `extra="forbid"` (no se permiten propiedades adicionales).

2.  **`Subagente`**:
    -   `id` (`str`): Identificador único en formato `snake_case`.
    -   `nombre` (`str`): Nombre de visualización del subagente.
    -   `rol` (`str`): Descripción corta del rol (ej. "Analista de Mercado").
    -   `modelo_llm` (`str`, default="auto"): El modelo LLM preferido para este agente.
    -   `prompt_sistema` (`str`, opcional): Directriz operativa fundamental.
    -   `objetivo` (`str`, opcional): Meta específica del subagente.
    -   `kpi_principal` (`str`, opcional): Métrica de rendimiento clave.
    -   `herramientas` (`list[str]`, opcional): Lista de herramientas/skills permitidas.
    -   `agentes_colaboradores` (`list[str]`, opcional): Identificadores de otros subagentes con los que se comunica.
    -   `skills` (`list[Skill]`): Mínimo 1 skill requerido para dar soporte operativo.

3.  **`Metadata`**:
    -   `nombre` (`str`, 2-100 caracteres): Nombre comercial o técnico de la startup o idea.
    -   `descripcion` (`str`, 10-500 caracteres): Pitch de negocio de la empresa.
    -   `origen` (`str`): URL de la noticia original.
    -   `modelo_negocio` (`str`, opcional): Modelo de monetización (SaaS, Freemium, Open-Core).
    -   `industria` (`str`, opcional): Sector comercial (ej. "Legaltech", "Fintech").
    -   `fecha_creacion` (`datetime`, opcional): Reconstruido y validado como timestamp ISO 8601.
    -   `tags` (`list[str]`, opcional): Etiquetas de búsqueda.
    -   `problema` (`str`, opcional): El pain-point del cliente que la empresa intenta solucionar.
    -   `solucion` (`str`, opcional): La solución agéntica construida.
    -   `idea_negocio` (`str`, opcional): Descripción ampliada de la idea.
    -   `cliente_objetivo` (`list[str]`, opcional): Perfiles de usuario target.
    -   `propuesta_valor` (`str`, opcional): Declaración clave de valor añadido.
    -   `ventaja_competitiva` (`str`, opcional): Por qué esta empresa destaca del resto.
    -   `competidores` (`list[str]`, opcional): Rivales de mercado conocidos.
    -   **Scores de Evaluación (0.0 - 100.0)**:
        *   `score_empresa_agentica` (`float`): Grado de dependencia de IA agéntica.
        *   `score_viabilidad` (`float`): Viabilidad técnica y comercial en el mercado.
        *   `score_automatizacion` (`float`): Porcentaje del flujo de trabajo desatendido.

4.  **`ContextoEmpresa`**:
    -   `dominio` (`str`, opcional): Sitio web oficial del proyecto.
    -   `modelo_operacion` (`str`, opcional): Debe ser "Fully Agentic", "Human-in-the-Loop" o "Semi-Autonomous".
    -   `conceptos_clave` (`list[str]`, opcional): Terminología de negocio central.
    -   `procesos_negocio` (`list[str]`, opcional): Lista de procesos que automatiza.
    -   `integraciones` (`list[str]`, opcional): Conexiones con plataformas externas (ej. "Slack", "HubSpot").
    -   `herramientas_openclaw` (`list[str]`, opcional): Herramientas recomendadas del ecosistema OpenClaw.
    -   `memoria_requerida` (`str`, opcional): Descripción de la memoria persistente de largo plazo necesaria.

5.  **`Orquestador`**:
    -   `tipo_flujo` (`str`): Debe ser "secuencial", "paralelo", "condicional" o "mixto".
    -   `agente_entrada` (`str`, opcional): El ID del subagente que inicia los flujos.
    -   `agente_salida` (`str`, opcional): El ID del subagente que entrega los resultados finales.
    -   `flujo_pasos` (`list[str]`, opcional): Secuencia de pasos lógicos del pipeline.
    -   `prompt_orquestador` (`str`, opcional): Instrucciones complejas para el ruteo de información.

6.  **`Limites`**:
    -   `tope_tokens_total` (`int`): Límite total de tokens por corrida completa (mínimo 1000).
    -   `tope_tokens_por_agente` (`int`): Límite de tokens asignado a cada subagente (mínimo 500).
    -   `timeout_segundos` (`int`): Tiempo máximo de ejecución del flujo de agentes (mínimo 10).
    -   `max_iteraciones` (`int`): Cantidad de ciclos permitidos antes de finalizar (mínimo 1).
    -   `tope_gasto_usd` (`float`): Gasto máximo presupuestado por ejecución (mínimo 0.0).

### 3.3. Nuevos Bloques de Contexto y Scores de Viabilidad
La versión v1.1.0 introduce la clase `ContextoEmpresa` y los campos de `Metadata` mejorados con scores numéricos para dar a los desarrolladores y sistemas automatizados una visión mucho más precisa de la viabilidad de la startup. Estos datos permiten ordenar, priorizar e indexar las ideas en el panel del frontend según el porcentaje de autonomía (`score_automatizacion`) o viabilidad comercial (`score_viabilidad`).

### 3.4. Reglas Críticas de Validación Semántica
-   **Validación de Versión:** El campo `version` del contrato principal debe coincidir estrictamente con el patrón regex `^\d+\.\d+\.\d+$`. Cualquier formato alternativo (como "v1.1", "1.1") provocará un `ValidationError`.
-   **Comportamiento de `extra="forbid"`:** Ninguna clase del modelo Pydantic permite que el LLM inyecte propiedades adicionales inventadas en la inferencia. Esto blinda al sistema contra el ruido semántico ("hallucinations").

---

## 4. MÓDULO DE INGESTA Y RASTREO (RAG_SCRAPER)

### 4.1. Filosofía de Ingesta Híbrida
El rastreo web masivo suele ser inestable debido a cambios de maquetación HTML, protecciones anti-bot (Cloudflare, CAPTCHAs) y altos costes de CPU/ancho de banda. Avril RAG soluciona esto usando una arquitectura de ingesta híbrida:
-   **Consumo de APIs Públicas:** Para Hacker News.
-   **Parseo XML Estructurado:** Para TechCrunch RSS.
-   **Conexiones de API Seguras por Token:** Para Product Hunt.
-   **Rastreo Inteligente por Link Discovery:** Para sitios de terceros en general.

### 4.2. Spider 1: HackerNewsSpider (Algolia Query)
Este spider no raspa el HTML de Hacker News directamente. En su lugar, hace consultas REST HTTP a la API oficial de Algolia Search (`https://hn.algolia.com/api/v1/search`), que indexa Hacker News casi en tiempo real.
-   **Estrategia:** Consulta términos clave como "agentic AI", "AI agents startup" y "autonomous agents business".
-   **Filtros:** Descarta publicaciones que no contengan palabras clave específicas en el título (ej. "agentic", "multi-agent").
-   **Rendimiento:** Extremadamente rápido (menos de 2 segundos por consulta), inmune a bloqueos de IP y cambios de maquetación de la interfaz de Hacker News.

### 4.3. Spider 2: TechCrunchSpider (RSS Feed Parsing)
Utiliza XPath para procesar el canal de RSS oficial de TechCrunch dedicado a la Inteligencia Artificial (`https://techcrunch.com/category/artificial-intelligence/feed/`).
-   **Estrategia:** Recupera las descripciones y enlaces XML de las últimas 20 a 50 noticias de TC.
-   **Filtros:** Analiza el título y la descripción buscando keywords de IA agéntica para garantizar la relevancia antes de emitir los ítems.
-   **Rendimiento:** Consumo mínimo de ancho de banda y latencia casi nula.

### 4.4. Spider 3: ProductHuntSpider (GraphQL API Integration)
Product Hunt es una de las mayores plataformas de lanzamiento de software. Este spider consume la API v2 oficial mediante peticiones HTTP `POST` que llevan un payload GraphQL detallado.
-   **Estrategia:** Recupera los últimos 20 lanzamientos de software con sus campos de título, tagline, descripción, fecha de creación y enlace del producto.
-   **Autenticación:** Utiliza el token `PRODUCTHUNT_TOKEN` provisto en el archivo `.env`.

### 4.5. Spider 4: GenericSpider (Link Discovery y Filtro por Keywords)
Es el spider más avanzado y flexible. Está diseñado para monitorear un banco de 27 URLs de capital de riesgo (VCs), blogs de frameworks y laboratorios de investigación (como OpenAI, CrewAI o LangChain).
-   **Descubrimiento de Enlaces:** Carga las URLs semilla desde `urls_fuentes.json`. Analiza la página principal y recopila enlaces internos que sigan patrones estructurados de artículos (`/blog/`, `/news/`, `/post/`, o que contengan el año en curso).
-   **Filtro Inteligente:** Ignora enlaces irrelevantes (páginas de términos de uso, portafolios de inversión estáticos, contacto, etc.).
-   **Extracción:** Visita los artículos descubiertos, extrae el título usando selectores CSS (buscando meta tags `og:title` o etiquetas `h1`) y el cuerpo del texto para generar el resumen.

---

## 5. MÓDULO DE DESTILACIÓN SEMÁNTICA (DISTILADOR.PY)

### 5.1. Fase de Evaluación de Viabilidad (Paso 1)
Antes de procesar una noticia para construir una arquitectura de negocio detallada, se ejecuta el proceso `evaluar_relevancia()`. Esta función actúa como un primer muro de filtrado para ahorrar recursos de inferencia.
-   **Lógica de Negocio:** El prompt de sistema define de manera estricta qué es una verdadera startup agéntica independiente y qué es una mejora menor ("feature") de una corporación masiva, un paper puramente de investigación académica o un simple wrapper de LLM.
-   **Salida:** Un JSON simple con campos `es_negocio_viable` (`bool`), `confianza` (`float`) y `razon` (`str`). Si el score de confianza es menor al umbral (configurado por defecto en 0.6), la noticia es automáticamente descartada del pipeline.

### 5.2. Fase de Destilación de Ideas (Paso 2)
Una vez aceptada la relevancia de la noticia, el sistema invoca a `destilar()`.
-   **Prompt de Sistema:** Proporciona al LLM las reglas de salida obligatorias y la plantilla JSON Schema de la especificación INF-RAG-000 v1.1.0 completa.
-   **Generación Inteligente:** El LLM tiene la instrucción de inferir lógicamente, a partir de noticias cortas, los requerimientos operativos reales de la startup: qué APIs necesitaría, qué herramientas de OpenClaw aplicarían mejor, qué roles de subagentes coordinados resolverían el problema y qué límites de tokens de control de costes son adecuados.

### 5.3. Fase de Validación Estricta (Paso 3)
El resultado retornado por la API de NVIDIA se limpia de bloques de código Markdown (removiendo ```json y ``` de forma segura) y se intenta instanciar como un objeto `ContratoEmpresaAgentica` de Pydantic. Si existen errores de validación (por ejemplo, tipos incorrectos, valores faltantes obligatorios, o un formato de versión de contrato inválido), la función captura el `ValidationError`, registra detalladamente en logs los campos problemáticos y aborta el guardado para evitar corromper la persistencia de la base de datos.

### 5.4. Normalización de Datos y Fechas
Dado que los LLMs suelen fallar o variar el formato al estructurar fechas y valores numéricos, `distilador.py` implementa funciones críticas de pre-validación:
-   **`normalizar_fecha_creacion()`**: Rescata fechas ruidosas, cadenas cortas de año (ej. "2026") o formatos incompletos y los reconstruye en formato ISO 8601 estricto con offset de zona horaria (`YYYY-MM-DDTHH:MM:SSZ`). Si es imposible salvar el formato de la fecha, elimina el campo del diccionario de entrada de forma proactiva para que Pydantic use su valor por defecto y no cause un rechazo catastrófico en el pipeline.
-   **`normalizar_scores()`**: Asegura la correcta conversión de los campos de score numéricos a formato `float`.

### 5.5. Generación de Documentos de Identidad Operativa (Paso 4)
Para cada idea de negocio que aprueba las pruebas anteriores, `generar_documento_identidad()` genera un documento Markdown de nivel ejecutivo.
-   **Organización en Squads:** Agrupa los subagentes del contrato de datos en squads estructurados (máximo 3 squads, con un máximo de 3 workers por squad, limitando el total de subagentes concurrentes a 12 para mantener el orden).
-   **Salida Física:** El documento generado se almacena de forma persistente en la carpeta física `documentos_identidad/` con un nombre sanitizado basado en el título de la empresa y los primeros 8 caracteres de su hash de origen, además de inyectarse en los metadatos internos de control del pipeline para su uso en interfaces frontend.

---

## 6. CAPA DE PERSISTENCIA Y EMBEDDINGS VECTORIALES

### 6.1. Integración con Supabase y pgvector
La persistencia de Avril RAG reside en Supabase sobre una base de datos PostgreSQL enriquecida con la extensión nativa de vectores `pgvector`. Esto permite realizar análisis de similitud semántica y búsquedas multidimensionales directly en SQL, sin depender de servicios de embeddings externos pesados o bases de datos de vectores no relacionales.

### 6.2. Decisión del Modelo de Embeddings: `nvidia/nv-embedqa-e5-v5`
El embedding vectorial representa el significado conceptual de la idea de negocio en un espacio multidimensional de **1024 dimensiones**.
-   **Modelo Elegido:** `nvidia/nv-embedqa-e5-v5` (NVIDIA AI Foundation Model).
-   **Por qué se seleccionó:** Reemplaza el enfoque original de embeddings locales o servicios nativos de Supabase no accesibles por falta de credenciales de despliegue en Edge Functions. Ofrece un rendimiento de nivel comercial bajo licencia abierta y es totalmente compatible con pgvector en Supabase.
-   **Nota Crítica:** Cambiar de modelo en el futuro requiere recrear la columna vector y volver a indexar todas las filas, ya que pgvector no permite cálculos entre dimensiones vectoriales diferentes.

### 6.3. Generación de Vectores e Inserción Directa
La función `insertar_idea()` en `supabase_client.py` coordina la persistencia:
1.  **Construcción del Texto Semántico:** Se concatena el nombre de la empresa, su descripción, el problema detectado y la solución planteada en una cadena unificada de texto descriptivo.
2.  **Invocación de la API de NVIDIA:** Se genera el vector flotante de 1024 dimensiones.
3.  **Transacción de Base de Datos:** Se ejecuta un query `INSERT` que inyecta todos los campos estructurados del contrato, los scores, el documento Markdown de identidad operativa y el campo `embedding` usando el tipo nativo `vector`.
4.  **Deduplicación:** Se define `ON CONFLICT (hash_origen) DO NOTHING` para evitar que noticias duplicadas o procesadas en ejecuciones previas ensucien el catálogo.

### 6.4. Estrategia de Deduplicación y Búsqueda Semántica
La base de datos implementa dos niveles de deduplicación:
-   **Deduplicación Estricta:** Mediante el índice único de la columna `hash_origen` (generado a partir de la URL de origen de la noticia).
-   **Deduplicación Semántica (Función `buscar_ideas_similares`):** Permite calcular la distancia coseno (`1 - (embedding <=> %s::vector)`) entre una idea de entrada y las existentes en base de datos. Si una nueva idea tiene un índice de similitud coseno superior a 0.85 con una idea existente, el sistema puede alertar que se trata del mismo proyecto bajo otra URL o artículo de blog.

---

## 7. ORQUESTACIÓN DE PIPELINE (MAIN.PY)

### 7.1. Ciclo de Vida del Pipeline
El script `main.py` actúa como la orquesta principal. Al ser invocado:
1.  **Exploración:** Descubre automáticamente todos los archivos spider instalados en el directorio del proyecto para saber qué rastreos ejecutar.
2.  **Scraping Paralelo de Cortas Sesiones:** Ejecuta un proceso de Scrapy por cada spider usando un directorio temporal para cada salida JSON individual, garantizando el aislamiento de fallas de scraping.
3.  **Consolidación:** Consolida las noticias crudas en el archivo `noticias.json` del proyecto.
4.  **Tubería de Inferencia:** Para cada noticia consolidada, ejecuta secuencialmente los procesos de evaluación, destilación, validación Pydantic, generación de reportes e inserción en Supabase con los reintentos y timeouts configurados.
5.  **Copia de Seguridad:** Almacena un archivo `ideas_borrador.json` local como respaldo histórico de la última ejecución.

### 7.2. Manejo de Almacenamiento Temporal
Para evitar que el disco del VPS se llene de archivos basura o logs gigantescos de Scrapy, `main.py` implementa el módulo `tempfile` de Python.
-   **Uso:** Crea un `TemporaryDirectory` en memoria del sistema para volcar la salida individual de los scrapers y lo destruye de manera segura en el bloque `finally` de ejecución, dejando únicamente los archivos validados de salida final en el disco del proyecto.

### 7.3. Registro y Logging Unificado (systemd-journald)
El sistema redirige los logs de Python a través de tres canales paralelos:
-   **Consola de Salida (`sys.stdout`):** Para monitoreo visual directo en desarrollo.
-   **Archivo de Log Físico (`avril-rag.log`):** Para persistencia en el proyecto.
-   **Systemd Journal Handler (`JournalHandler`):** Si el script se ejecuta dentro de un entorno Linux con Systemd, el log de Python se inyecta nativamente al daemon de logs del sistema de Linux (`journald`). Esto permite consultar logs con filtros de tiempo avanzados en el VPS usando herramientas de infraestructura estándar.

---

## 8. GUÍA DE DESPLIEGUE EN PRODUCCIÓN (VPS)

### 8.1. Requisitos de Infraestructura
-   **Sistema Operativo:** Ubuntu Server 22.04 LTS o superior / Debian 12.
-   **Entorno de Ejecución:** Python 3.11+ o Python 3.12+ con entornos virtuales (`venv`).
-   **Acceso a Base de Datos:** Cadena de conexión TCP abierta a Supabase PostgreSQL.
-   **Librería Systemd para Python:** El sistema operativo del VPS debe tener instalados los headers de systemd (`libsystemd-dev` en sistemas Debian/Ubuntu) para que la dependencia de python `python-systemd` pueda compilarse e instalarse de forma nativa.

### 8.2. Variables de Entorno Seguras (.env)
En producción, el archivo `.env` debe ubicarse en la raíz del proyecto `/srv/avril/.env` (o el directorio correspondiente del proyecto) y contar con permisos restringidos de lectura (`chmod 600 .env` de modo que solo el usuario del sistema pueda leerlo).

Contenido del archivo `.env`:
```ini
SUPABASE_URL = "https://ahfpnygsufynsdnhibtb.supabase.co"
SUPABASE_KEY = "sb_pub_..."
SUPABASE_CONN = "postgresql://postgres.ahfpnygsufynsdnhibtb:PASSWORD@aws-1-us-east-1.pooler.supabase.com:5432/postgres"
NVIDIA_API_KEY = "nvapi-..."
PRODUCTHUNT_TOKEN = "..."
```

### 8.3. Configuración de Systemd Service y Timer
Para automatizar el pipeline de forma segura, se utilizan dos unidades de Systemd instaladas en el directorio del sistema `/etc/systemd/system/`.

#### Servicio: `/etc/systemd/system/avril-rag.service`
Este archivo describe la ejecución del servicio del pipeline de datos como una tarea unitaria (`oneshot`).

```ini
[Unit]
Description=Avril RAG - Automated News Pipeline for Agentic Business Ideas
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=backend
Group=backend
WorkingDirectory=/srv/avril
ExecStart=/srv/avril/.venv/bin/python3 /srv/avril/main.py

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=avril-rag
SyslogFacility=local7

# Seguridad
NoNewPrivileges=true
ProtectHome=yes
ProtectSystem=strict

# Timeouts (30 min para el pipeline)
TimeoutStartSec=30m
Restart=no

[Install]
WantedBy=multi-user.target
```

#### Programador (Timer): `/etc/systemd/system/avril-rag.timer`
Este archivo gestiona la cadencia de ejecución semanal de manera exacta.

```ini
[Unit]
Description=Timer para Ejecucion Semanal de Avril RAG

[Timer]
# Se ejecuta todos los viernes a las 11:00 AM (Hora Local)
OnCalendar=Fri *-*-* 11:00:00
# Recupera la ejecución si el servidor estuvo apagado a esa hora
Persistent=true

[Install]
WantedBy=timers.target
```

### 8.4. Comandos de Administración de Systemd
A continuación se listan los comandos operativos críticos para el mantenimiento de la automatización en el VPS:

-   **Habilitar y Activar el Timer:**
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable --now avril-rag.timer
    ```
-   **Comprobar Estado de los Timers Activos:**
    ```bash
    systemctl list-timers --all
    ```
-   **Ejecutar el Pipeline Manualmente a través de Systemd:**
    ```bash
    sudo systemctl start avril-rag.service
    ```
-   **Monitorear logs en tiempo real:**
    ```bash
    sudo journalctl -u avril-rag.service -f
    ```
-   **Verificar logs del último fallo:**
    ```bash
    sudo journalctl -u avril-rag.service -p err --since "yesterday"
    ```

---

## 9. PROTOCOLO DE ONBOARDING PARA DESARROLLADORES

### 9.1. Configuración de Entorno Local
Para comenzar a desarrollar en el proyecto Avril RAG, sigue estos pasos estructurados:
1.  Instala Python 3.12 y la herramienta de entornos virtuales:
    ```bash
    sudo apt update
    sudo apt install python3.12 python3.12-venv libsystemd-dev build-essential -y
    ```
2.  Clona el repositorio e ingresa a él:
    ```bash
    git clone <url_repo>
    cd rag_avril
    ```
3.  Crea el entorno virtual y actívalo:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```
4.  Instala las dependencias de desarrollo y producción:
    ```bash
    pip install -r requirements.txt
    ```
5.  Inicializa las tablas locales/Supabase de desarrollo:
    ```bash
    python3 setup_db.py
    ```

### 9.2. Flujo para Crear y Agregar un Nuevo Spider
Si necesitas agregar una nueva fuente de datos al pipeline, sigue el protocolo estandarizado de Scrapy:
1.  Crea un nuevo archivo de spider en `rag_scraper/rag_scraper/spiders/mi_nuevo_spider.py`.
2.  Define una clase que herede de `scrapy.Spider`:
    ```python
    import scrapy
    import hashlib
    from rag_scraper.items import NoticiaItem

    class MiNuevoSpider(scrapy.Spider):
        name = "mi_nuevo"
        start_urls = ["https://ejemplo.com/blog"]

        def parse(self, response):
            for articulo in response.css("div.post"):
                item = NoticiaItem()
                item["titulo"] = articulo.css("h2::text").get()
                item["url"] = response.urljoin(articulo.css("a::attr(href)").get())
                item["resumen"] = articulo.css("p.summary::text").get()[:1000]
                item["fuente"] = "Mi Nuevo Portal"
                item["hash_url"] = hashlib.md5(item["url"].encode()).hexdigest()
                yield item
    ```
3.  El orquestador `main.py` lo detectará y ejecutará de forma automática en el próximo ciclo gracias a la función `obtener_todos_los_spiders()`.

### 9.3. Ciclo de Modificación y Despliegue de Cambios
Cualquier cambio al esquema o contrato de datos debe ser versionado en Git y desplegado siguiendo este orden:
1.  Modificar `contrato_models.py` localmente y asegurar que la versión del contrato haya sido actualizada en su declaración de clase.
2.  Ejecutar pruebas unitarias de parseo locales sobre `ideas_borrador.json`.
3.  Si la modificación altera la base de datos (columnas añadidas, cambios de tipo o tamaño de embeddings), modifica `setup_db.py` y ejecútalo para actualizar las tablas en Supabase.
4.  Sube tus cambios a Git: `git commit -am "Update contract to v1.2.0"`
5.  En el VPS, realiza un pull de la rama estable, recarga las dependencias e inicializa si es necesario con `setup_db.py`.
6.  Ejecuta `sudo systemctl daemon-reload` para refrescar cualquier cambio en las unidades de Systemd.

---

## 10. GUÍA DE SOLUCIÓN DE PROBLEMAS (TROUBLESHOOTING)

### 10.1. Errores de API de NVIDIA y Quotas
-   **Síntoma:** Error `429 Too Many Requests` o fallas de autenticación en logs del destilador o embeddings.
-   **Causa:** Has superado la cuota de peticiones gratuitas asignadas a tu cuenta de desarrollador de NVIDIA AI Foundation, o tu API key en el archivo `.env` ha expirado.
-   **Solución:**
    1.  Verifica tu cuota de tokens ingresando al panel de NVIDIA Build.
    2.  Si la clave es incorrecta o expiró, actualiza el valor de `NVIDIA_API_KEY` en tu `.env`.
    3.  Asegúrate de que no estás ejecutando el pipeline completo repetidamente en lapsos de tiempo cortos; para desarrollo, utiliza siempre el parámetro `--limite 2` para minimizar el gasto.

### 10.2. Problemas con pgvector y Cambio de Dimensiones
-   **Síntoma:** Error `psycopg2.errors.InvalidParameterValue: vector dimensions do not match`.
-   **Causa:** Se cambió el modelo de embeddings en `supabase_client.py` (por ejemplo, de un modelo de 1024 dimensiones como `nvidia/nv-embedqa-e5-v5` a uno de 1536 dimensiones de OpenAI), pero la columna `embedding` en la base de datos aún espera un vector del tamaño antiguo.
-   **Solución:**
    1.  Modifica el parámetro `EMBED_DIMENSIONES` en `setup_db.py` para que coincida con el nuevo modelo.
    2.  Ejecuta `python3 setup_db.py` para forzar el borrado y la recreación de la columna vector en la tabla `ideas_negocio`. *Nota: Esto eliminará los vectores previamente calculados, por lo que requerirás hacer un backfill manual para recalcular los embeddings de las filas existentes.*

### 10.3. Errores de Conexión de Supabase
-   **Síntoma:** Error `psycopg2.OperationalError: connection to server at ... failed: Connection timed out`.
-   **Causa:** Supabase pausa los proyectos gratuitos que no registran actividad por más de una semana. También puede deberse a un cambio de dirección IP de los pools de Supabase o contraseñas incorrectas en `SUPABASE_CONN`.
-   **Solución:**
    1.  Ingresa al dashboard de tu proyecto Supabase y verifica que la base de datos esté activa ("Active" status). Si está pausada, haz clic en "Restore Project".
    2.  Verifica que tu clave o contraseña en la cadena de conexión de postgresql no contenga caracteres especiales sin escapar semánticamente dentro del `.env`.

### 10.4. Diagnóstico de Fails en Systemd
-   **Síntoma:** El comando `systemctl status avril-rag.timer` muestra `inactive` o el servicio falla al ejecutarse.
-   **Causa:** Rutas absolutas incorrectas en los campos `WorkingDirectory` o `ExecStart` del archivo del servicio, o falta de permisos del usuario asignado en el VPS.
-   **Solución:**
    1.  Asegúrate de que la ruta al entorno virtual `/srv/avril/.venv/bin/python3` es correcta y tiene permisos de ejecución por el usuario `backend`.
    2.  Verifica la sintaxis del archivo de Systemd con `systemd-analyze verify /etc/systemd/system/avril-rag.service`.
    3.  Consulta los logs completos con `sudo journalctl -xe -u avril-rag.service`.

---

## 11. GLOSARIO DE TÉRMINOS Y ANEXOS

-   **RAG (Retrieval-Augmented Generation):** Técnica de arquitectura que combina la recuperación de datos e información externa indexada con las habilidades de inferencia lógica de los LLMs para producir respuestas y análisis extremadamente precisos y libres de alucinaciones.
-   **pgvector:** Extensión de base de datos relacional para PostgreSQL que permite almacenar, indexar y consultar vectores de alta dimensionalidad (como embeddings) usando lógica nativa SQL.
-   **HNSW (Hierarchical Navigable Small World):** Un algoritmo matemático de indexación espacial y búsquedas aproximadas de vecinos cercanos (ANN) de altísima eficiencia para colecciones vectoriales de pgvector.
-   **Embedding:** Representación numérica y matemática de un texto o concepto dentro de un mapa espacial de significado semántico, útil para calcular similitudes de conceptos más allá del uso de palabras clave idénticas.
-   **Contrato de Datos:** Esquema técnico y estructural estricto que rige las interfaces de comunicación entre APIs, bases de datos o sistemas de agentes para evitar discrepancias de información.
