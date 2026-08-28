"""
Scheduler de alertas e lembretes automáticos.

Jobs:
1. Verificar alertas de carteira — a cada 1 hora
2. Lembrete de aporte mensal — todo dia às 8h
3. Relatório semanal — todo domingo às 10h
4. Dica financeira diária — todo dia às 9h
5. Oportunidades de mercado — a cada 2 horas (alertas URGENTES)
"""

import asyncio
import datetime
import logging

from telegram.ext import ContextTypes

from services.market_analysis import (
    SINAL_EMOJI,
    SINAL_TEXTO,
    analise_completa_acao,
    analise_completa_crypto,
    get_crypto_price,
    get_stock_price,
    verificar_carteira,
)
from services.portfolio_service import (
    CRYPTO_NOMES,
    get_carteira_ativa,
    get_usuarios_para_alertar,
    update_ultimo_alerta,
)

logger = logging.getLogger(__name__)


# ── Job 1: Verificar alertas de venda/compra ─────────────────


async def job_verificar_alertas(context: ContextTypes.DEFAULT_TYPE):
    """
    Job que roda periodicamente para verificar e enviar alertas.
    Registrado no main.py via job_queue.
    """
    logger.info("Verificando alertas de carteira...")

    try:
        usuarios = await get_usuarios_para_alertar()
        logger.info("Usuários para alertar: %d", len(usuarios))

        for user in usuarios:
            telegram_id = user["telegram_id"]

            try:
                posicoes = await get_carteira_ativa(telegram_id)
                if not posicoes:
                    continue

                # Montar lista de compras para análise
                compras = [
                    {
                        "ativo": p["ativo"],
                        "tipo": p["tipo"],
                        "preco_compra": p["preco_compra"],
                        "valor_investido": p["valor_investido"],
                        "data_compra": p["data_compra"],
                    }
                    for p in posicoes
                ]

                # Verificar cada ativo
                alertas = await verificar_carteira(compras)

                # Filtrar só os que precisam de ação
                alertas_importantes = [
                    a for a in alertas if a.get("mensagem") is not None
                ]

                if alertas_importantes:
                    # Montar mensagem
                    msg = "🔔 **Alerta da sua Carteira**\n\n"

                    for alerta in alertas_importantes:
                        nome = CRYPTO_NOMES.get(
                            alerta["ativo"].lower(), alerta["ativo"]
                        )
                        sinal = "+" if alerta["variacao_pct"] >= 0 else ""

                        msg += (
                            f"{alerta['mensagem']}\n"
                            f"  💰 Investiu: R${alerta['valor_investido']:,.2f}\n"
                            f"  📊 Valor atual: R${alerta['valor_atual_estimado']:,.2f}\n"
                            f"  📈 Resultado: {sinal}{alerta['variacao_pct']:.1f}%\n\n"
                        )

                    msg += (
                        "━━━━━━━━━━━━━━━━━━━\n"
                        "📋 /carteira — Ver posições completas\n"
                        "📊 /analisar [ativo] — Análise detalhada\n"
                        "🔕 /alertas — Desativar alertas"
                    )

                    await context.bot.send_message(
                        chat_id=telegram_id,
                        text=msg,
                        parse_mode="Markdown",
                    )
                    logger.info("Alerta enviado para %s", telegram_id)

                # Atualizar timestamp do último alerta
                await update_ultimo_alerta(telegram_id)

            except Exception as e:
                logger.error(
                    "Erro ao processar alertas do usuário %s: %s",
                    telegram_id,
                    e,
                )

    except Exception as e:
        logger.error("Erro no job de alertas: %s", e)


# ── Job 2: Lembrete de aporte mensal ─────────────────────────


async def job_aporte_diario(context: ContextTypes.DEFAULT_TYPE):
    """
    Roda todo dia às 8h. Verifica se é dia de pagamento de alguém
    e envia sugestões de compra com análise de mercado ao vivo.
    """
    from services.aporte_service import get_usuarios_para_aporte

    dia_hoje = datetime.date.today().day
    logger.info("Verificando aportes para dia %d...", dia_hoje)

    try:
        usuarios = await get_usuarios_para_aporte(dia_hoje)
        logger.info("Usuários com aporte no dia %d: %d", dia_hoje, len(usuarios))

        for plano in usuarios:
            telegram_id = plano["telegram_id"]
            valor = plano["valor_mensal"]
            perfil = plano["perfil_risco"]

            try:
                msg = await _montar_sugestao_aporte(valor, perfil)
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=msg,
                    parse_mode="Markdown",
                )
                logger.info("Lembrete de aporte enviado para %s", telegram_id)
            except Exception as e:
                logger.error(
                    "Erro ao enviar aporte para %s: %s", telegram_id, e
                )

    except Exception as e:
        logger.error("Erro no job de aporte: %s", e)


