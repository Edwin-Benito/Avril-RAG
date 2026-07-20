"""
llm_config.py — Configuración modular del LLM

Centraliza la configuración del cliente LLM y permite cambiar API keys,
modelos y proveedores fácilmente sin modificar distilador.py.

Soporta:
  - NVIDIA API (por defecto)
  - OpenAI API
  - Otros proveedores compatible con OpenAI (local, Ollama, etc.)
"""

import os
import logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class LLMConfig:
    """Configuración centralizada del cliente LLM."""
    
    # Valores por defecto (pueden ser sobrescritos por variables de entorno)
    DEFAULT_PROVIDER = "nvidia"  # Options: "nvidia", "openai", "custom"
    DEFAULT_MODEL = "meta/llama-3.1-70b-instruct"
    
    # URLs base por proveedor
    PROVIDER_URLS = {
        "nvidia": "https://integrate.api.nvidia.com/v1",
        "openai": "https://api.openai.com/v1",
        "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "groq": "https://api.groq.com/openai/v1",
    }
    
    def __init__(self):
        """Inicializa la configuración leyendo variables de entorno."""
        self.provider = os.getenv("LLM_PROVIDER", self.DEFAULT_PROVIDER).lower()
        self.model = os.getenv("LLM_MODEL", self.DEFAULT_MODEL)
        self.api_key = self._obtener_api_key()
        self.base_url = self._obtener_base_url()
        self.client = None
        self._inicializar_cliente()
    
    def _obtener_api_key(self) -> str:
        """Obtiene la API key según el proveedor."""
        if self.provider == "nvidia":
            key = os.getenv("NVIDIA_API_KEY")
            if not key:
                logger.error("Falta NVIDIA_API_KEY en variables de entorno")
                raise ValueError("NVIDIA_API_KEY requerida para provider 'nvidia'")
            return key
        elif self.provider == "openai":
            key = os.getenv("OPENAI_API_KEY")
            if not key:
                logger.error("Falta OPENAI_API_KEY en variables de entorno")
                raise ValueError("OPENAI_API_KEY requerida para provider 'openai'")
            return key
        elif self.provider == "gemini":
            key = os.getenv("GOOGLE_API_KEY")
            if not key:
                logger.error("Falta GOOGLE_API_KEY en variables de entorno")
                raise ValueError("GOOGLE_API_KEY requerida para provider 'gemini'")
            return key
        elif self.provider == "groq":
            key = os.getenv("GROQ_API_KEY")
            if not key:
                logger.error("Falta GROQ_API_KEY en variables de entorno")
                raise ValueError("GROQ_API_KEY requerida para provider 'groq'")
            return key
        else:
            # Para proveedores custom, espera LLM_API_KEY
            key = os.getenv("LLM_API_KEY")
            if not key:
                logger.warning(f"Proveedor '{self.provider}' requiere LLM_API_KEY")
            return key or ""
    
    def _obtener_base_url(self) -> str:
        """Obtiene la URL base según el proveedor."""
        if self.provider in self.PROVIDER_URLS:
            return self.PROVIDER_URLS[self.provider]
        # Para custom, espera LLM_BASE_URL
        url = os.getenv("LLM_BASE_URL")
        if not url:
            logger.warning(f"Proveedor '{self.provider}' requiere LLM_BASE_URL")
        return url or ""
    
    def _inicializar_cliente(self):
        """Crea el cliente OpenAI compatible."""
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
        logger.info(
            f"[LLM] Inicializado: provider='{self.provider}', "
            f"model='{self.model}', url='{self.base_url}'"
        )
    
    def generar_completacion(
        self,
        mensajes: list[dict],
        temperatura: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """
        Genera una completación usando el cliente LLM.
        
        Args:
            mensajes: Lista de dicts con 'role' y 'content'
            temperatura: Control de creatividad (0.0-2.0)
            max_tokens: Máximo de tokens en la respuesta
        
        Returns:
            Texto de la respuesta o None si falla
        """
        try:
            respuesta = self.client.chat.completions.create(
                model=self.model,
                messages=mensajes,
                temperature=temperatura,
                max_tokens=max_tokens,
            )
            return respuesta.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generando completación: {e}")
            return None
    
    def cambiar_provider(self, nuevo_provider: str, nueva_api_key: str = None):
        """Cambia el proveedor LLM en tiempo de ejecución."""
        self.provider = nuevo_provider.lower()
        if nueva_api_key:
            self.api_key = nueva_api_key
        else:
            self.api_key = self._obtener_api_key()
        self.base_url = self._obtener_base_url()
        self._inicializar_cliente()
        logger.info(f"[LLM] Proveedor cambiado a '{self.provider}'")
    
    def cambiar_modelo(self, nuevo_modelo: str):
        """Cambia el modelo LLM en tiempo de ejecución."""
        self.model = nuevo_modelo
        logger.info(f"[LLM] Modelo cambiado a '{self.model}'")
    
    def obtener_estado(self) -> dict:
        """Retorna el estado actual de la configuración LLM."""
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "api_key_configurada": bool(self.api_key),
        }


# Instancia global del cliente LLM
llm_config = LLMConfig()
