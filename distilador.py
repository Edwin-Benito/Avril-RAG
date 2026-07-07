"""
distilador.py — INF-RAG-001
Lee noticias.json, evalúa viabilidad de negocio, destila cada noticia en una
idea de negocio agéntico usando un LLM compatible con OpenAI y valida con
Pydantic (INF-RAG-000). Guarda ideas válidas en ideas_borrador.json.

Uso:
    python distilador.py                  # procesa todas las noticias
    python distilador.py --limite 5       # solo las primeras 5 (para pruebas)
"""

import json
import sys
import argparse
import time
import logging
import re
import os
from pydantic import ValidationError
from dotenv import load_dotenv

from contrato_models import ContratoEmpresaAgentica
from llm_config import llm_config

load_dotenv()

# Configuración del logger para este módulo
logger = logging.getLogger(__name__)

TIEMPO_MAX_EVALUACION = 30.0
TIEMPO_MAX_DESTILACION = 45.0
TIEMPO_MAX_IDENTIDAD = 45.0


def extraer_json_texto(texto: str) -> dict | None:
    """Extrae el primer objeto JSON válido desde texto con fences o ruido."""
    if not isinstance(texto, str):
        return None

    texto = texto.strip()

    if texto.startswith("```"):
        partes = texto.split("```", 2)
        if len(partes) >= 2:
            bloque = partes[1].strip()
            if bloque.startswith("json"):
                bloque = bloque[4:].strip()
            texto = bloque

    inicio = texto.find("{")
    if inicio == -1:
        return None

    try:
        objeto, _ = json.JSONDecoder().raw_decode(texto[inicio:])
        if isinstance(objeto, dict):
            return objeto
        return None
    except json.JSONDecodeError:
        return None

PROMPT_SISTEMA_EVALUACION = """Eres un analista de venture capital especializado en IA agéntica.
Tu único trabajo es decidir si una noticia describe una EMPRESA O PRODUCTO
agéntico real e INDEPENDIENTE que podría convertirse en un modelo de negocio.

═══════════════════════════════════════════════════════════════════════════════
DEFINICIÓN: ¿Qué ES una EMPRESA AGÉNTICA?
═══════════════════════════════════════════════════════════════════════════════

Una empresa agéntica debe cumplir TODAS estas condiciones:

1. **INDEPENDENCIA EMPRESARIAL**: 
   - Startup o producto con marca/nombre propio y modelo de negocio separado
   - NO una "feature" dentro de una empresa tech grande (Google, Microsoft, OpenAI, etc.)
   - Ejemplo : "Google lanza AI Overviews" = feature de Google
   - Ejemplo : "Perplexity lanza búsqueda con IA agéntica" = empresa independiente

2. **NATURALEZA AGÉNTICA NATIVA**:
   - El producto opera mediante **agentes autónomos** como componente central
   - Puede haber human-in-the-loop, pero la lógica principal es agéntica
   - Ejemplo : "AutoGPT proporciona orquestación de agentes" = agéntico por diseño
   - Ejemplo : "ChatGPT lanza modo lectura" = LLM sin agentes

3. **MODELO DE NEGOCIO CLARO**:
   - Usuarios/clientes podrían pagar por usarlo (SaaS, API, Marketplace, etc.)
   - Clientes: empresas, desarrolladores, profesionales (no el público masivo)
   - Ejemplo : "CrewAI ofrece orquestación de agentes para equipos"
   - Ejemplo : "Un investigador publica un paper sobre multi-agent systems"

4. **PRODUCTO REAL O ETAPA TEMPRANA VIABLE**:
   - MVP, beta, o public release (no solo anuncio teórico)
   - Tiene documentación, código, o interface público
   - Ejemplo : "AnythingLLM lanza soporte para swarms agénticos"
   - Ejemplo : "Investigadores predicen que en 2030 habrá agentes autónomos"

═══════════════════════════════════════════════════════════════════════════════
RECHAZA (es_negocio_viable = false) SI:
═══════════════════════════════════════════════════════════════════════════════

 Lanzamiento de MODELO DE IA en sí (Claude, GPT, Gemini, Llama, Grok, etc.)
 Razón: Un modelo no es una empresa — es infraestructura que otras usan
 
 Feature nueva de empresa tech GRANDE y establecida (Google, Microsoft, Meta, 
 Amazon, Apple, OpenAI, Anthropic, Nvidia, etc.)
 Razón: No es una startup; tiene recursos inigualables
 
 Feature de un producto existente (ej. "ChatGPT ahora tiene modo X", 
 "Slack agrega integración Y")
 Razón: Es mejora a un producto existente, no nuevo negocio
 
 Paper académico, investigación o publicación sin producto asociado
 Razón: Es teoría, no empresa
 
 Artículo de opinión, advertencia o crítica sobre IA agéntica
 Razón: No describe un producto/empresa específico
 
 Regulación, política pública o marco legal
 Razón: No es un modelo de negocio
 
 Incidente de seguridad o falla de un agente
 Razón: Es una noticia sobre riesgos, no sobre una empresa
 
 Análisis de mercado, predicción de Gartner, o tendencias generales
 Razón: Es meta-análisis, no empresa específica
 
 Producto que es esencialmente un wrapper o cliente de un modelo (ej. 
   "App para usar Claude mejor")
   Razón: No añade valor empresarial distintivo — es UX sobre infraestructura

═══════════════════════════════════════════════════════════════════════════════
ACEPTA (es_negocio_viable = true) SI:
═══════════════════════════════════════════════════════════════════════════════

 Startup que ofrece orquestación de agentes (ej. CrewAI, AutoGen, AnythingLLM)

 Plataforma agéntica para casos de uso específicos:
   - Legal: startup que automatiza revisión de contratos con agentes
   - Healthcare: sistema que diagnostica con agentes coordinados
   - Finanzas: trading bot que ejecuta estrategias con agentes
   
 Infraestructura para desarrolladores:
   - API o SDK para construir agentes (LangChain, LlamaIndex)
   - Orquestadores de swarms (ej. AgentPool)
   
 SaaS agéntico para operaciones internas:
   - CRM que automatiza ventas con agentes
   - HR que maneja procesos con agentes autónomos
   
 Open-source agentic con modelo de negocio viable:
   - Enterprise support, consulting, hosted version

CRITERIO CLAVE PARA DECIDIR:
"¿Podría alguien crear una startup completamente nueva basada en esta idea?"
- SÍ → Acepta
- NO (porque es feature/modelo/paper) → Rechaza

═══════════════════════════════════════════════════════════════════════════════

Responde ÚNICAMENTE con un JSON de esta forma exacta, sin texto adicional:
{
  "es_negocio_viable": true o false,
  "confianza": número entre 0.0 y 1.0,
  "razon": "explicación breve (máximo 1 oración) de por qué aceptaste o rechazaste"
}"""

