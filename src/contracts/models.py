"""
Modelos Pydantic — Contrato de Parámetros INF-RAG-000 v1.1.0
Fuente única de verdad para validación en todo el pipeline.
Compatible con OpenClaw y extensible para empresas agénticas.
"""

from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# SKILLS
# ============================================================

class Skill(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str
    descripcion: Optional[str] = None
    parametros: Optional[dict] = None


# ============================================================
# SUBAGENTES
# ============================================================

class Subagente(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    nombre: str
    rol: str

    modelo_llm: Optional[str] = Field(
        default="auto",
        description="Usa 'auto' para que el sistema elija el modelo más conveniente."
    )

    prompt_sistema: Optional[str] = None

    # NUEVOS CAMPOS PARA EMPRESAS AGÉNTICAS
    objetivo: Optional[str] = None

    kpi_principal: Optional[str] = None

    herramientas: Optional[list[str]] = None

    agentes_colaboradores: Optional[list[str]] = None

    skills: list[Skill] = Field(min_length=1)


# ============================================================
# METADATA EMPRESARIAL
# ============================================================

class Metadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # EXISTENTES
    nombre: str = Field(
        min_length=2,
        max_length=100
    )

    descripcion: str = Field(
        min_length=10,
        max_length=500
    )

    origen: str

    modelo_negocio: Optional[str] = None

    industria: Optional[str] = None

    fecha_creacion: Optional[datetime] = None

    tags: Optional[list[str]] = None

    # NUEVOS CAMPOS DE IDENTIDAD EMPRESARIAL

    problema: Optional[str] = None

    solucion: Optional[str] = None

    idea_negocio: Optional[str] = None

    cliente_objetivo: Optional[list[str]] = None

    propuesta_valor: Optional[str] = None

    ventaja_competitiva: Optional[str] = None

    competidores: Optional[list[str]] = None

    # MÉTRICAS DE EVALUACIÓN

    score_empresa_agentica: Optional[float] = Field(
        default=None,
        ge=0,
        le=100
    )

    score_viabilidad: Optional[float] = Field(
        default=None,
        ge=0,
        le=100
    )

    score_automatizacion: Optional[float] = Field(
        default=None,
        ge=0,
        le=100
    )


# ============================================================
# CONTEXTO DE LA EMPRESA
# ============================================================

class ContextoEmpresa(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dominio: Optional[str] = None

    modelo_operacion: Optional[str] = None
    # Ejemplos:
    # "Fully Agentic"
    # "Human-in-the-Loop"
    # "Semi-Autonomous"

    conceptos_clave: Optional[list[str]] = None

    procesos_negocio: Optional[list[str]] = None

    integraciones: Optional[list[str]] = None

    herramientas_openclaw: Optional[list[str]] = None

    memoria_requerida: Optional[str] = None


# ============================================================
# ORQUESTADOR
# ============================================================

class Orquestador(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo_flujo: Literal[
        "secuencial",
        "paralelo",
        "condicional",
        "mixto"
    ]

    agente_entrada: Optional[str] = None

    agente_salida: Optional[str] = None

    flujo_pasos: Optional[list[str]] = None

    prompt_orquestador: Optional[str] = None


# ============================================================
# LIMITES
# ============================================================

class Limites(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tope_tokens_total: Optional[int] = Field(
        default=None,
        ge=1000
    )

    tope_tokens_por_agente: Optional[int] = Field(
        default=None,
        ge=500
    )

    timeout_segundos: Optional[int] = Field(
        default=None,
        ge=10
    )

    max_iteraciones: Optional[int] = Field(
        default=None,
        ge=1
    )

    tope_gasto_usd: Optional[float] = Field(
        default=None,
        ge=0
    )


# ============================================================
# CONTRATO PRINCIPAL
# ============================================================

class ContratoEmpresaAgentica(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = Field(
        pattern=r"^\d+\.\d+\.\d+$"
    )

    metadata: Metadata

    # NUEVO BLOQUE DE CONTEXTO
    contexto_empresa: Optional[ContextoEmpresa] = None

    subagentes: list[Subagente] = Field(
        min_length=1
    )

    orquestador: Orquestador

    limites: Limites

    pipeline_info: Optional[dict] = Field(default=None, alias="_pipeline")