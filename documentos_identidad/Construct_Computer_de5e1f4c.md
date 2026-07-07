# Construct Computer

## Identidad
Construct Computer es un sistema operativo en la nube con agentes autónomos de IA para realizar tareas diarias, enfocado en automatizar tareas diarias y reducir la intervención humana.

## Operating Cadence
- **Lunes:** Inicio de la automatización de tareas diarias
- **Miércoles:** Integración con herramientas de negocio
- **Viernes:** Revisión y ajuste de la automatización y la integración

## Runtime Topology
Instancia exactamente **2 orquestaciones de swarm** (2 squads orquestadores), 
cada uno con máximo 3 workers/subagentes; total de agentes ≤ 4.

### Orchestrator Squads and Workers
1. **Squad de Automatización**
   - Worker 1: Agente Autónomo
2. **Squad de Integración**
   - Worker 1: Agente de Integración

Esta estructura sirve para escalar la automatización y la integración de tareas diarias de manera efectiva, permitiendo a Construct Computer ofrecer un sistema operativo en la nube con agentes autónomos de IA que pueden realizar tareas diarias y reducir la intervención humana.