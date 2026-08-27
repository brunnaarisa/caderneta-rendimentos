"""Serviço para buscar a taxa CDI ao vivo do Banco Central."""

import logging
from datetime import datetime

import aiohttp

from config import BCB_CDI_URL

logger = logging.getLogger(__name__)

# Cache em memória
_cache: dict = {"taxa": None, "data": None, "buscado_em": None}


async def get_cdi_atual() -> dict:
    """
    Busca a taxa CDI mais recente da API do Banco Central.
    Retorna {"taxa": float, "data": str} ou o último valor cacheado.
    """
    global _cache

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(BCB_CDI_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    dados = await resp.json()
                    if dados and len(dados) > 0:
                        _cache = {
                            "taxa": float(dados[0]["valor"]),
                            "data": dados[0]["data"],
                            "buscado_em": datetime.now().isoformat(),
                        }
                        logger.info("CDI atualizado: %s%% em %s", _cache["taxa"], _cache["data"])
                        return _cache
    except Exception as e:
        logger.warning("Erro ao buscar CDI: %s", e)

    if _cache["taxa"] is not None:
        logger.info("Usando CDI em cache: %s%%", _cache["taxa"])
        return _cache

    # Fallback — valor aproximado
    return {"taxa": 13.65, "data": "fallback", "buscado_em": None}


def cdi_anual(taxa_diaria: float) -> float:
    """Converte CDI diário para anual (252 dias úteis)."""
    return ((1 + taxa_diaria / 100) ** 252 - 1) * 100