async def _montar_sugestao_aporte(valor: float, perfil: str) -> str:
    """
    Monta a sugestão de aporte com análise de mercado ao vivo.
    Importa as estratégias do oquefazer (lazy import para evitar circular).
    """
    # Importação lazy para evitar dependência circular
    from handlers.oquefazer import ESTRATEGIAS

    faixa = "pequeno" if valor < 500 else ("medio" if valor <= 5000 else "grande")
    estrategia = ESTRATEGIAS.get(perfil, ESTRATEGIAS["moderado"])
    acoes = estrategia["faixas"][faixa]["acoes"]

    msg = (
        f"💰 **Dia de aporte!** Hora de investir seus R${valor:,.2f}\n\n"
        f"Perfil: {estrategia['emoji']} {estrategia['nome']}\n\n"
        f"📊 **O que comprar hoje (com análise ao vivo):**\n\n"
    )

    # Guias resumidos por tipo
    como_crypto = "📱 _Binance: Comprar → [ativo] → valor → Confirmar_"
    como_acao = "📱 _Nubank: Investir → Ações → [ticker] → Comprar_"
    como_rf = "📱 _Nubank: Investir → Renda Fixa → escolher → Investir_"

    for acao in acoes:
        valor_acao = valor * acao["percentual"] / 100
        nome = acao["ativo"]
        msg += f"**{acao['percentual']}% → R${valor_acao:,.2f} em {nome}**\n"
        msg += f"   _{acao['porque']}_\n"

        # Tentar análise rápida dos ativos principais
        analise_str = await _analise_rapida(nome)
        if analise_str:
            msg += f"   {analise_str}\n"

        # Mini how-to
        nome_lower = nome.lower()
        if any(
            kw in nome_lower
            for kw in ("bitcoin", "btc", "ethereum", "eth", "solana", "cripto")
        ):
            msg += f"   {como_crypto}\n"
        elif any(c.isdigit() for c in nome) and len(nome) >= 4:
            msg += f"   {como_acao}\n"
        elif any(
            kw in nome_lower for kw in ("cdb", "tesouro", "lci", "lca", "renda fixa")
        ):
            msg += f"   {como_rf}\n"

        msg += "\n"

    agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    msg += (
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📡 _Análise em {agora}_\n\n"
        f"Comprou? Registre:\n"
        f"📝 /comprei — Registrar cada compra\n"
        f"📖 /comocomprar — Passo a passo detalhado\n"
        f"📋 /carteira — Ver todas as posições\n\n"
        f"🔑 _Comprar todo mês no mesmo dia (DCA) é a melhor "
        f"estratégia para quem está começando!_"
    )

    return msg


async def _analise_rapida(nome_ativo: str) -> str | None:
    """Tenta analisar rapidamente um ativo e retorna uma linha resumida."""
    import re

    nome_lower = nome_ativo.lower()

    # Mapeamento de keywords para IDs de cripto
    crypto_map = {
        "bitcoin": "bitcoin",
        "btc": "bitcoin",
        "ethereum": "ethereum",
        "eth": "ethereum",
        "solana": "solana",
        "sol": "solana",
    }

    # Tentar como cripto
    for keyword, coin_id in crypto_map.items():
        if keyword in nome_lower:
            try:
                analise = await analise_completa_crypto(coin_id)
                if analise:
                    sinal = analise["sinal"]["sinal"]
                    emoji = SINAL_EMOJI.get(sinal, "🟡")
                    texto = SINAL_TEXTO.get(sinal, "Neutro")
                    preco = analise["preco"]["preco_brl"]
                    return f"{emoji} R${preco:,.2f} — {texto}"
            except Exception:
                pass
            return None

    # Tentar como ação/ETF/FII
    tickers = re.findall(r"\b([A-Z]{4}\d{1,2})\b", nome_ativo)
    if tickers:
        ticker = tickers[0]
        try:
            analise = await analise_completa_acao(ticker)
            if analise:
                sinal = analise["sinal"]["sinal"]
                emoji = SINAL_EMOJI.get(sinal, "🟡")
                texto = SINAL_TEXTO.get(sinal, "Neutro")
                preco = analise["stock"]["preco"]
                return f"{emoji} R${preco:.2f} — {texto}"
        except Exception:
            pass

    return None


