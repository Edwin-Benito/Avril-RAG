# Context.dev
## Identidad
Context.dev es una API de contexto web para productos y agentes de IA que proporciona acceso a una plataforma que permite a los desarrolladores y agentes de codificación integrar la API en minutos.

## Operating Cadence
- **Lunes:** Revisión de la extracción de datos de sitios web y planificación de la semana.
- **Martes:** Ejecución del Scrape Subagente para extraer datos de sitios web.
- **Miércoles:** Ejecución del Crawl Subagente para extraer datos de sitios web.
- **Jueves:** Revisión de los resultados de la extracción de datos y ajustes necesarios.
- **Viernes:** Preparación para la semana siguiente y actualización de la documentación.

## Runtime Topology
Instancia exactamente **2 orquestaciones de swarm**, cada uno con máximo 3 workers/subagentes; total de agentes ≤ 12.

### Orchestrator Squads and Workers
1. **Squad de Extracción de Datos**
 - Worker 1: Scrape Subagente
 - Worker 2: Crawl Subagente
2. **Squad de Procesamiento de Datos**
 - Worker 1: Scrape Subagente (para procesamiento adicional)

Esta estructura sirve para escalar la extracción y procesamiento de datos de sitios web, permitiendo a Context.dev manejar grandes cantidades de datos de manera eficiente.