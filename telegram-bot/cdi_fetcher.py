"""
Busca CDI e IPCA ao vivo das APIs públicas do Banco Central.
Cacheia valores pra não bater na API a cada mensagem.
"""
import time
import logging
from urllib.request import urlopen, Request
from urllib.error import URLError
import json

logger = logging.getLogger(__name__)

# Cache em memória
_cache = {
    'cdi_annual': 13.90,  # fallback
    'cdi_fetched_at': 0,
    'ipca_annual': 4.50,  # fallback
    'ipca_fetched_at': 0,
}

CACHE_TTL = 3600  # 1 hora


def fetch_cdi():
    """Busca taxa CDI anual do Banco Central."""
    now = time.time()
    if now - _cache['cdi_fetched_at'] < CACHE_TTL:
        return _cache['cdi_annual']

    try:
        url = 'https://api.bcb.gov.br/dados/serie/bcdata.sgs.4389/dados/ultimos/1?formato=json'
        req = Request(url, headers={'Accept': 'application/json'})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if data and len(data) > 0:
                daily_rate = float(data[0]['valor'].replace(',', '.'))
                annual = (pow(1 + daily_rate / 100, 252) - 1) * 100
                _cache['cdi_annual'] = round(annual, 2)
                _cache['cdi_fetched_at'] = now
                logger.info(f'CDI atualizado: {_cache["cdi_annual"]}% a.a.')
    except Exception as e:
        logger.warning(f'Falha ao buscar CDI: {e}')

    return _cache['cdi_annual']


def fetch_ipca():
    """Busca IPCA acumulado 12 meses do IBGE/BCB."""
    now = time.time()
    if now - _cache['ipca_fetched_at'] < CACHE_TTL:
        return _cache['ipca_annual']

    try:
        url = 'https://api.bcb.gov.br/dados/serie/bcdata.sgs.13522/dados/ultimos/1?formato=json'
        req = Request(url, headers={'Accept': 'application/json'})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if data and len(data) > 0:
                ipca = float(data[0]['valor'].replace(',', '.'))
                _cache['ipca_annual'] = round(ipca, 2)
                _cache['ipca_fetched_at'] = now
                logger.info(f'IPCA atualizado: {_cache["ipca_annual"]}% a.a.')
    except Exception as e:
        logger.warning(f'Falha ao buscar IPCA: {e}')

    return _cache['ipca_annual']


def get_rates():
    """Retorna CDI e IPCA atuais."""
    return {
        'cdi': fetch_cdi(),
        'ipca': fetch_ipca(),
    }