# ── Job 3: Relatório semanal ─────────────────────────────────


async def job_relatorio_semanal(context: ContextTypes.DEFAULT_TYPE):
    """
    Roda todo domingo às 10h. Envia um resumo semanal da carteira.
    """
    from services.aporte_service import get_usuarios_com_carteira

    logger.info("Gerando relatórios semanais...")

    try:
        usuarios = await get_usuarios_com_carteira()
        logger.info("Usuários com carteira ativa: %d", len(usuarios))

        for user in usuarios:
            telegram_id = user["telegram_id"]

            try:
                posicoes = await get_carteira_ativa(telegram_id)
                if not posicoes:
                    continue

                msg = "📊 **Relatório Semanal — FinançasIA**\n\n"
                msg += "💼 **Sua Carteira:**\n"

                total_investido = 0
                total_atual = 0

                for pos in posicoes:
                    ativo = pos["ativo"]
                    tipo = pos["tipo"]
                    preco_compra = pos["preco_compra"]
                    valor_investido = pos["valor_investido"]

                    # Buscar preço atual
                    if tipo == "crypto":
                        pd = await get_crypto_price(ativo)
                        preco_atual = pd["preco_brl"] if pd else preco_compra
                    else:
                        sd = await get_stock_price(ativo)
                        preco_atual = sd["preco"] if sd else preco_compra

                    var = ((preco_atual - preco_compra) / preco_compra) * 100
                    valor_atual = valor_investido * (1 + var / 100)

                    total_investido += valor_investido
                    total_atual += valor_atual

                    emoji = "🟢" if var >= 0 else "🔴"
                    sinal = "+" if var >= 0 else ""
                    nome = CRYPTO_NOMES.get(ativo, ativo.upper())

                    msg += (
                        f"{emoji} {nome}: R${valor_investido:,.2f} → "
                        f"R${valor_atual:,.2f} ({sinal}{var:.1f}%)\n"
                    )

                lucro = total_atual - total_investido
                var_total = (
                    (lucro / total_investido * 100) if total_investido else 0
                )
                emoji_total = "🟢" if lucro >= 0 else "🔴"
                sinal_total = "+" if lucro >= 0 else ""

                msg += (
                    f"\n{emoji_total} **Total:** R${total_investido:,.2f} → "
                    f"R${total_atual:,.2f} "
                    f"(**{sinal_total}R${lucro:,.2f}** / "
                    f"{sinal_total}{var_total:.1f}%)\n\n"
                )

                # Sugestões baseadas na carteira
                msg += "💡 **O que eu faria:**\n"

                for pos in posicoes[:3]:  # top 3 posições
                    ativo = pos["ativo"]
                    tipo = pos["tipo"]
                    preco_compra = pos["preco_compra"]

                    if tipo == "crypto":
                        pd = await get_crypto_price(ativo)
                        preco_atual = pd["preco_brl"] if pd else preco_compra
                    else:
                        sd = await get_stock_price(ativo)
                        preco_atual = sd["preco"] if sd else preco_compra

                    var = ((preco_atual - preco_compra) / preco_compra) * 100
                    nome = CRYPTO_NOMES.get(ativo, ativo.upper())

                    if var > 30:
                        msg += f"• {nome}: lucro de {var:.0f}% — considere vender parte\n"
                    elif var < -20:
                        msg += f"• {nome}: queda de {abs(var):.0f}% — avaliar se mantém\n"
                    else:
                        msg += f"• {nome}: {'+' if var >= 0 else ''}{var:.0f}% — manter posição\n"

                msg += (
                    "\n━━━━━━━━━━━━━━━━━━━\n"
                    "📋 /carteira — Posições detalhadas\n"
                    "📊 /analisar [ativo] — Análise completa\n"
                    "💰 /aporte — Configurar aporte mensal"
                )

                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=msg,
                    parse_mode="Markdown",
                )
                logger.info("Relatório semanal enviado para %s", telegram_id)

            except Exception as e:
                logger.error(
                    "Erro no relatório de %s: %s", telegram_id, e
                )

    except Exception as e:
        logger.error("Erro no job de relatório semanal: %s", e)


