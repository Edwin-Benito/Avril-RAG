# VerifiedProxy

## Identidad
VerifiedProxy es una plataforma de verificación de identidad y autorización para agentes de IA, diseñada para reducir el riesgo de fraude y mejorar la seguridad en las transacciones realizadas por agentes de IA. Su objetivo es proporcionar una capa de verificación de identidad y autorización para agentes de IA, permitiendo a las plataformas verificar la autorización de los agentes antes de permitir acciones.

## Operating Cadence
- **Lunes:** Revisión de registros de agentes y actualización de la base de datos de identidades verificadas.
- **Miércoles:** Análisis de logs de autenticación y verificación de identidad para identificar posibles vulnerabilidades.
- **Viernes:** Revisión de los KPIs de verificación de identidad y autenticación para evaluar el desempeño del sistema.

## Runtime Topology
Instancia exactamente **2 orquestaciones de swarm** (2 squads orquestadores), cada uno con máximo 3 workers/subagentes; total de agentes ≤ 4.

### Orchestrator Squads and Workers
1. **Squad de Verificación de Identidad**
   - Worker 1: Verificador de Identidad
2. **Squad de Autenticación de Agentes**
   - Worker 1: Autenticador de Agentes

Esta estructura sirve para escalar la verificación de identidad y la autenticación de agentes de manera eficiente, permitiendo a VerifiedProxy manejar un gran número de solicitudes de verificación y autenticación de manera segura y precisa. La separación en dos squads permite una especialización clara y una gestión más efectiva de los procesos de verificación y autenticación.