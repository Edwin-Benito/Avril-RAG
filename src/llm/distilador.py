"""
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

from src.contracts.models import ContratoEmpresaAgentica
from src.llm.nvidia_client import llm_config

# Importamos los prompts desde nuestra nueva estructura
from src.prompts.evaluacion import PROMPT_SISTEMA_EVALUACION, PROMPT_USUARIO_EVALUACION
from src.prompts.destilacion import PROMPT_SISTEMA, PROMPT_USUARIO
from src.prompts.identidad import PROMPT_SISTEMA_IDENTIDAD, PROMPT_USUARIO_IDENTIDAD

load_dotenv()

logger = logging.getLogger(__name__)

TIEMPO_MAX_EVALUACION = 30.0
TIEMPO_MAX_DESTILACION = 45.0
TIEMPO_MAX_IDENTIDAD = 45.0


def extraer_json_texto(texto: str) -> dict | None:
    
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
  
    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        return data

    fecha = metadata.get("fecha_creacion")
    if not fecha or not isinstance(fecha, str):
        return data

    fecha = fecha.strip()

    if len(fecha) < 8:
        m = re.match(r"^\b(19|20)\d{2}\b$", fecha)
        if m:
            metadata["fecha_creacion"] = f"{m.group(0)}-01-01T00:00:00Z"
            return data
        else:
            logger.warning(f"[FECHA] Input demasiado corto o inválido '{fecha}', se remueve.")
            del metadata["fecha_creacion"]
            return data

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?", fecha):
        if not re.search(r"(Z|[+-]\d{2}:\d{2})$", fecha):
            fecha = fecha + "Z"
        metadata["fecha_creacion"] = fecha
        return data

    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", fecha)
    if m:
        metadata["fecha_creacion"] = f"{m.group(0)}T00:00:00Z"
        return data

    m = re.search(r"(\d{4})-(\d{2})(?!\d)", fecha)
    if m:
        metadata["fecha_creacion"] = f"{m.group(0)}-01T00:00:00Z"
        return data

    m = re.search(r"\b(19|20)\d{2}\b", fecha)
    if m:
        metadata["fecha_creacion"] = f"{m.group(0)}-01-01T00:00:00Z"
        return data

    logger.warning(f"[FECHA] Formato irreconocible '{fecha}', se omite el campo.")
    del metadata["fecha_creacion"]
    return data


def normalizar_scores(data: dict) -> dict:
   
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
        
        if intento < max_reintentos - 1:
            time.sleep(3)

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


def generar_documento_identidad(contrato: ContratoEmpresaAgentica, url_origen: str) -> str | None:
    """PASO 4 del pipeline: Genera un documento narrativo complementario en Markdown."""
    contrato_json = contrato.model_dump_json(exclude_none=True, indent=2)
    
    # Formateamos los prompts inyectando las variables dinámicas de esta noticia
    prompt_sys = PROMPT_SISTEMA_IDENTIDAD.format(url_origen=url_origen)
    prompt_usr = PROMPT_USUARIO_IDENTIDAD.format(
        descripcion=contrato.metadata.descripcion,
        contrato_json=contrato_json
    )

    try:
        respuesta = llm_config.client.chat.completions.create(
            model=llm_config.model,
            messages=[
                {"role": "system", "content": prompt_sys},
                {"role": "user", "content": prompt_usr},
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
            time.sleep(3)
            continue

        logger.info(f"    [VIABLE] confianza={evaluacion['confianza']:.2f} — {evaluacion['razon']}")

        time.sleep(2)

        # PASO 2 — Destilar con el LLM
        data = destilar(noticia)
        if data is None:
            ideas_fallidas += 1
            continue

        time.sleep(2)

        # PASO 3 — Validar con Pydantic
        contrato = validar(data)
        if contrato is None:
            ideas_fallidas += 1
            continue

        # PASO 4 — Generar documento de identidad operativa (no bloqueante)
        documento_identidad = generar_documento_identidad(contrato, noticia["url"])
        
        if documento_identidad:
            logger.info(f"    [IDENTIDAD] Documento generado ({len(documento_identidad)} chars)")

        time.sleep(2)

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

        time.sleep(3)

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