# ── Job 4: Dica financeira diária ──────────────────────────


async def job_dica_diaria(context: ContextTypes.DEFAULT_TYPE):
    """
    Roda todo dia às 9h BRT (12h UTC). Envia uma dica financeira
    para todos os usuários que têm carteira ativa.
    """
    from handlers.ferramentas import DICAS_FINANCEIRAS
    from services.aporte_service import get_usuarios_com_carteira

    logger.info("Enviando dica financeira diária...")

    try:
        usuarios = await get_usuarios_com_carteira()
        if not usuarios:
            logger.info("Nenhum usuário para enviar dica diária.")
            return

        # Dica baseada no dia do ano (mesma para todos)
        indice = datetime.date.today().timetuple().tm_yday % len(DICAS_FINANCEIRAS)
        dica = DICAS_FINANCEIRAS[indice]

        for user in usuarios:
            telegram_id = user["telegram_id"]
            try:
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=(
                        f"☀️ **Bom dia! Sua dica financeira de hoje:**\n\n"
                        f"{dica}\n\n"
                        "📊 /painel — Seu dashboard\n"
                        "📈 /oquefazer — O que comprar hoje"
                    ),
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.error("Erro ao enviar dica para %s: %s", telegram_id, e)

        logger.info("Dica diária enviada para %d usuários.", len(usuarios))

    except Exception as e:
        logger.error("Erro no job de dica diária: %s", e)


# ── Job 5: Oportunidades urgentes de mercado ─────────────────

# Ativos monitorados pelo scanner de oportunidades
_SCANNER_CRYPTOS = [
    ("bitcoin", "Bitcoin", "BTC"),
    ("ethereum", "Ethereum", "ETH"),
    ("solana", "Solana", "SOL"),
]

_SCANNER_ACOES = [
    ("BOVA11", "BOVA11 (Ibovespa)"),
    ("IVVB11", "IVVB11 (S&P 500)"),
    ("WEGE3", "WEG"),
    ("PETR4", "Petrobras"),
    ("VALE3", "Vale"),
]


