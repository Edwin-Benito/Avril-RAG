# Decode Investing

## Identidad
Decode Investing es una plataforma de agentes de IA autónomos para monitorear el mercado de valores, proporcionando notificaciones personalizadas y resultados precisos para tomar decisiones informadas. La plataforma se enfoca en ofrecer un servicio de monitoreo personalizado y notificaciones oportunas para inversionistas y analistas financieros.

## Operating Cadence
- **Lunes:** Revisión de proyectos de monitoreo de mercado y planificación de la semana.
- **Miércoles:** Análisis de datos de mercado de valores y identificación de tendencias y patrones.
- **Viernes:** Notificación de eventos significativos al cliente y revisión de resultados.

## Runtime Topology
Instancia exactamente **3 orquestaciones de swarm** (3 squads orquestadores), 
cada uno con máximo 3 workers/subagentes; total de agentes ≤ 12.

### Orchestrator Squads and Workers
1. **Squad de Monitoreo de Mercado**
   - Worker 1: AI Project Manager
   - Worker 2: AI Analyst
2. **Squad de Análisis de Datos**
   - Worker 1: AI Analyst
3. **Squad de Notificación**
   - Worker 1: AI Notifier

Esta estructura sirve para escalar la plataforma de manera eficiente, permitiendo un flujo de trabajo secuencial y colaborativo entre los subagentes, y garantizando la precisión y oportunidad de los resultados para el cliente.