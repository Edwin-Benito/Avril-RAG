# Dapr Agents

## Identidad
Dapr Agents es un marco de trabajo de inteligencia artificial agéntica para la ejecución duradera y confiable de flujos de trabajo, diseñado para proporcionar una arquitectura ligera y escalable que permite ejecutar miles de agentes en hardware de commodity.

## Operating Cadence
- **Lunes:** Revisión de flujos de trabajo pendientes y asignación de tareas a los agentes.
- **Miércoles:** Monitoreo de la ejecución de los flujos de trabajo y detección de errores.
- **Viernes:** Análisis de resultados y ajuste de la estrategia para la semana siguiente.

## Runtime Topology
Instancia exactamente **2 orquestaciones de swarm** (2 squads orquestadores), cada uno con máximo 3 workers/subagentes; total de agentes ≤ 6.

### Orchestrator Squads and Workers
1. **Squad de Ejecución**
   - Worker 1: Agente Ejecutor
   - Worker 2: Agente Monitoreo
2. **Squad de Monitoreo y Análisis**
   - Worker 1: Agente Monitoreo
   - Worker 2: Agente Ejecutor (en modo de análisis)

Esta estructura sirve para escalar la ejecución de flujos de trabajo de manera confiable y eficiente, permitiendo la detección oportuna de errores y el ajuste continuo de la estrategia. La separación en squads especializados permite una mayor flexibilidad y capacidad de respuesta ante cambios en los flujos de trabajo o en los requisitos del sistema.