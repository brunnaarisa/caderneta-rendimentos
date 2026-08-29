"""
Serviço de análise de mercado — busca preços, analisa tendências
e gera sinais de compra/venda.

APIs gratuitas usadas:
- CoinGecko: preços e histórico de criptomoedas
- BRAPI (brapi.dev): preços de ações e FIIs da B3
- Alternative.me: Fear & Greed Index (cripto)
"""

import logging
from datetime import datetime, timedelta

import aiohttp

logger = logging.getLogger(__name__)

# Cache em memória para não bater rate limit
_cache: dict = {}
CACHE_TTL = 300  # 5 minutos


def _cache_key(name: str) -> str:
    return f"market_{name}"


def _is_cached(key: str) -> bool:
    if key not in _cache:
        return False
    cached_at = _cache[key].get("_cached_at", 0)
    return (datetime.now().timestamp() - cached_at) < CACHE_TTL


# ── APIs de preço ──────────────────────────────────────────────


async def get_crypto_price(coin_id: str = "bitcoin") -> dict | None:
    """Busca preço atual de uma cripto via CoinGecko."""
    key = _cache_key(f"crypto_{coin_id}")
    if _is_cached(key):
        return _cache[key]

    url = (
        f"https://api.coingecko.com/api/v3/simple/price"
        f"?ids={coin_id}&vs_currencies=brl&include_24hr_change=true"
        f"&include_24hr_vol=true&include_market_cap=true"
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if coin_id in data:
                        result = {
                            "preco_brl": data[coin_id].get("brl", 0),
                            "variacao_24h": data[coin_id].get("brl_24h_change", 0),
                            "market_cap": data[coin_id].get("brl_market_cap", 0),
                            "volume_24h": data[coin_id].get("brl_24h_vol", 0),
                            "_cached_at": datetime.now().timestamp(),
                        }
                        _cache[key] = result
                        return result
    except Exception as e:
        logger.warning("Erro ao buscar preço crypto %s: %s", coin_id, e)
    return None


async def get_crypto_history(coin_id: str = "bitcoin", days: int = 90) -> list | None:
    """Busca histórico de preços de uma cripto (últimos N dias)."""
    key = _cache_key(f"crypto_hist_{coin_id}_{days}")
    if _is_cached(key):
        return _cache[key].get("prices")

    url = (
        f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        f"?vs_currency=brl&days={days}"
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    prices = [
                        {"timestamp": p[0], "preco": p[1]}
                        for p in data.get("prices", [])
                    ]
                    _cache[key] = {
                        "prices": prices,
                        "_cached_at": datetime.now().timestamp(),
                    }
                    return prices
    except Exception as e:
        logger.warning("Erro ao buscar histórico crypto %s: %s", coin_id, e)
    return None


async def get_fear_greed_index() -> dict | None:
    """Busca o Fear & Greed Index do mercado cripto."""
    key = _cache_key("fear_greed")
    if _is_cached(key):
        return _cache[key]

    url = "https://api.alternative.me/fng/?limit=1"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("data"):
                        fng = data["data"][0]
                        result = {
                            "valor": int(fng["value"]),
                            "classificacao": fng["value_classification"],
                            "_cached_at": datetime.now().timestamp(),
                        }
                        _cache[key] = result
                        return result
    except Exception as e:
        logger.warning("Erro ao buscar Fear & Greed: %s", e)
    return None


async def get_stock_price(ticker: str) -> dict | None:
    """Busca preço atual de uma ação/FII da B3 via BRAPI."""
    key = _cache_key(f"stock_{ticker}")
    if _is_cached(key):
        return _cache[key]

    url = f"https://brapi.dev/api/quote/{ticker}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get("results", [])
                    if results:
                        stock = results[0]
                        result = {
                            "ticker": stock.get("symbol", ticker),
                            "nome": stock.get("longName", ticker),
                            "preco": stock.get("regularMarketPrice", 0),
                            "variacao_dia": stock.get("regularMarketChangePercent", 0),
                            "max_52sem": stock.get("fiftyTwoWeekHigh", 0),
                            "min_52sem": stock.get("fiftyTwoWeekLow", 0),
                            "max_dia": stock.get("regularMarketDayHigh", 0),
                            "min_dia": stock.get("regularMarketDayLow", 0),
                            "_cached_at": datetime.now().timestamp(),
                        }
                        _cache[key] = result
                        return result
    except Exception as e:
        logger.warning("Erro ao buscar ação %s: %s", ticker, e)
    return None


# ── Análise técnica simplificada ───────────────────────────────


def calcular_medias_moveis(prices: list[dict]) -> dict:
    """Calcula médias móveis simples de 7, 30 e 90 dias."""
    if not prices or len(prices) < 7:
        return {}

    precos = [p["preco"] for p in prices]

    def media(lst, n):
        if len(lst) < n:
            return None
        return sum(lst[-n:]) / n

    preco_atual = precos[-1]
    mm7 = media(precos, 7)
    mm30 = media(precos, 30)
    mm90 = media(precos, 90) if len(precos) >= 90 else None

    return {
        "preco_atual": preco_atual,
        "mm7": mm7,
        "mm30": mm30,
        "mm90": mm90,
        "acima_mm7": preco_atual > mm7 if mm7 else None,
        "acima_mm30": preco_atual > mm30 if mm30 else None,
        "acima_mm90": preco_atual > mm90 if mm90 else None,
    }


def calcular_suporte_resistencia(prices: list[dict]) -> dict:
    """Identifica suporte e resistência recentes."""
    if not prices or len(prices) < 14:
        return {}

    precos = [p["preco"] for p in prices]

    # Máxima e mínima dos últimos 30 e 90 dias
    max_30d = max(precos[-30:]) if len(precos) >= 30 else max(precos)
    min_30d = min(precos[-30:]) if len(precos) >= 30 else min(precos)
    max_90d = max(precos) if len(precos) >= 90 else max(precos)
    min_90d = min(precos) if len(precos) >= 90 else min(precos)

    preco_atual = precos[-1]

    # Distância percentual do topo e do fundo
    dist_topo_30d = ((max_30d - preco_atual) / max_30d * 100) if max_30d else 0
    dist_fundo_30d = ((preco_atual - min_30d) / min_30d * 100) if min_30d else 0

    return {
        "max_30d": max_30d,
        "min_30d": min_30d,
        "max_90d": max_90d,
        "min_90d": min_90d,
        "dist_topo_30d_pct": round(dist_topo_30d, 1),
        "dist_fundo_30d_pct": round(dist_fundo_30d, 1),
    }


def calcular_momentum(prices: list[dict]) -> dict:
    """Calcula indicadores de momentum simplificados."""
    if not prices or len(prices) < 14:
        return {}

    precos = [p["preco"] for p in prices]
    preco_atual = precos[-1]

    # Variação percentual em diferentes períodos
    var_7d = ((preco_atual - precos[-7]) / precos[-7] * 100) if len(precos) >= 7 else 0
    var_30d = ((preco_atual - precos[-30]) / precos[-30] * 100) if len(precos) >= 30 else 0
    var_90d = ((preco_atual - precos[-90]) / precos[-90] * 100) if len(precos) >= 90 else 0

    # RSI simplificado (14 períodos)
    gains = []
    losses = []
    window = precos[-15:]  # precisa de 15 para 14 variações
    for i in range(1, len(window)):
        change = window[i] - window[i - 1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(gains) / len(gains) if gains else 0
    avg_loss = sum(losses) / len(losses) if losses else 0.001

    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    rsi = 100 - (100 / (1 + rs))

    return {
        "var_7d": round(var_7d, 1),
        "var_30d": round(var_30d, 1),
        "var_90d": round(var_90d, 1),
        "rsi_14": round(rsi, 1),
    }


# ── Análise completa ──────────────────────────────────────────


def gerar_sinal(
    medias: dict, suporte: dict, momentum: dict, fear_greed: dict | None
) -> dict:
    """
    Gera um sinal de compra/venda baseado na análise técnica.

    Retorna:
        sinal: "COMPRA_FORTE", "COMPRA", "NEUTRO", "VENDA", "VENDA_FORTE"
        score: -100 a +100
        motivos: lista de razões
    """
    score = 0
    motivos = []

    # 1. Médias móveis (tendência)
    if medias.get("acima_mm7") and medias.get("acima_mm30"):
        score += 15
        motivos.append("📈 Preço acima das médias de 7 e 30 dias (tendência de alta)")
    elif not medias.get("acima_mm7") and not medias.get("acima_mm30"):
        score -= 15
        motivos.append("📉 Preço abaixo das médias de 7 e 30 dias (tendência de baixa)")

    if medias.get("acima_mm90") is True:
        score += 10
        motivos.append("📈 Acima da média de 90 dias (tendência de longo prazo positiva)")
    elif medias.get("acima_mm90") is False:
        score -= 10
        motivos.append("📉 Abaixo da média de 90 dias (tendência de longo prazo negativa)")

    # 2. Suporte e resistência
    dist_topo = suporte.get("dist_topo_30d_pct", 0)
    dist_fundo = suporte.get("dist_fundo_30d_pct", 0)

    if dist_topo < 3:
        score -= 15
        motivos.append(
            f"⚠️ Muito perto do topo dos últimos 30 dias "
            f"(a {dist_topo:.1f}% da máxima) — cuidado ao comprar no topo"
        )
    elif dist_topo > 20:
        score += 15
        motivos.append(
            f"💡 {dist_topo:.1f}% abaixo do topo de 30 dias — "
            f"pode ser oportunidade de compra"
        )

    if dist_fundo < 5:
        score += 10
        motivos.append("🔍 Perto do fundo recente — possível zona de suporte")

    # 3. Momentum / RSI
    rsi = momentum.get("rsi_14", 50)
    if rsi > 70:
        score -= 20
        motivos.append(
            f"🔴 RSI em {rsi:.0f} (sobrecomprado) — mercado pode corrigir em breve"
        )
    elif rsi < 30:
        score += 20
        motivos.append(
            f"🟢 RSI em {rsi:.0f} (sobrevendido) — possível fundo, momento de compra"
        )
    elif rsi < 45:
        score += 5
        motivos.append(f"🟡 RSI em {rsi:.0f} — região neutra para baixo")
    elif rsi > 55:
        score -= 5
        motivos.append(f"🟡 RSI em {rsi:.0f} — região neutra para cima")

    # 4. Variação recente
    var_7d = momentum.get("var_7d", 0)
    if var_7d > 15:
        score -= 10
        motivos.append(
            f"⚡ Subiu {var_7d:.1f}% em 7 dias — alta forte, risco de correção"
        )
    elif var_7d < -15:
        score += 10
        motivos.append(
            f"💥 Caiu {var_7d:.1f}% em 7 dias — queda forte, possível oportunidade"
        )

    # 5. Fear & Greed Index (cripto)
    if fear_greed:
        fg_valor = fear_greed.get("valor", 50)
        fg_class = fear_greed.get("classificacao", "")
        if fg_valor <= 25:
            score += 15
            motivos.append(
                f"😰 Fear & Greed: {fg_valor} ({fg_class}) — "
                f"mercado com medo extremo (historicamente bom para comprar)"
            )
        elif fg_valor >= 75:
            score -= 15
            motivos.append(
                f"🤑 Fear & Greed: {fg_valor} ({fg_class}) — "
                f"mercado com ganância extrema (historicamente hora de cautela)"
            )
        else:
            motivos.append(
                f"😐 Fear & Greed: {fg_valor} ({fg_class})"
            )

    # Determinar sinal
    if score >= 30:
        sinal = "COMPRA_FORTE"
    elif score >= 10:
        sinal = "COMPRA"
    elif score <= -30:
        sinal = "VENDA_FORTE"
    elif score <= -10:
        sinal = "VENDA"
    else:
        sinal = "NEUTRO"

    return {"sinal": sinal, "score": score, "motivos": motivos}


SINAL_EMOJI = {
    "COMPRA_FORTE": "🟢🟢",
    "COMPRA": "🟢",
    "NEUTRO": "🟡",
    "VENDA": "🔴",
    "VENDA_FORTE": "🔴🔴",
}

SINAL_TEXTO = {
    "COMPRA_FORTE": "Ótimo momento para comprar",
    "COMPRA": "Bom momento para comprar",
    "NEUTRO": "Momento neutro — sem sinal claro",
    "VENDA": "Considere vender ou esperar",
    "VENDA_FORTE": "Forte sinal de venda — considere realizar lucro",
}


async def analise_completa_crypto(coin_id: str = "bitcoin") -> dict | None:
    """Faz análise completa de uma criptomoeda."""
    preco = await get_crypto_price(coin_id)
    historico = await get_crypto_history(coin_id, 90)
    fear_greed = await get_fear_greed_index()

    if not preco or not historico:
        return None

    medias = calcular_medias_moveis(historico)
    suporte = calcular_suporte_resistencia(historico)
    momentum = calcular_momentum(historico)
    sinal = gerar_sinal(medias, suporte, momentum, fear_greed)

    return {
        "ativo": coin_id,
        "preco": preco,
        "medias": medias,
        "suporte": suporte,
        "momentum": momentum,
        "fear_greed": fear_greed,
        "sinal": sinal,
    }


async def analise_completa_acao(ticker: str) -> dict | None:
    """Faz análise de uma ação/FII da B3 (mais limitada sem histórico completo)."""
    stock = await get_stock_price(ticker)
    if not stock:
        return None

    # Análise com os dados disponíveis
    preco = stock["preco"]
    max_52 = stock.get("max_52sem", preco)
    min_52 = stock.get("min_52sem", preco)

    dist_topo = ((max_52 - preco) / max_52 * 100) if max_52 else 0
    dist_fundo = ((preco - min_52) / min_52 * 100) if min_52 else 0

    motivos = []
    score = 0

    # Variação do dia
    var_dia = stock.get("variacao_dia", 0)
    if var_dia > 3:
        score -= 5
        motivos.append(f"📈 Subiu {var_dia:.1f}% hoje")
    elif var_dia < -3:
        score += 5
        motivos.append(f"📉 Caiu {var_dia:.1f}% hoje")

    # Posição em relação a 52 semanas
    if dist_topo < 5:
        score -= 10
        motivos.append(
            f"⚠️ A {dist_topo:.1f}% da máxima de 52 semanas (R${max_52:.2f}) — perto do topo"
        )
    elif dist_topo > 30:
        score += 15
        motivos.append(
            f"💡 {dist_topo:.1f}% abaixo da máxima de 52 sem. — pode ser oportunidade"
        )

    if dist_fundo < 10:
        score += 10
        motivos.append(
            f"🔍 Perto da mínima de 52 sem. (R${min_52:.2f}) — zona de suporte"
        )

    # Classificar sinal
    if score >= 15:
        sinal_nome = "COMPRA"
    elif score <= -15:
        sinal_nome = "VENDA"
    else:
        sinal_nome = "NEUTRO"

    return {
        "ativo": ticker,
        "stock": stock,
        "dist_topo_52sem": round(dist_topo, 1),
        "dist_fundo_52sem": round(dist_fundo, 1),
        "sinal": {"sinal": sinal_nome, "score": score, "motivos": motivos},
    }


# ── Verificar oportunidades de venda para a carteira ───────────


async def verificar_carteira(compras: list[dict]) -> list[dict]:
    """
    Verifica cada ativo da carteira e gera alertas de venda se apropriado.

    compras: [{"ativo": "bitcoin", "tipo": "crypto", "preco_compra": 300000,
               "valor_investido": 125, "data_compra": "2025-01-15"}, ...]

    Retorna lista de alertas para enviar ao usuário.
    """
    alertas = []

    for compra in compras:
        tipo = compra.get("tipo", "crypto")
        ativo = compra["ativo"]
        preco_compra = compra["preco_compra"]
        valor_investido = compra["valor_investido"]

        if tipo == "crypto":
            analise = await analise_completa_crypto(ativo)
            if not analise:
                continue

            preco_atual = analise["preco"]["preco_brl"]
            variacao_pct = ((preco_atual - preco_compra) / preco_compra) * 100
            lucro_estimado = valor_investido * variacao_pct / 100

            alerta = {
                "ativo": ativo.upper(),
                "tipo": tipo,
                "preco_compra": preco_compra,
                "preco_atual": preco_atual,
                "variacao_pct": round(variacao_pct, 1),
                "valor_investido": valor_investido,
                "valor_atual_estimado": round(valor_investido + lucro_estimado, 2),
                "lucro_estimado": round(lucro_estimado, 2),
                "sinal": analise["sinal"],
                "data_compra": compra.get("data_compra", ""),
            }

            # Gerar recomendação de ação
            sinal = analise["sinal"]["sinal"]
            if variacao_pct >= 50 and sinal in ("VENDA", "VENDA_FORTE"):
                alerta["acao"] = "VENDER"
                alerta["mensagem"] = (
                    f"🔔 Seu {ativo.upper()} valorizou {variacao_pct:.0f}% "
                    f"e os indicadores sugerem venda. Considere realizar lucro!"
                )
            elif variacao_pct >= 100:
                alerta["acao"] = "VENDER_PARCIAL"
                alerta["mensagem"] = (
                    f"🚀 Seu {ativo.upper()} DOBROU de valor! "
                    f"Que tal vender metade e garantir o lucro?"
                )
            elif variacao_pct <= -25 and sinal in ("COMPRA", "COMPRA_FORTE"):
                alerta["acao"] = "COMPRAR_MAIS"
                alerta["mensagem"] = (
                    f"📉 Seu {ativo.upper()} caiu {abs(variacao_pct):.0f}%, "
                    f"mas os indicadores sugerem recuperação. "
                    f"Indicadores sugerem possível recuperação."
                )
            elif variacao_pct <= -40:
                alerta["acao"] = "ATENÇÃO"
                alerta["mensagem"] = (
                    f"⚠️ Seu {ativo.upper()} caiu {abs(variacao_pct):.0f}%. "
                    f"Avalie se a tese de investimento ainda faz sentido."
                )
            elif sinal == "VENDA_FORTE" and variacao_pct > 0:
                alerta["acao"] = "CONSIDERAR_VENDA"
                alerta["mensagem"] = (
                    f"🟡 Indicadores do {ativo.upper()} apontam para venda. "
                    f"Você está com {variacao_pct:.0f}% de lucro."
                )
            else:
                alerta["acao"] = "MANTER"
                alerta["mensagem"] = None  # sem alerta

            alertas.append(alerta)

        elif tipo == "acao":
            stock = await get_stock_price(ativo)
            if not stock:
                continue

            preco_atual = stock["preco"]
            variacao_pct = ((preco_atual - preco_compra) / preco_compra) * 100
            lucro_estimado = valor_investido * variacao_pct / 100

            alerta = {
                "ativo": ativo.upper(),
                "tipo": tipo,
                "preco_compra": preco_compra,
                "preco_atual": preco_atual,
                "variacao_pct": round(variacao_pct, 1),
                "valor_investido": valor_investido,
                "valor_atual_estimado": round(valor_investido + lucro_estimado, 2),
                "lucro_estimado": round(lucro_estimado, 2),
                "data_compra": compra.get("data_compra", ""),
            }

            # Sinais para ações
            if variacao_pct >= 30 and preco_atual >= stock.get("max_52sem", 0) * 0.95:
                alerta["acao"] = "CONSIDERAR_VENDA"
                alerta["mensagem"] = (
                    f"📈 {ativo.upper()} subiu {variacao_pct:.0f}% e está "
                    f"perto da máxima de 52 semanas. Considere vender parte."
                )
            elif variacao_pct >= 50:
                alerta["acao"] = "VENDER_PARCIAL"
                alerta["mensagem"] = (
                    f"🚀 {ativo.upper()} subiu {variacao_pct:.0f}%! "
                    f"Pode ser bom vender parte e garantir lucro."
                )
            elif variacao_pct <= -30:
                alerta["acao"] = "ATENÇÃO"
                alerta["mensagem"] = (
                    f"⚠️ {ativo.upper()} caiu {abs(variacao_pct):.0f}%. "
                    f"Avalie se a tese de investimento ainda faz sentido."
                )
            else:
                alerta["acao"] = "MANTER"
                alerta["mensagem"] = None

            alertas.append(alerta)

    return alertas
