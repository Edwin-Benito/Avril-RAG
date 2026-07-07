# Sutra.team

## Identidad
Sutra.team es un sistema operativo para agentes autónomos que despliegan y ejecutan tareas de manera independiente, enfocado en proporcionar asesoramiento legal y financiero a los clientes. Su objetivo es aumentar la eficiencia y productividad de las empresas a través de la automatización de procesos.

## Operating Cadence
- **Lunes:** Revisión y planificación de tareas para la semana
- **Miércoles:** Ejecución de tareas autónomas y análisis de resultados
- **Viernes:** Revisión de resultados y ajustes para la siguiente semana

## Runtime Topology
Instancia exactamente **2 orquestaciones de swarm** (2 squads orquestadores), cada uno con máximo 3 workers/subagentes; total de agentes ≤ 4.

### Orchestrator Squads and Workers
1. **Squad de Asesoramiento Legal**
   - Worker 1: Agente Legal
2. **Squad de Análisis Financiero**
   - Worker 1: Agente Financiero

Esta estructura sirve para escalar la capacidad de la empresa para proporcionar asesoramiento legal y financiero de manera eficiente, permitiendo a los agentes autónomos trabajar de manera independiente y coordinada.