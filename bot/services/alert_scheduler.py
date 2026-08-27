"""
Scheduler de alertas e lembretes automáticos.

Jobs:
1. Verificar alertas de carteira — a cada 1 hora
2. Lembrete de aporte mensal — todo dia às 8h
3. Relatório semanal — todo domingo às 10h
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

    logger.info(
        "Jobs registrados: alertas (1h), aporte diário (8h BRT), "
        "relatório semanal (dom 10h BRT)"
    )