async def job_oportunidades_mercado(context: ContextTypes.DEFAULT_TYPE):
    """
    Roda a cada 2 horas. Escaneia criptos e ações monitorados
    em busca de condições extremas de mercado e envia alertas
    URGENTES de compra/venda para usuários inscritos.

    Condições de COMPRA urgente:
    - Queda > 5% em 24h (oportunidade de compra)
    - RSI < 25 (sobrevendido)
    - Fear & Greed < 20 (pânico no mercado)

    Condições de VENDA urgente:
    - Alta > 15% em 24h (possível topo)
    - RSI > 80 (sobrecomprado)
    - Fear & Greed > 80 (euforia/ganância)
    """
    from handlers.alerta_mercado import (
        get_usuarios_alerta_mercado,
        update_ultimo_alerta_mercado,
    )

    logger.info("Escaneando oportunidades de mercado...")

    try:
        usuarios = await get_usuarios_alerta_mercado()
        if not usuarios:
            logger.info("Nenhum usuário com alertas de mercado ativos.")
            return

        # Filtrar usuários que não receberam alerta nas últimas 6h
        agora = datetime.datetime.now()
        usuarios_elegíveis = []
        for u in usuarios:
            ultimo = u.get("ultimo_alerta")
            if ultimo:
                try:
                    ultimo_dt = datetime.datetime.fromisoformat(ultimo)
                    if (agora - ultimo_dt).total_seconds() < 21600:  # 6h
                        continue
                except (ValueError, TypeError):
                    pass
            usuarios_elegíveis.append(u)

        if not usuarios_elegíveis:
            logger.info("Todos os usuários já receberam alerta recente.")
            return

        # Escanear mercado cripto
        alertas_urgentes = []

        # Fear & Greed Index (afeta todas as criptos)
        from services.market_analysis import get_fear_greed_index

        fg = await get_fear_greed_index()
        fg_valor = fg.get("valor", 50) if fg else 50
        fg_class = fg.get("classificacao", "") if fg else ""

        # Alerta global de Fear & Greed extremo
        if fg and fg_valor <= 20:
            alertas_urgentes.append({
                "tipo": "COMPRA",
                "emoji": "🟢🟢",
                "urgencia": "🚨🚨",
                "ativo": "MERCADO CRIPTO",
                "motivo": (
                    f"Índice de Medo em **{fg_valor}** ({fg_class}) — "
                    "PÂNICO no mercado! Historicamente, comprar no "
                    "medo extremo gera os maiores retornos."
                ),
                "acao": "Considere comprar Bitcoin, Ethereum ou Solana",
            })
        elif fg and fg_valor >= 80:
            alertas_urgentes.append({
                "tipo": "VENDA",
                "emoji": "🔴🔴",
                "urgencia": "🚨🚨",
                "ativo": "MERCADO CRIPTO",
                "motivo": (
                    f"Índice de Ganância em **{fg_valor}** ({fg_class}) — "
                    "EUFORIA no mercado! Historicamente, o mercado "
                    "costuma cair forte depois de euforia extrema."
                ),
                "acao": "Considere realizar lucros em criptos",
            })

        # Escanear cada cripto
        for coin_id, nome, sigla in _SCANNER_CRYPTOS:
            try:
                analise = await analise_completa_crypto(coin_id)
                if not analise:
                    continue

                preco = analise["preco"]
                var_24h = preco.get("variacao_24h", 0)
                momentum = analise.get("momentum", {})
                rsi = momentum.get("rsi_14", 50)
                preco_brl = preco["preco_brl"]

                # Queda forte > 5% em 24h
                if var_24h <= -5:
                    alertas_urgentes.append({
                        "tipo": "COMPRA",
                        "emoji": "🟢",
                        "urgencia": "🚨",
                        "ativo": f"{nome} ({sigla})",
                        "motivo": (
                            f"Caiu **{abs(var_24h):.1f}%** nas últimas 24h!\n"
                            f"   Preço: R${preco_brl:,.2f}\n"
                            f"   Quedas bruscas podem ser oportunidade de compra."
                        ),
                        "acao": f"Analisar se é hora de comprar {sigla}",
                    })

                # RSI sobrevendido
                if rsi < 25:
                    alertas_urgentes.append({
                        "tipo": "COMPRA",
                        "emoji": "🟢🟢",
                        "urgencia": "🚨🚨",
                        "ativo": f"{nome} ({sigla})",
                        "motivo": (
                            f"RSI em **{rsi:.0f}** — SOBREVENDIDO!\n"
                            f"   Preço: R${preco_brl:,.2f}\n"
                            f"   Indicador sugere que está 'barato demais' — "
                            f"possível reversão em breve."
                        ),
                        "acao": f"Forte sinal de compra para {sigla}",
                    })

                # Alta forte > 15% em 24h
                if var_24h >= 15:
                    alertas_urgentes.append({
                        "tipo": "VENDA",
                        "emoji": "🔴",
                        "urgencia": "🚨",
                        "ativo": f"{nome} ({sigla})",
                        "motivo": (
                            f"Subiu **{var_24h:.1f}%** nas últimas 24h!\n"
                            f"   Preço: R${preco_brl:,.2f}\n"
                            f"   Altas muito rápidas podem ser seguidas de correção."
                        ),
                        "acao": f"Se tem {sigla}, considere vender parte",
                    })

                # RSI sobrecomprado
                if rsi > 80:
                    alertas_urgentes.append({
                        "tipo": "VENDA",
                        "emoji": "🔴🔴",
                        "urgencia": "🚨🚨",
                        "ativo": f"{nome} ({sigla})",
                        "motivo": (
                            f"RSI em **{rsi:.0f}** — SOBRECOMPRADO!\n"
                            f"   Preço: R${preco_brl:,.2f}\n"
                            f"   Indicador sugere que está 'caro demais' — "
                            f"risco de queda."
                        ),
                        "acao": f"Sinal de venda para {sigla}",
                    })

            except Exception as e:
                logger.warning("Erro ao escanear %s: %s", nome, e)

        # Escanear ações
        for ticker, nome in _SCANNER_ACOES:
            try:
                stock = await get_stock_price(ticker)
                if not stock:
                    continue

                var_dia = stock.get("variacao_dia", 0)
                preco = stock["preco"]
                max_52 = stock.get("max_52sem", preco)
                min_52 = stock.get("min_52sem", preco)

                # Queda forte > 5% no dia
                if var_dia <= -5:
                    alertas_urgentes.append({
                        "tipo": "COMPRA",
                        "emoji": "🟢",
                        "urgencia": "🚨",
                        "ativo": nome,
                        "motivo": (
                            f"Caiu **{abs(var_dia):.1f}%** hoje!\n"
                            f"   Preço: R${preco:.2f}\n"
                            f"   Quedas acentuadas em ações sólidas podem "
                            f"ser ponto de entrada."
                        ),
                        "acao": f"Analisar se é hora de comprar {ticker}",
                    })

                # Perto da mínima de 52 semanas (< 5% acima)
                if min_52 > 0:
                    dist_fundo = ((preco - min_52) / min_52) * 100
                    if dist_fundo < 5:
                        alertas_urgentes.append({
                            "tipo": "COMPRA",
                            "emoji": "🟢",
                            "urgencia": "⚡",
                            "ativo": nome,
                            "motivo": (
                                f"Perto da **mínima de 52 semanas**!\n"
                                f"   Preço: R${preco:.2f} "
                                f"(mín: R${min_52:.2f})\n"
                                f"   Pode ser zona de suporte forte."
                            ),
                            "acao": f"Possível fundo — avaliar {ticker}",
                        })

                # Alta forte > 8% no dia
                if var_dia >= 8:
                    alertas_urgentes.append({
                        "tipo": "VENDA",
                        "emoji": "🔴",
                        "urgencia": "🚨",
                        "ativo": nome,
                        "motivo": (
                            f"Subiu **{var_dia:.1f}%** hoje!\n"
                            f"   Preço: R${preco:.2f}\n"
                            f"   Alta muito rápida — se você tem, pode ser "
                            f"hora de garantir lucro."
                        ),
                        "acao": f"Se tem {ticker}, considere vender parte",
                    })

                # Perto da máxima de 52 semanas (< 3% abaixo)
                if max_52 > 0:
                    dist_topo = ((max_52 - preco) / max_52) * 100
                    if dist_topo < 3 and var_dia > 2:
                        alertas_urgentes.append({
                            "tipo": "VENDA",
                            "emoji": "🔴",
                            "urgencia": "⚡",
                            "ativo": nome,
                            "motivo": (
                                f"Perto da **máxima de 52 semanas**!\n"
                                f"   Preço: R${preco:.2f} "
                                f"(máx: R${max_52:.2f})\n"
                                f"   Pode ser zona de resistência."
                            ),
                            "acao": f"Se tem lucro em {ticker}, considere vender",
                        })

            except Exception as e:
                logger.warning("Erro ao escanear %s: %s", ticker, e)

        # Se não há alertas urgentes, sair
        if not alertas_urgentes:
            logger.info("Nenhuma oportunidade urgente detectada.")
            return

        logger.info(
            "Oportunidades detectadas: %d — enviando para %d usuários",
            len(alertas_urgentes),
            len(usuarios_elegíveis),
        )

        # Agrupar alertas por tipo
        compras = [a for a in alertas_urgentes if a["tipo"] == "COMPRA"]
        vendas = [a for a in alertas_urgentes if a["tipo"] == "VENDA"]

        # Montar mensagem
        msg = "🚨 **ALERTA URGENTE DE MERCADO** 🚨\n\n"

        agora_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        msg += f"📡 _Análise em {agora_str}_\n\n"

        if compras:
            msg += "🟢 **OPORTUNIDADES DE COMPRA:**\n\n"
            for a in compras:
                msg += (
                    f"{a['urgencia']} **{a['ativo']}**\n"
                    f"   {a['motivo']}\n"
                    f"   👉 _{a['acao']}_\n\n"
                )

        if vendas:
            msg += "🔴 **SINAIS DE VENDA:**\n\n"
            for a in vendas:
                msg += (
                    f"{a['urgencia']} **{a['ativo']}**\n"
                    f"   {a['motivo']}\n"
                    f"   👉 _{a['acao']}_\n\n"
                )

        msg += (
            "━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ _Estes são sinais técnicos, não garantia de lucro. "
            "Faça sua própria análise!_\n\n"
            "📈 /analisar [ativo] — Análise detalhada\n"
            "📋 /oquefazer — Plano completo do que comprar\n"
            "📖 /comocomprar — Passo a passo para comprar\n"
            "🔕 /alertamercado — Desativar alertas"
        )

        # Limitar tamanho da mensagem
        if len(msg) > 4000:
            msg = msg[:3950] + "\n\n_...mais sinais disponíveis via /analisar_"

        # Enviar para todos os usuários elegíveis
        for u in usuarios_elegíveis:
            telegram_id = u["telegram_id"]
            try:
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=msg,
                    parse_mode="Markdown",
                )
                await update_ultimo_alerta_mercado(telegram_id)
                logger.info("Alerta de mercado enviado para %s", telegram_id)
            except Exception as e:
                logger.error(
                    "Erro ao enviar alerta de mercado para %s: %s",
                    telegram_id, e,
                )

    except Exception as e:
        logger.error("Erro no job de oportunidades de mercado: %s", e)


