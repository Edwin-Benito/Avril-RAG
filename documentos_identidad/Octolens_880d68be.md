# Octolens

## Identidad
Octolens es una empresa agéntica que ofrece una API de monitoreo de menciones en internet para agentes de IA, proporcionando acceso a información en línea para empresas que utilizan agentes de IA. La empresa se enfoca en proporcionar una solución de monitoreo de menciones en internet para empresas de tecnología y desarrolladores de IA.

## Operating Cadence
- **Lunes:** Revisión de menciones en internet y actualización de la base de datos
- **Miércoles:** Análisis de información filtrada y generación de informes para clientes
- **Viernes:** Revisión de KPIs y ajuste de parámetros para mejorar el desempeño

## Runtime Topology
Instancia exactamente **2 orquestaciones de swarm** (2 squads orquestadores), 
cada uno con máximo 3 workers/subagentes; total de agentes ≤ 4.

### Orchestrator Squads and Workers
1. **Squad de Monitoreo**
   - Worker 1: Agente de Monitoreo
2. **Squad de Filtro**
   - Worker 1: Agente de Filtro

Esta estructura sirve para escalar la capacidad de monitoreo y filtro de información, permitiendo a Octolens proporcionar información relevante y precisa a sus clientes de manera eficiente. La separación en squads permite una mayor especialización y flexibilidad en la asignación de tareas y recursos.