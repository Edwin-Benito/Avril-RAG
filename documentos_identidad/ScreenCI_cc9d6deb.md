# ScreenCI

## Identidad
ScreenCI es una herramienta para mantener videos de productos en sincronía con el producto, convirtiendo pruebas E2E en videos. Ofrece una solución para que equipos de SaaS mantengan sus videos de productos actualizados y sincronizados con el producto.

## Operating Cadence
- **Lunes:** Creación de videos a partir de pruebas E2E
- **Miércoles:** Edición y fine-tunado de videos
- **Viernes:** Publicación de videos en línea

## Runtime Topology
Instancia exactamente **2 orquestaciones de swarm** (2 squads orquestadores), 
cada uno con máximo 3 workers/subagentes; total de agentes ≤ 4.

### Orchestrator Squads and Workers
1. **Squad de Creación de Contenido**
   - Worker 1: Creador de videos
2. **Squad de Edición y Publicación**
   - Worker 1: Editor de videos

Esta estructura sirve para escalar la creación y edición de videos de manera eficiente, permitiendo a ScreenCI mantener una alta calidad en sus productos y satisfacer las necesidades de sus clientes de manera efectiva.