"""
Uso:
    python distilador.py                  # procesa todas las noticias
    python distilador.py --limite 5       # solo las primeras 5 (para pruebas)
"""

import json
import sys
import argparse
import time
from openai import OpenAI
from pydantic import ValidationError
from dotenv import load_dotenv
import os

from contrato_models import ContratoEmpresaAgentica

load_dotenv()

# ── Cliente NVIDIA ─────────────────────────────────────────────────────────────
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY"),
)

MODEL = "meta/llama-3.1-70b-instruct"

# ── Prompt de destilación ──────────────────────────────────────────────────────
PROMPT_SISTEMA = """Eres un analista experto en modelos de negocio de IA agéntica.
Tu tarea es convertir noticias sobre startups o productos de IA en ideas de negocio
estructuradas en formato JSON estricto.

REGLAS OBLIGATORIAS:
- Responde ÚNICAMENTE con un objeto JSON válido. Sin texto antes ni después.
- Sin bloques de código, sin comillas triples, sin explicaciones.
- El JSON debe cumplir exactamente este schema.

SCHEMA REQUERIDO:
{
  "version": "1.0.0",
  "metadata": {
    "nombre": "string (2-100 chars, requerido)",
    "descripcion": "string (10-500 chars, requerido)",
    "origen": "string URL (requerido)",
    "modelo_negocio": "string opcional (SaaS, marketplace, freemium, etc.)",
    "industria": "string opcional",
    "fecha_creacion": "string ISO 8601 opcional",
    "tags": ["array de strings opcional"]
  },
  "subagentes": [
    {
      "id": "string snake_case requerido",
      "nombre": "string requerido",
      "rol": "string requerido",
      "modelo_llm": "claude-3-haiku | claude-3-5-sonnet | gpt-4o | gpt-4o-mini (opcional)",
      "skills": [
        {
          "nombre": "string requerido",
          "descripcion": "string opcional"
        }
      ]
    }
  ],
  "orquestador": {
    "tipo_flujo": "secuencial | paralelo | condicional | mixto (requerido)"
  },
  "limites": {
    "tope_tokens_total": integer >= 1000 (opcional),
    "tope_tokens_por_agente": integer >= 500 (opcional),
    "timeout_segundos": integer >= 10 (opcional),
    "tope_gasto_usd": number >= 0 (opcional)
  }
}"""

PROMPT_USUARIO = """Convierte esta noticia en una idea de negocio agéntico estructurada.
Infiere subagentes razonables (mínimo 2), sus skills, el tipo de orquestación y límites conservadores.

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


def destilar(noticia: dict) -> dict | None:
    """Llama al LLM y retorna el JSON parseado, o None si falla."""
    prompt = PROMPT_USUARIO.format(
        titulo=noticia["titulo"],
        fuente=noticia["fuente"],
        url=noticia["url"],
        resumen=noticia["resumen"][:800],
    )

    try:
        respuesta = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        texto = respuesta.choices[0].message.content.strip()

        # Limpiar posibles bloques de código que el modelo agregue
        if texto.startswith("```"):
            texto = texto.split("```")[1]
            if texto.startswith("json"):
                texto = texto[4:]
        texto = texto.strip()

        return json.loads(texto)

    except json.JSONDecodeError as e:
        print(f"    [ERROR JSON] No se pudo parsear la respuesta: {e}")
        return None
    except Exception as e:
        print(f"    [ERROR API] {e}")
        return None


def validar(data: dict) -> ContratoEmpresaAgentica | None:
    """Valida el JSON contra el contrato"""
    try:
        return ContratoEmpresaAgentica(**data)
    except ValidationError as e:
        errores = [f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
                   for err in e.errors()]
        print(f"    [INVALIDO] {' | '.join(errores[:3])}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Destilador")
    parser.add_argument("--limite", type=int, default=None,
                        help="Máximo de noticias a procesar (default: todas)")
    parser.add_argument("--entrada", default="noticias.json",
                        help="Archivo de entrada (default: noticias.json)")
    parser.add_argument("--salida", default="ideas_borrador.json",
                        help="Archivo de salida (default: ideas_borrador.json)")
    args = parser.parse_args()

    # Cargar noticias
    with open(args.entrada, encoding="utf-8") as f:
        noticias = json.load(f)

    # Filtrar las que tienen contenido útil
    noticias_utiles = [n for n in noticias if tiene_contenido_util(n)]
    print(f"\nNoticias totales:     {len(noticias)}")
    print(f"Con contenido útil:   {len(noticias_utiles)}")

    if args.limite:
        noticias_utiles = noticias_utiles[:args.limite]
        print(f"Procesando (límite):  {len(noticias_utiles)}")

    ideas_validas = []
    ideas_fallidas = 0

    print(f"\n{'─'*60}")

    for i, noticia in enumerate(noticias_utiles, 1):
        titulo_corto = noticia["titulo"][:55]
        print(f"\n[{i}/{len(noticias_utiles)}] {titulo_corto}...")

        # Destilar con el LLM
        data = destilar(noticia)
        if data is None:
            ideas_fallidas += 1
            continue

        # Validar con Pydantic
        contrato = validar(data)
        if contrato is None:
            ideas_fallidas += 1
            continue

        # Agregar metadata del pipeline
        idea = contrato.model_dump(mode="json", exclude_none=True)
        idea["_pipeline"] = {
            "status": "borrador",
            "hash_origen": noticia["hash_url"],
            "procesado_en": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        ideas_validas.append(idea)
        print(f"    [OK] → {contrato.metadata.nombre} "
              f"| {len(contrato.subagentes)} subagentes "
              f"| flujo: {contrato.orquestador.tipo_flujo}")

        # Pausa para respetar rate limits de NVIDIA
        time.sleep(1.5)

    # Guardar resultados
    with open(args.salida, "w", encoding="utf-8") as f:
        json.dump(ideas_validas, f, ensure_ascii=False, indent=2)

    print(f"\n{'─'*60}")
    print(f"Ideas válidas:  {len(ideas_validas)}")
    print(f"Fallidas:       {ideas_fallidas}")
    print(f"Guardadas en:   {args.salida}")


if __name__ == "__main__":
    main()