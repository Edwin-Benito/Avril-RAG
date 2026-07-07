# CodeMote

## Identidad
CodeMote es una herramienta de control remoto para modelos de IA que permite sesiones en vivo y aprobaciones directas desde un iPhone, brindando una conexión directa y segura entre el dispositivo y la máquina o VPS. Esto permite a los desarrolladores gestionar sesiones de IA de forma eficiente y segura.

## Operating Cadence
- **Lunes:** Revisión de sesiones de IA y planificación de tareas para la semana.
- **Miércoles:** Análisis de datos y ajustes de configuración para optimizar el rendimiento de las sesiones de IA.
- **Viernes:** Revisión de progreso y planificación para la siguiente semana.

## Runtime Topology
Instancia exactamente **2 orquestaciones de swarm** (2 squads orquestadores), cada uno con máximo 3 workers/subagentes; total de agentes ≤ 12.

### Orchestrator Squads and Workers
1. **Squad de Control Remoto**
   - Worker 1: Agente de control remoto
   - Worker 2: Agente de autenticación segura
2. **Squad de Seguridad y Optimización**
   - Worker 1: Agente de autenticación segura
   - Worker 2: (No asignado, para futuras expansiones)

Esta estructura sirve para escalar la capacidad de CodeMote de manera eficiente, permitiendo una gestión segura y eficaz de las sesiones de IA, y facilita la incorporación de nuevos agentes y capacidades en el futuro.