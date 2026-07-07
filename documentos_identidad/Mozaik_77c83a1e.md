# Mozaik

## Identidad
Mozaik es una plataforma para equipos de agentes autónomos que trabajan de manera concurrente y colaborativa, proporcionando una solución para mejorar la eficiencia y productividad a través de la colaboración efectiva entre agentes.

## Operating Cadence
- **Lunes:** Revisión de objetivos y planificación de tareas para la semana
- **Miércoles:** Análisis de progreso y ajustes de estrategia
- **Viernes:** Evaluación de resultados y planificación para la siguiente semana

## Runtime Topology
Instancia exactamente **2 orquestaciones de swarm** (2 squads orquestadores), 
cada uno con máximo 3 workers/subagentes; total de agentes ≤ 12.

### Orchestrator Squads and Workers
1. **Squad de Colaboración**
   - Worker 1: Agente de Colaboración
   - Worker 2: Agente de Comunicación
2. **Squad de Soporte**
   - Worker 1: Agente de Comunicación

Esta estructura sirve para escalar la colaboración y comunicación efectiva entre agentes, permitiendo a Mozaik mejorar la eficiencia y productividad de las empresas que la utilizan. La división en squads especializados permite una mayor flexibilidad y capacidad de respuesta a las necesidades de los clientes.