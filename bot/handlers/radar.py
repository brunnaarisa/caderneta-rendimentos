"""
Handler do Radar de Oportunidades — escaneia ativos e rankeia os melhores.

/radar — Escaneia todos os ativos monitorados e mostra um ranking
         das melhores oportunidades de compra e sinais de venda.
"""

import asyncio
import datetime
import logging

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from services.market_analysis import (
    SINAL_EMOJI,
    SINAL_TEXTO,
    analise_completa_acao,
    analise_completa_crypto,
    get_fear_greed_index,
)

logger = logging.getLogger(__name__)

# Ativos monitorados
_CRYPTOS = [
    ("bitcoin", "Bitcoin", "BTC"),
    ("ethereum", "Ethereum", "ETH"),
    ("solana", "Solana", "SOL"),
]

_ACOES = [
    ("BOVA11", "BOVA11 (Ibovespa)", "ETF"),
    ("IVVB11", "IVVB11 (S&P 500)", "ETF"),
    ("WEGE3", "WEG", "Ação"),
    ("PETR4", "Petrobras", "Ação"),
    ("VALE3", "Vale", "Ação"),
    ("ITUB4", "Itaú", "Ação"),
    ("BBDC4", "Bradesco", "Ação"),
    ("ABEV3", "Ambev", "Ação"),
    ("MGLU3", "Magazine Luiza", "Ação"),
    ("RENT3", "Localiza", "Ação"),
]