# ── Job 6: Verificar alertas de preço-alvo ──────────────────


async def job_verificar_alertas_preco(context: ContextTypes.DEFAULT_TYPE):
    """
    Roda a cada 1 hora. Verifica todos os alertas de preço-alvo ativos,
    compara com o preço atual e envia notificação quando o alvo é atingido.
    """
    from handlers.alerta_preco import (
        get_todos_alertas_preco_ativos,
        marcar_alerta_notificado,
    )

    logger.info("Verificando alertas de preço-alvo...")

    try:
        alertas = await get_todos_alertas_preco_ativos()
        if not alertas:
            logger.info("Nenhum alerta de preço ativo.")
            return

        logger.info("Alertas de preço ativos: %d", len(alertas))

        for alerta in alertas:
            try:
                ativo = alerta["ativo"]
                tipo = alerta["tipo"]
                direcao = alerta["direcao"]
                preco_alvo = alerta["preco_alvo"]
                telegram_id = alerta["telegram_id"]

                # Buscar preço atual
                preco_atual = None
                if tipo == "crypto":
                    pd = await get_crypto_price(ativo)
                    if pd:
                        preco_atual = pd["preco_brl"]
                else:
                    sd = await get_stock_price(ativo)
                    if sd:
                        preco_atual = sd["preco"]

                if preco_atual is None:
                    continue

                # Verificar se o alvo foi atingido
                atingido = False
                if direcao == "acima" and preco_atual >= preco_alvo:
                    atingido = True
                elif direcao == "abaixo" and preco_atual <= preco_alvo:
                    atingido = True

                if atingido:
                    nome = CRYPTO_NOMES.get(ativo, ativo.upper())
                    emoji_dir = "📈" if direcao == "acima" else "📉"
                    texto_dir = "subiu" if direcao == "acima" else "caiu"

                    msg = (
                        f"🎯🔔 **ALERTA DE PREÇO ATINGIDO!**\n\n"
                        f"📌 **{nome}** {texto_dir} até o seu alvo!\n\n"
                        f"{emoji_dir} Preço atual: **R${preco_atual:,.2f}**\n"
                        f"🎯 Seu alvo: R${preco_alvo:,.2f}\n\n"
                    )

                    if direcao == "acima":
                        msg += (
                            "💡 _O ativo atingiu o preço que você esperava. "
                            "Se era um alvo de venda, considere realizar lucro!_\n\n"
                        )
                    else:
                        msg += (
                            "💡 _O ativo caiu até o preço que você esperava. "
                            "Se era um alvo de compra, pode ser hora de entrar!_\n\n"
                        )

                    msg += (
                        "━━━━━━━━━━━━━━━━━━━\n"
                        "📈 /analisar — Análise completa\n"
                        "📋 /alvos — Seus alertas ativos\n"
                        "🎯 /alvo — Criar novo alerta"
                    )

                    await context.bot.send_message(
                        chat_id=telegram_id,
                        text=msg,
                        parse_mode="Markdown",
                    )
                    await marcar_alerta_notificado(alerta["id"])
                    logger.info(
                        "Alerta #%d notificado — %s atingiu R$%.2f para user %s",
                        alerta["id"], ativo, preco_alvo, telegram_id,
                    )

            except Exception as e:
                logger.error(
                    "Erro ao verificar alerta #%s: %s",
                    alerta.get("id"), e,
                )

    except Exception as e:
        logger.error("Erro no job de alertas de preço: %s", e)