PROMPT_USUARIO_EVALUACION = """Evalúa esta noticia estrictamente contra la 
definición de EMPRESA AGÉNTICA INDEPENDIENTE:

Título: {titulo}
Fuente: {fuente}
Resumen: {resumen}

RECUERDA LOS RECHAZOS AUTOMÁTICOS:
- Modelos de IA (Claude, GPT, Gemini, Llama, etc.)
- Features de empresas grandes (Google, Microsoft, OpenAI, Anthropic, etc.)
- Papers o investigación sin producto
- Wrappers o clientes de modelos
- Incidentes de seguridad
- Regulación o política

Responde SOLO con el JSON de evaluación, sin texto adicional."""


# ── Prompt de destilación (paso 2 — schema v1.1.0 enriquecido) ──────────────────
PROMPT_SISTEMA = """Eres un analista experto en modelos de negocio y arquitecturas de IA agéntica.
Tu tarea es convertir noticias sobre startups o productos de IA en planos de negocio altamente estructurados en formato JSON estricto.

REGLAS OBLIGATORIAS:
- Responde ÚNICAMENTE con un objeto JSON válido. Sin texto antes ni después.
- Sin bloques de código, sin comillas triples, sin explicaciones.
- El JSON debe cumplir exactamente con el schema INF-RAG-000 v1.1.0 provisto.

SCHEMA REQUERIDO:
{
  "version": "1.1.0",
  "metadata": {
    "nombre": "string (2-100 chars, requerido)",
    "descripcion": "string (10-500 chars, requerido)",
    "origen": "string URL (requerido)",
    "modelo_negocio": "string opcional (SaaS, Marketplace, Freemium, Open-Core, etc.)",
    "industria": "string opcional",
    "fecha_creacion": "string ISO 8601 opcional",
    "tags": ["array de strings opcional"],
    "problema": "string opcional (Problema real detectado en el mercado)",
    "solucion": "string opcional (Solución planteada)",
    "idea_negocio": "string opcional (Breve pitch del modelo operativo)",
    "cliente_objetivo": ["array de strings opcional"],
    "propuesta_valor": "string opcional",
    "ventaja_competitiva": "string opcional",
    "competidores": ["array de strings opcional"],
    "score_empresa_agentica": number entre 0 y 100 (opcional),
    "score_viabilidad": number entre 0 y 100 (opcional),
    "score_automatizacion": number entre 0 y 100 (opcional)
  },
  "contexto_empresa": {
    "dominio": "string opcional",
    "modelo_operacion": "Fully Agentic | Human-in-the-Loop | Semi-Autonomous (opcional)",
    "conceptos_clave": ["array de strings opcional"],
    "procesos_negocio": ["array de strings opcional"],
    "integraciones": ["array de strings opcional"],
    "herramientas_openclaw": ["array de strings opcional"],
    "memoria_requerida": "string opcional (Breve descripción del contexto persistente necesario)"
  },
  "subagentes": [
    {
      "id": "string snake_case requerido",
      "nombre": "string requerido",
      "rol": "string requerido",
      "modelo_llm": "string opcional. Usa 'auto' si no tienes una preferencia clara.",
      "prompt_sistema": "string opcional (Directriz base para el comportamiento de este subagente)",
      "objetivo": "string opcional (Qué debe lograr en la organización)",
      "kpi_principal": "string opcional (Métrica de éxito para el agente)",
      "herramientas": ["array de strings opcional"],
      "agentes_colaboradores": ["array de strings opcional (IDs de otros subagentes con los que interactúa)"],
      "skills": [
        {
          "nombre": "string requerido",
          "descripcion": "string opcional",
          "parametros": "object/dict opcional"
        }
      ]
    }
  ],
  "orquestador": {
    "tipo_flujo": "secuencial | paralelo | condicional | mixto (requerido)",
    "agente_entrada": "string opcional (ID del agente que recibe el trigger inicial)",
    "agente_salida": "string opcional (ID del agente que finaliza o entrega el resultado)",
    "flujo_pasos": ["array de strings opcional (Descripción secuencial del pipeline)"],
    "prompt_orquestador": "string opcional (Instrucciones de ruteo y coordinación general)"
  },
  "limites": {
    "tope_tokens_total": integer >= 1000 (opcional),
    "tope_tokens_por_agente": integer >= 500 (opcional),
    "timeout_segundos": integer >= 10 (opcional),
    "max_iteraciones": integer >= 1 (opcional),
    "tope_gasto_usd": number >= 0 (opcional)
  }
}

CRITERIOS DE SCORES (0-100):
- score_empresa_agentica: Mide si depende nativamente de flujos autónomos agénticos o si solo es software tradicional.
- score_viabilidad: Grado de madurez del mercado y factibilidad técnica de desarrollo.
- score_automatizacion: Qué porcentaje de la operación puede correr desatendido.

IMPORTANTE sobre fecha_creacion: si la incluyes, DEBE tener el formato ISO
8601 completo con fecha y hora, ejemplo exacto: "2026-01-15T00:00:00Z".
NUNCA escribas solo el año ("2026") o solo la fecha sin hora."""