async def radar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Escaneia todos os ativos e mostra ranking de oportunidades."""
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    await update.message.reply_text(
        "📡 **Radar de Oportunidades**\n\n"
        "🔍 Escaneando 13 ativos ao vivo...\n"
        "_(cripto + ações da B3 — pode levar alguns segundos)_",
        parse_mode="Markdown",
    )

    # Buscar Fear & Greed
    fg = await get_fear_greed_index()

    # Analisar tudo em paralelo
    tasks = []
    for coin_id, nome, sigla in _CRYPTOS:
        tasks.append(_analisar_crypto(coin_id, nome, sigla))
    for ticker, nome, cat in _ACOES:
        tasks.append(_analisar_acao(ticker, nome, cat))

    resultados = await asyncio.gather(*tasks)
    resultados = [r for r in resultados if r]

    if not resultados:
        await update.message.reply_text(
            "❌ Não consegui buscar dados do mercado agora. "
            "Tente novamente em alguns minutos.",
            parse_mode="Markdown",
        )
        return

    # Separar compras e vendas
    compras = sorted(
        [r for r in resultados if r["score"] >= 10],
        key=lambda x: x["score"],
        reverse=True,
    )
    vendas = sorted(
        [r for r in resultados if r["score"] <= -10],
        key=lambda x: x["score"],
    )
    neutros = [
        r for r in resultados if -10 < r["score"] < 10
    ]

    agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    msg = f"📡 **RADAR DE OPORTUNIDADES**\n"
    msg += f"📊 _Análise em {agora}_\n\n"

    # Fear & Greed
    if fg:
        fg_valor = fg["valor"]
        fg_class = fg["classificacao"]
        if fg_valor <= 25:
            fg_emoji = "😰"
        elif fg_valor <= 45:
            fg_emoji = "😟"
        elif fg_valor <= 55:
            fg_emoji = "😐"
        elif fg_valor <= 75:
            fg_emoji = "😊"
        else:
            fg_emoji = "🤑"
        msg += (
            f"{fg_emoji} **Sentimento do mercado:** "
            f"{fg_valor}/100 ({fg_class})\n\n"
        )

    # Top oportunidades de compra
    if compras:
        msg += "🟢 **MELHORES OPORTUNIDADES DE COMPRA:**\n\n"
        for i, a in enumerate(compras[:5], 1):
            medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i - 1]
            msg += (
                f"{medal} **{a['nome']}** ({a['categoria']})\n"
                f"   💰 R${a['preco']:,.2f} | "
                f"Score: {a['emoji']} **{a['score']:+d}**\n"
                f"   📊 {a['sinal_texto']}\n"
            )
            # Motivo principal
            if a.get("motivos"):
                msg += f"   💡 _{a['motivos'][0]}_\n"
            msg += "\n"
    else:
        msg += "🟡 Nenhuma oportunidade forte de compra agora.\n\n"

    # Sinais de venda
    if vendas:
        msg += "🔴 **SINAIS DE VENDA / CAUTELA:**\n\n"
        for a in vendas[:3]:
            msg += (
                f"⚠️ **{a['nome']}** ({a['categoria']})\n"
                f"   💰 R${a['preco']:,.2f} | "
                f"Score: {a['emoji']} **{a['score']:+d}**\n"
                f"   📊 {a['sinal_texto']}\n"
            )
            if a.get("motivos"):
                msg += f"   💡 _{a['motivos'][0]}_\n"
            msg += "\n"

    # Neutros (resumo)
    if neutros:
        nomes_neutros = ", ".join(n["nome"] for n in neutros[:5])
        msg += f"🟡 **Neutros:** {nomes_neutros}\n\n"

    # Resumo rápido
    total = len(resultados)
    n_compra = len(compras)
    n_venda = len(vendas)
    n_neutro = len(neutros)
    msg += (
        "━━━━━━━━━━━━━━━━━━━\n"
        f"📊 **Resumo:** {total} ativos analisados\n"
        f"🟢 {n_compra} para comprar | "
        f"🔴 {n_venda} para vender | "
        f"🟡 {n_neutro} neutros\n\n"
    )

    # Melhor ação
    if compras:
        best = compras[0]
        msg += (
            f"⭐ **Melhor oportunidade agora:** "
            f"{best['nome']} (score {best['score']:+d})\n\n"
        )

    msg += (
        "📈 /analisar [ativo] — Análise detalhada\n"
        "📋 /oquefazer — Plano completo do que comprar\n"
        "📖 /comocomprar — Passo a passo para comprar\n"
        "🎯 /alvo [ativo] [preço] — Alerta de preço"
    )

    # Enviar (dividir se necessário)
    if len(msg) > 4000:
        partes = []
        while msg:
            if len(msg) <= 4000:
                partes.append(msg)
                break
            corte = msg.rfind("\n", 0, 4000)
            if corte == -1:
                corte = 4000
            partes.append(msg[:corte])
            msg = msg[corte:].lstrip("\n")
        for parte in partes:
            await update.message.reply_text(
                parte, parse_mode="Markdown"
            )
    else:
        await update.message.reply_text(msg, parse_mode="Markdown")

    # XP por usar o radar
    from services.gamification_service import add_xp, registrar_acesso_diario

    await registrar_acesso_diario(update.effective_user.id)
    await add_xp(update.effective_user.id, "ver_dashboard")


# ── Análise individual ───────────────────────────────────────


async def _analisar_crypto(
    coin_id: str, nome: str, sigla: str
) -> dict | None:
    """Analisa uma crypto para o radar."""
    try:
        analise = await analise_completa_crypto(coin_id)
        if not analise:
            return None
        sinal = analise["sinal"]
        return {
            "nome": f"{nome} ({sigla})",
            "categoria": "Cripto",
            "preco": analise["preco"]["preco_brl"],
            "score": sinal["score"],
            "sinal_texto": SINAL_TEXTO.get(sinal["sinal"], "Neutro"),
            "emoji": SINAL_EMOJI.get(sinal["sinal"], "🟡"),
            "motivos": sinal.get("motivos", []),
        }
    except Exception as e:
        logger.warning("Erro ao analisar %s no radar: %s", nome, e)
        return None


async def _analisar_acao(
    ticker: str, nome: str, categoria: str
) -> dict | None:
    """Analisa uma ação para o radar."""
    try:
        analise = await analise_completa_acao(ticker)
        if not analise:
            return None
        sinal = analise["sinal"]
        return {
            "nome": nome,
            "categoria": categoria,
            "preco": analise["stock"]["preco"],
            "score": sinal["score"],
            "sinal_texto": SINAL_TEXTO.get(sinal["sinal"], "Neutro"),
            "emoji": SINAL_EMOJI.get(sinal["sinal"], "🟡"),
            "motivos": sinal.get("motivos", []),
        }
    except Exception as e:
        logger.warning("Erro ao analisar %s no radar: %s", ticker, e)
        return None


def get_radar_handlers() -> list:
    """Retorna os handlers do radar."""
    return [
        CommandHandler("radar", radar_cmd),
        CommandHandler("oportunidades", radar_cmd),
        CommandHandler("scanner", radar_cmd),
    ]
