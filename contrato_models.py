
from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class Skill(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str
    descripcion: Optional[str] = None
    parametros: Optional[dict] = None


class Subagente(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    nombre: str
    rol: str
    modelo_llm: Optional[str] = Field(default="auto", description="Usa 'auto' para que el sistema elija el modelo más conveniente.")
    prompt_sistema: Optional[str] = None
    skills: list[Skill] = Field(min_length=1)


class Metadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str = Field(min_length=2, max_length=100)
    descripcion: str = Field(min_length=10, max_length=500)
    origen: str
    modelo_negocio: Optional[str] = None
    industria: Optional[str] = None
    fecha_creacion: Optional[datetime] = None
    tags: Optional[list[str]] = None


class Orquestador(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tipo_flujo: Literal["secuencial", "paralelo", "condicional", "mixto"]
    agente_entrada: Optional[str] = None
    agente_salida: Optional[str] = None
    flujo_pasos: Optional[list[str]] = None
    prompt_orquestador: Optional[str] = None


class Limites(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tope_tokens_total: Optional[int] = Field(default=None, ge=1000)
    tope_tokens_por_agente: Optional[int] = Field(default=None, ge=500)
    timeout_segundos: Optional[int] = Field(default=None, ge=10)
    max_iteraciones: Optional[int] = Field(default=None, ge=1)
    tope_gasto_usd: Optional[float] = Field(default=None, ge=0)


class ContratoEmpresaAgentica(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    metadata: Metadata
    subagentes: list[Subagente] = Field(min_length=1)
    orquestador: Orquestador
    limites: Limites
