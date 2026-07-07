# AnySearch

## Identidad
AnySearch es una herramienta de búsqueda para agentes de IA que proporciona información filtrada, desduplicada y estructurada de fuentes confiables. Su objetivo es mejorar la precisión y confiabilidad de los resultados de los agentes de IA. AnySearch opera en el dominio de la Inteligencia Artificial y utiliza un modelo de operación Fully Agentic.

## Operating Cadence
- **Lunes:** Revisión de los procesos de búsqueda y filtrado de información.
- **Miércoles:** Análisis de la calidad de la información proporcionada y ajustes en los algoritmos de filtrado.
- **Viernes:** Evaluación del desempeño de los agentes y planificación de mejoras para la semana siguiente.

## Runtime Topology
Instancia exactamente **2 orquestaciones de swarm** (2 squads orquestadores), cada uno con máximo 3 workers/subagentes; total de agentes ≤ 12.

### Orchestrator Squads and Workers
1. **Squad de Búsqueda**
   - Worker 1: Agente de búsqueda (search_agent)
   - Worker 2: Agente de filtrado (filter_agent)
2. **Squad de Procesamiento**
   - Worker 1: Agente de filtrado (filter_agent)
   - Worker 2: Agente de búsqueda (search_agent)

Esta estructura sirve para escalar la capacidad de procesamiento de información y mejorar la eficiencia en la búsqueda y filtrado de datos, permitiendo a AnySearch proporcionar resultados precisos y confiables a los agentes de IA. La división en squads especializados permite una mayor flexibilidad y capacidad de adaptación a las necesidades cambiantes de los clientes.