# ── Job 7: Resumo matinal ──────────────────────────────────


async def job_resumo_matinal(context: ContextTypes.DEFAULT_TYPE):
    """
    Roda todo dia às 7h BRT (10h UTC).
    Envia o resumo matinal personalizado para todos os usuários inscritos.
    """
    from handlers.resumo_matinal import (
        get_usuarios_resumo_matinal,
        montar_resumo_matinal,
    )

    logger.info("Enviando resumos matinais...")

    try:
        usuarios = await get_usuarios_resumo_matinal()
        if not usuarios:
            logger.info("Nenhum usuário com resumo matinal ativo.")
            return

        logger.info("Usuários com resumo matinal: %d", len(usuarios))
        enviados = 0

        for user in usuarios:
            telegram_id = user["telegram_id"]
            try:
                msg = await montar_resumo_matinal(telegram_id)

                # Dividir se necessário (resumo pode ser longo)
                if len(msg) > 4000:
                    partes = []
                    remaining = msg
                    while remaining:
                        if len(remaining) <= 4000:
                            partes.append(remaining)
                            break
                        corte = remaining.rfind("\n", 0, 4000)
                        if corte == -1:
                            corte = 4000
                        partes.append(remaining[:corte])
                        remaining = remaining[corte:].lstrip("\n")
                    for parte in partes:
                        await context.bot.send_message(
                            chat_id=telegram_id,
                            text=parte,
                            parse_mode="Markdown",
                        )
                else:
                    await context.bot.send_message(
                        chat_id=telegram_id,
                        text=msg,
                        parse_mode="Markdown",
                    )

                enviados += 1
                logger.info("Resumo matinal enviado para %s", telegram_id)

                # Pequena pausa entre envios para evitar rate limit
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(
                    "Erro ao enviar resumo matinal para %s: %s",
                    telegram_id, e,
                )

        logger.info(
            "Resumos matinais enviados: %d/%d", enviados, len(usuarios)
        )

    except Exception as e:
        logger.error("Erro no job de resumo matinal: %s", e)


