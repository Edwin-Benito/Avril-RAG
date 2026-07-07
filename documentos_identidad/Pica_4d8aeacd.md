# Pica

## Identidad
Pica es una plataforma de infraestructura de IA agéntica de código abierto basada en Rust, diseñada para proporcionar una solución robusta y escalable para la confianza y la supervisión en la autonomía de la IA. Su objetivo es empoderar a los desarrolladores con los bloques de construcción para sistemas agénticos seguros y capaces.

## Operating Cadence
- **Lunes:** Revisión de los objetivos y planes de trabajo para la semana
- **Miércoles:** Reunión de coordinación entre los agentes de desarrollo y soporte
- **Viernes:** Revisión de los progresos y planificación para la semana siguiente

## Runtime Topology
Instancia exactamente **2 orquestaciones de swarm** (2 squads orquestadores), 
cada uno con máximo 3 workers/subagentes; total de agentes ≤ 4.

### Orchestrator Squads and Workers
1. **Desarrollo y Mantenimiento**
   - Worker 1: Agente de Desarrollo
2. **Soporte Técnico**
   - Worker 1: Agente de Soporte

Esta estructura sirve para escalar de manera efectiva, ya que permite una clara división de tareas y responsabilidades entre los agentes, lo que facilita la coordinación y el trabajo en equipo. Además, la limitación en el número de agentes y workers garantiza una gestión eficiente de los recursos y una mayor calidad en la prestación de servicios.