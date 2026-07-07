"""
embeddings_config.py — Configuración modular de embeddings

Centraliza la generación de embeddings semánticos. Soporta múltiples
proveedores (NVIDIA, OpenAI, etc.) sin afectar el resto del código.

Modelos soportados:
  - NVIDIA: nvidia/nv-embedqa-e5-v5 (1024 dims, uso comercial permitido)
  - OpenAI: text-embedding-3-small, text-embedding-3-large (por defecto)
  - Custom: Cualquier modelo compatible
"""

import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class EmbeddingsConfig:
    """Configuración centralizada de embeddings semánticos."""
    
    # Configuración por proveedor
    PROVIDERS = {
        "nvidia": {
            "url": "https://integrate.api.nvidia.com/v1/embeddings",
            "default_model": "nvidia/nv-embedqa-e5-v5",
            "default_dimensions": 1024,
            "api_key_env": "NVIDIA_API_KEY",
        },
        "openai": {
            "url": "https://api.openai.com/v1/embeddings",
            "default_model": "text-embedding-3-small",
            "default_dimensions": 1536,
            "api_key_env": "OPENAI_API_KEY",
        },
    }
    
    def __init__(self):
        """Inicializa la configuración de embeddings."""
        self.provider = os.getenv("EMBEDDINGS_PROVIDER", "nvidia").lower()
        
        if self.provider not in self.PROVIDERS:
            raise ValueError(
                f"Proveedor '{self.provider}' no soportado. "
                f"Opciones: {', '.join(self.PROVIDERS.keys())}"
            )
        
        config = self.PROVIDERS[self.provider]
        self.url = os.getenv("EMBEDDINGS_URL", config["url"])
        self.model = os.getenv("EMBEDDINGS_MODEL", config["default_model"])
        self.dimensions = int(os.getenv(
            "EMBEDDINGS_DIMENSIONS",
            config["default_dimensions"]
        ))
        
        # Obtener API key según el proveedor
        self.api_key = os.getenv(config["api_key_env"])
        if not self.api_key:
            logger.warning(
                f"[EMBEDDINGS] Falta {config['api_key_env']} "
                f"para provider '{self.provider}'"
            )
        
        logger.info(
            f"[EMBEDDINGS] Inicializado: provider='{self.provider}', "
            f"model='{self.model}', dimensions={self.dimensions}"
        )
    
    def generar_embedding(self, texto: str) -> list[float] | None:
        """
        Genera un embedding semántico para el texto dado.
        
        Args:
            texto: Texto a embedir
        
        Returns:
            Lista de floats representando el embedding (o None si falla)
        """
        if not self.api_key:
            logger.warning("[EMBEDDINGS] API key no configurada, embedding omitido")
            return None
        
        if not texto or not texto.strip():
            logger.warning("[EMBEDDINGS] Texto vacío, embedding omitido")
            return None
        
        try:
            payload = {
                "input": [texto],
                "model": self.model,
                "encoding_format": "float",
            }
            
            # Añadir parámetros específicos según el proveedor
            if self.provider == "nvidia":
                payload["input_type"] = "passage"
                payload["truncate"] = "END"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            
            respuesta = requests.post(
                self.url,
                json=payload,
                headers=headers,
                timeout=15,
            )
            respuesta.raise_for_status()
            
            data = respuesta.json()
            embedding = data["data"][0]["embedding"]
            
            # Validar dimensiones
            if len(embedding) != self.dimensions:
                logger.warning(
                    f"[EMBEDDINGS] Dimensión inesperada: {len(embedding)} "
                    f"(se esperaba {self.dimensions}). Embedding omitido."
                )
                return None
            
            return embedding
        
        except requests.exceptions.Timeout:
            logger.warning("[EMBEDDINGS] Timeout en generación de embedding")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"[EMBEDDINGS] Error HTTP: {e}")
            return None
        except (KeyError, IndexError) as e:
            logger.warning(f"[EMBEDDINGS] Respuesta inesperada: {e}")
            return None
        except Exception as e:
            logger.warning(f"[EMBEDDINGS] Error inesperado: {e}")
            return None
    
    def cambiar_provider(self, nuevo_provider: str, nueva_api_key: str = None):
        """Cambia el proveedor de embeddings en tiempo de ejecución."""
        nuevo_provider = nuevo_provider.lower()
        
        if nuevo_provider not in self.PROVIDERS:
            raise ValueError(
                f"Proveedor '{nuevo_provider}' no soportado. "
                f"Opciones: {', '.join(self.PROVIDERS.keys())}"
            )
        
        config = self.PROVIDERS[nuevo_provider]
        self.provider = nuevo_provider
        self.url = config["url"]
        self.model = config["default_model"]
        self.dimensions = config["default_dimensions"]
        
        if nueva_api_key:
            self.api_key = nueva_api_key
        else:
            self.api_key = os.getenv(config["api_key_env"], "")
        
        logger.info(
            f"[EMBEDDINGS] Proveedor cambiado a '{self.provider}', "
            f"model='{self.model}', dimensions={self.dimensions}"
        )
    
    def cambiar_modelo(self, nuevo_modelo: str, nuevas_dimensiones: int = None):
        """Cambia el modelo de embeddings en tiempo de ejecución."""
        self.model = nuevo_modelo
        if nuevas_dimensiones:
            self.dimensions = nuevas_dimensiones
        logger.info(
            f"[EMBEDDINGS] Modelo cambiado a '{self.model}', "
            f"dimensions={self.dimensions}"
        )
    
    def obtener_estado(self) -> dict:
        """Retorna el estado actual de la configuración de embeddings."""
        return {
            "provider": self.provider,
            "model": self.model,
            "dimensions": self.dimensions,
            "url": self.url,
            "api_key_configurada": bool(self.api_key),
        }


# Instancia global de embeddings
embeddings_config = EmbeddingsConfig()