PROMPT_USUARIO = """Convierte esta noticia en una idea de negocio agéntico estructurada bajo el contrato v1.1.0.
Diseña una arquitectura operativa profesional. Infiere de forma inteligente la identidad de negocio, el contexto ideal para OpenClaw, un ecosistema de subagentes interactivos (mínimo 2) y sus métricas de evaluación.

NOTICIA:
Título: {titulo}
Fuente: {fuente}
URL: {url}
Resumen: {resumen}

Responde SOLO con el JSON, sin ningún texto adicional."""


def tiene_contenido_util(noticia: dict) -> bool:
    """Filtra noticias cuyo resumen es idéntico al título (sin contexto real)."""
    titulo = noticia.get("titulo", "").strip()
    resumen = noticia.get("resumen", "").strip()
    return resumen != titulo and len(resumen) > len(titulo) + 20


def evaluar_relevancia(noticia: dict, umbral_confianza: float = 0.6) -> dict:
    """PASO 1 del pipeline de destilación."""
    prompt = PROMPT_USUARIO_EVALUACION.format(
        titulo=noticia["titulo"],
        fuente=noticia["fuente"],
        resumen=noticia["resumen"][:600],
    )

    try:
        respuesta = llm_config.client.chat.completions.create(
            model=llm_config.model,
            messages=[
                {"role": "system", "content": PROMPT_SISTEMA_EVALUACION},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=200,
            timeout=TIEMPO_MAX_EVALUACION,
        )
        contenido = respuesta.choices[0].message.content
        resultado = extraer_json_texto(contenido)
        if resultado is None:
            raise json.JSONDecodeError("Respuesta no parseable", contenido or "", 0)

        es_viable = bool(resultado.get("es_negocio_viable", False))
        confianza = float(resultado.get("confianza", 0.0))
        razon = str(resultado.get("razon", ""))

        if es_viable and confianza < umbral_confianza:
            es_viable = False
            razon = f"[confianza baja: {confianza}] {razon}"

        return {"es_negocio_viable": es_viable, "confianza": confianza, "razon": razon}

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning(f"[EVAL] Respuesta no parseable: {e}")
        return {"es_negocio_viable": False, "confianza": 0.0,
                "razon": f"error_evaluacion: respuesta no parseable ({e})"}
    except Exception as e:
        logger.error(f"[EVAL] Error de API: {e}")
        return {"es_negocio_viable": False, "confianza": 0.0,
                "razon": f"error_evaluacion: {e}"}


def normalizar_fecha_creacion(data: dict) -> dict:
    """
    Extrae y normaliza la parte de fecha reconstruyendo un ISO 8601 completo.
    Si el formato es inválido, demasiado corto o corrupto, elimina el campo 
    para evitar fallos estrictos en Pydantic.
    """
    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        return data

    fecha = metadata.get("fecha_creacion")
    if not fecha or not isinstance(fecha, str):
        return data

    fecha = fecha.strip()

    # Si es muy corto (ej: "2026" o texto ruidoso) y no tiene un patrón claro,
    # intentamos rescatar el año si son 4 dígitos exactos, si no, se borra.
    if len(fecha) < 8:
        m = re.match(r"^\b(19|20)\d{2}\b$", fecha)
        if m:
            metadata["fecha_creacion"] = f"{m.group(0)}-01-01T00:00:00Z"
            return data
        else:
            logger.warning(f"[FECHA] Input demasiado corto o inválido '{fecha}', se remueve.")
            del metadata["fecha_creacion"]
            return data

    # Ya viene completa y bien formada — asegurar sufijo Z si falta hora offset
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?", fecha):
        if not re.search(r"(Z|[+-]\d{2}:\d{2})$", fecha):
            fecha = fecha + "Z"
        metadata["fecha_creacion"] = fecha
        return data

    # Buscar patrón YYYY-MM-DD
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", fecha)
    if m:
        metadata["fecha_creacion"] = f"{m.group(0)}T00:00:00Z"
        return data

    # Buscar patrón YYYY-MM
    m = re.search(r"(\d{4})-(\d{2})(?!\d)", fecha)
    if m:
        metadata["fecha_creacion"] = f"{m.group(0)}-01T00:00:00Z"
        return data

    # Buscar solo un año de 4 dígitos
    m = re.search(r"\b(19|20)\d{2}\b", fecha)
    if m:
        metadata["fecha_creacion"] = f"{m.group(0)}-01-01T00:00:00Z"
        return data

    # Si no cayó en ninguna regla, limpiar para salvar el pipeline
    logger.warning(f"[FECHA] Formato irreconocible '{fecha}', se omite el campo.")
    del metadata["fecha_creacion"]
    return data


def normalizar_scores(data: dict) -> dict:
    """
    Asegura que los nuevos scores numéricos de evaluación tengan el formato 
    float correcto o se remuevan si vienen corruptos para evitar fallos en Pydantic.
    """
    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        return data

    campos_score = ["score_empresa_agentica", "score_viabilidad", "score_automatizacion"]
    for campo in campos_score:
        if campo in metadata:
            valor = metadata[campo]
            if valor is None:
                continue
            try:
                metadata[campo] = float(valor)
            except (ValueError, TypeError):
                logger.warning(f"[SCORES] Valor inválido para {campo}: {valor}. Removiendo campo.")
                del metadata[campo]
    return data


def destilar(noticia: dict, max_reintentos: int = 3) -> dict | None:
    """Llama al LLM y retorna el JSON parseado, o None si falla. Incluye reintentos automáticos."""
    prompt = PROMPT_USUARIO.format(
        titulo=noticia["titulo"],
        fuente=noticia["fuente"],
        url=noticia["url"],
        resumen=noticia["resumen"][:800],
    )

    for intento in range(max_reintentos):
        try:
            # NUEVO: timeout explícito de 45 segundos para que no se congele jamás
            respuesta = llm_config.client.chat.completions.create(
                model=llm_config.model,
                messages=[
                    {"role": "system", "content": PROMPT_SISTEMA},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1500,
                timeout=TIEMPO_MAX_DESTILACION,
            )
            contenido = respuesta.choices[0].message.content
            data = extraer_json_texto(contenido)
            if data is None:
                raise json.JSONDecodeError("Respuesta no parseable", contenido or "", 0)

            data = normalizar_fecha_creacion(data)
            data = normalizar_scores(data)
            return data

        except json.JSONDecodeError as e:
            logger.warning(f"[ERROR JSON] Intento {intento+1}/{max_reintentos} - Parseo fallido: {e}")
        except Exception as e:
            logger.warning(f"[ERROR API LLM] Intento {intento+1}/{max_reintentos} - {e}")
        
        # Esperar un poco antes del siguiente reintento si no es el último
        if intento < max_reintentos - 1:
            time.sleep(3)

    # Si llega aquí, es porque agotó los 3 intentos
    logger.error(f"[ABORTADO] Se agotaron los {max_reintentos} reintentos para '{noticia['titulo'][:40]}'")
    return None


def validar(data: dict) -> ContratoEmpresaAgentica | None:
    """Valida el JSON contra el contrato"""
    try:
        return ContratoEmpresaAgentica(**data)
    except ValidationError as e:
        errores = [f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
                   for err in e.errors()]
        logger.warning(f"[INVALIDO] {' | '.join(errores[:3])}")
        return None


# ── Prompt de IDENTIDAD OPERATIVA (paso 4 — documento narrativo externo) ──
PROMPT_SISTEMA_IDENTIDAD = """Eres un architecto de organizaciones agénticas.
Recibes un contrato JSON ya validado de una empresa agéntica y debes redactar
su documento de identidad operativa en formato Markdown legible por humanos.

REGLAS DE ESTRUCTURA:
- Agrupa los subagentes recibidos en como máximo 3 "squads", cada uno con un tema claro.
- Cada squad tiene como máximo 3 workers (usa los subagentes reales del contrato).
- El total de agentes en todos los squads no debe exceder 12.
- Incluye una sección de "Runtime Topology" y una "Operating Cadence" semanal razonable.
- Usa el nombre y la descripción reales del contrato.

FORMATO DE SALIDA (Markdown, sin bloques de código, sin texto fuera del documento):

# [Nombre de la empresa]

## Identidad
[2-3 líneas basadas en la descripción real del contrato]

## Operating Cadence
- **[Día]:** [actividad]
- **[Día]:** [actividad]

## Runtime Topology
Instancia exactamente **N orquestaciones de swarm** (N squads orquestadores),
cada uno con máximo 3 workers/subagentes; total de agentes ≤ 12.

### Orchestrator Squads and Workers
1. **[Nombre del squad 1]**
   - Worker 1: [nombre real del subagente]
2. **[Nombre del squad 2]**
   - Worker 1: [nombre real del subagente]

[Cierra con 1-2 líneas explicando por qué esta estructura sirve para escalar.]"""

PROMPT_USUARIO_IDENTIDAD = """Contrato JSON validado de la empresa:

{contrato_json}

Genera el documento de identidad operativa en Markdown siguiendo exactamente
el formato especificado."""


def generar_documento_identidad(contrato: ContratoEmpresaAgentica) -> str | None:
    """PASO 4 del pipeline: Genera un documento narrativo complementario en Markdown."""
    contrato_json = contrato.model_dump_json(exclude_none=True, indent=2)
    prompt = PROMPT_USUARIO_IDENTIDAD.format(contrato_json=contrato_json)

    try:
        respuesta = llm_config.client.chat.completions.create(
            model=llm_config.model,
            messages=[
                {"role": "system", "content": PROMPT_SISTEMA_IDENTIDAD},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=800,
            timeout=TIEMPO_MAX_IDENTIDAD,
        )
        texto = (respuesta.choices[0].message.content or "").strip()

        if texto.startswith("```"):
            texto = texto.split("```")[1]
            if texto.startswith("markdown") or texto.startswith("md"):
                texto = texto.split("\n", 1)[1] if "\n" in texto else texto
        texto = texto.strip()

        return texto

    except Exception as e:
        logger.warning(f"[IDENTIDAD] No se pudo generar el documento: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Destilador")
    parser.add_argument("--limite", type=int, default=None,
                        help="Máximo de noticias a procesar (default: todas)")
    parser.add_argument("--entrada", default="noticias.json",
                        help="Archivo de entrada (default: noticias.json)")
    parser.add_argument("--salida", default="ideas_borrador.json",
                        help="Archivo de salida (default: ideas_borrador.json)")
    parser.add_argument("--umbral-confianza", type=float, default=0.6,
                        help="Confianza mínima para aceptar una idea como viable (default: 0.6)")
    args = parser.parse_args()

    # Cargar noticias
    try:
        with open(args.entrada, encoding="utf-8") as f:
            noticias = json.load(f)
    except FileNotFoundError:
        logger.error(f"No se encontró el archivo de entrada: {args.entrada}")
        sys.exit(1)

    # Filtrar las que tienen contenido útil
    noticias_utiles = [n for n in noticias if tiene_contenido_util(n)]
    logger.info(f"Noticias totales:     {len(noticias)}")
    logger.info(f"Con contenido útil:   {len(noticias_utiles)}")

    if args.limite:
        noticias_utiles = noticias_utiles[:args.limite]
        logger.info(f"Procesando (límite):  {len(noticias_utiles)}")

    ideas_validas = []
    ideas_fallidas = 0
    ideas_descartadas = 0

    logger.info(f"{'─'*60}")

    for i, noticia in enumerate(noticias_utiles, 1):
        titulo_corto = noticia["titulo"][:55]
        logger.info(f"[{i}/{len(noticias_utiles)}] {titulo_corto}...")

        # PASO 1 — ¿Es una idea de negocio agéntico viable?
        evaluacion = evaluar_relevancia(noticia, umbral_confianza=args.umbral_confianza)
        if not evaluacion["es_negocio_viable"]:
            ideas_descartadas += 1
            logger.info(f"    [DESCARTADA] {evaluacion['razon']}")
            time.sleep(1.0)
            continue

        logger.info(f"    [VIABLE] confianza={evaluacion['confianza']:.2f} — {evaluacion['razon']}")

        # PASO 2 — Destilar con el LLM
        data = destilar(noticia)
        if data is None:
            ideas_fallidas += 1
            continue

        # PASO 3 — Validar con Pydantic
        contrato = validar(data)
        if contrato is None:
            ideas_fallidas += 1
            continue

        # PASO 4 — Generar documento de identidad operativa (no bloqueante)
        documento_identidad = generar_documento_identidad(contrato)
        if documento_identidad:
            logger.info(f"    [IDENTIDAD] Documento generado ({len(documento_identidad)} chars)")

        # Agregar metadata del pipeline
        idea = contrato.model_dump(mode="json", exclude_none=True)
        idea["_pipeline"] = {
            "status": "borrador",
            "hash_origen": noticia["hash_url"],
            "procesado_en": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "evaluacion_confianza": evaluacion["confianza"],
            "documento_identidad": documento_identidad,
        }

        ideas_validas.append(idea)
        logger.info(f"    [OK] → {contrato.metadata.nombre} "
                    f"| {len(contrato.subagentes)} subagentes "
                    f"| flujo: {contrato.orquestador.tipo_flujo}")

        if documento_identidad:
            os.makedirs("documentos_identidad", exist_ok=True)
            nombre_archivo = contrato.metadata.nombre.replace(" ", "_").replace("/", "-")
            ruta_md = f"documentos_identidad/{nombre_archivo}_{noticia['hash_url'][:8]}.md"
            with open(ruta_md, "w", encoding="utf-8") as f:
                f.write(documento_identidad)

        time.sleep(1.5)

    # Guardar resultados
    with open(args.salida, "w", encoding="utf-8") as f:
        json.dump(ideas_validas, f, ensure_ascii=False, indent=2)

    logger.info(f"{'─'*60}")
    logger.info(f"Ideas válidas:        {len(ideas_validas)}")
    logger.info(f"Descartadas (paso 1): {ideas_descartadas}")
    logger.info(f"Fallidas (paso 2/3):  {ideas_fallidas}")
    logger.info(f"Guardadas en:         {args.salida}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    main()