# ── Registrar todos os jobs ──────────────────────────────────


def registrar_jobs(app):
    """
    Registra os jobs periódicos no bot.
    Chamado pelo main.py após criar a Application.
    """
    job_queue = app.job_queue

    # 1. Verificar alertas de carteira — a cada 1 hora
    job_queue.run_repeating(
        job_verificar_alertas,
        interval=3600,
        first=60,
        name="verificar_alertas",
    )

    # 2. Lembrete de aporte — todo dia às 8h (horário de Brasília ~ 11h UTC)
    job_queue.run_daily(
        job_aporte_diario,
        time=datetime.time(hour=11, minute=0, second=0),
        name="aporte_diario",
    )

    # 3. Relatório semanal — todo domingo às 10h (13h UTC)
    job_queue.run_daily(
        job_relatorio_semanal,
        time=datetime.time(hour=13, minute=0, second=0),
        days=(6,),  # 6 = domingo
        name="relatorio_semanal",
    )

    # 4. Dica financeira diária — todo dia às 9h BRT (12h UTC)
    job_queue.run_daily(
        job_dica_diaria,
        time=datetime.time(hour=12, minute=0, second=0),
        name="dica_diaria",
    )

    # 5. Oportunidades urgentes de mercado — a cada 2 horas
    job_queue.run_repeating(
        job_oportunidades_mercado,
        interval=7200,
        first=300,  # 5 min após iniciar (dá tempo de estabilizar)
        name="oportunidades_mercado",
    )

    # 6. Verificar alertas de preço-alvo — a cada 1 hora
    job_queue.run_repeating(
        job_verificar_alertas_preco,
        interval=3600,
        first=120,
        name="alertas_preco",
    )

    # 7. Resumo matinal — todo dia às 7h BRT (10h UTC)
    job_queue.run_daily(
        job_resumo_matinal,
        time=datetime.time(hour=10, minute=0, second=0),
        name="resumo_matinal",
    )

    logger.info(
        "Jobs registrados: alertas (1h), aporte diário (8h BRT), "
        "relatório semanal (dom 10h BRT), dica diária (9h BRT), "
        "oportunidades mercado (2h), alertas preço (1h), "
        "resumo matinal (7h BRT)"
    )
