"""
Handler do resumo matinal personalizado.

/bomdia — Ativa/desativa o resumo matinal (todo dia às 7h BRT).

O resumo inclui:
- Status da carteira (se tiver)
- Visão geral do mercado (BTC, IBOV, Fear & Greed)
- Melhor oportunidade do dia
- Frase motivacional
"""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from database.db import get_db

logger = logging.getLogger(__name__)


# ── Frases motivacionais ─────────────────────────────────────

FRASES_MOTIVACIONAIS = [
    "💪 _\"O melhor momento para plantar uma árvore foi 20 anos atrás. O segundo melhor é agora.\"_",
    "📈 _\"Não é sobre timing do mercado, é sobre tempo NO mercado.\"_",
    "🎯 _\"Quem poupa sempre tem, quem não poupa corre atrás.\"_",
    "💰 _\"Riqueza não é quanto você ganha, mas quanto você guarda.\"_",
    "🧠 _\"Investir não é sobre ficar rico rápido, é sobre não ficar pobre devagar.\"_",
    "🌱 _\"Cada real investido hoje é um soldado trabalhando por você amanhã.\"_",
    "⏰ _\"O tempo no mercado bate o timing do mercado. Comece hoje.\"_",
    "🏆 _\"Disciplina é escolher entre o que você quer agora e o que mais quer na vida.\"_",
    "📊 _\"Diversifique. Não coloque todos os ovos na mesma cesta.\"_",
    "🔥 _\"Juros compostos são a oitava maravilha do mundo.\"_ — Einstein",
    "💎 _\"Compre ao som de canhões, venda ao som de trombetas.\"_ — Buffett",
    "🚀 _\"O mercado é um mecanismo de transferir dinheiro dos impacientes para os pacientes.\"_",
    "🌟 _\"Invista em conhecimento. É o investimento que paga os maiores juros.\"_",
    "🎓 _\"O risco vem de não saber o que você está fazendo.\"_ — Buffett",
    "💡 _\"Não espere comprar na mínima e vender na máxima. Ninguém faz isso.\"_",
]


# ── Serviço de configuração ──────────────────────────────────


async def get_resumo_config(telegram_id: int) -> dict | None:
    """Busca configuração de resumo matinal do usuário."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM resumo_matinal_config WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def toggle_resumo_matinal(telegram_id: int) -> bool:
    """Ativa/desativa resumo matinal. Retorna o novo estado."""
    config = await get_resumo_config(telegram_id)
    db = await get_db()
    try:
        if config:
            novo = 0 if config["ativo"] else 1
            await db.execute(
                "UPDATE resumo_matinal_config SET ativo = ? "
                "WHERE telegram_id = ?",
                (novo, telegram_id),
            )
        else:
            novo = 1
            await db.execute(
                "INSERT INTO resumo_matinal_config (telegram_id, ativo) "
                "VALUES (?, 1)",
                (telegram_id,),
            )
        await db.commit()
        return bool(novo)
    finally:
        await db.close()


async def get_usuarios_resumo_matinal() -> list[dict]:
    """Retorna todos os usuários com resumo matinal ativo."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT telegram_id FROM resumo_matinal_config WHERE ativo = 1"
        )
        return [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()


# ── Handlers ─────────────────────────────────────────────────


async def bomdia_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra painel de controle do resumo matinal."""
    telegram_id = update.effective_user.id
    config = await get_resumo_config(telegram_id)
    ativo = config["ativo"] if config else False

    status = "🟢 **ATIVADO**" if ativo else "🔴 **DESATIVADO**"

    await update.message.reply_text(
        "☀️ **Resumo Matinal Personalizado**\n\n"
        f"Status: {status}\n\n"
        "Todo dia às **7h da manhã** eu te mando:\n\n"
        "📊 Status da sua carteira (se tiver)\n"
        "🌍 Visão geral do mercado (BTC, IBOV)\n"
        "😰 Índice de Medo/Ganância\n"
        "⭐ Melhor oportunidade do dia\n"
        "💡 Frase motivacional\n\n"
        "É como um briefing financeiro de 30 segundos! ☕",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔴 Desativar" if ativo else "🟢 Ativar resumo!",
                        callback_data="resumo_matinal_toggle",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "👀 Ver exemplo agora",
                        callback_data="resumo_matinal_preview",
                    )
                ],
            ]
        ),
    )


async def resumo_matinal_toggle(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Toggle do resumo matinal."""
    query = update.callback_query
    await query.answer()

    telegram_id = query.from_user.id
    novo_estado = await toggle_resumo_matinal(telegram_id)

    if novo_estado:
        await query.edit_message_text(
            "☀️ **Resumo matinal ATIVADO!**\n\n"
            "A partir de amanhã, todo dia às 7h você recebe\n"
            "seu briefing financeiro personalizado! ☕\n\n"
            "_Use /bomdia para desativar._",
            parse_mode="Markdown",
        )
    else:
        await query.edit_message_text(
            "🔴 **Resumo matinal desativado.**\n\n"
            "_Use /bomdia para reativar._",
            parse_mode="Markdown",
        )


async def resumo_matinal_preview(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Mostra preview do resumo matinal."""
    query = update.callback_query
    await query.answer("Gerando preview...")

    telegram_id = query.from_user.id

    # Gerar e enviar o resumo como preview
    msg = await montar_resumo_matinal(telegram_id)

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=msg,
        parse_mode="Markdown",
    )


# ── Montagem do resumo ──────────────────────────────────────


async def montar_resumo_matinal(telegram_id: int) -> str:
    """Monta o resumo matinal completo para um usuário."""
    import datetime as dt

    from services.market_analysis import (
        SINAL_EMOJI,
        SINAL_TEXTO,
        analise_completa_acao,
        analise_completa_crypto,
        get_crypto_price,
        get_fear_greed_index,
        get_stock_price,
    )
    from services.portfolio_service import CRYPTO_NOMES, get_carteira_ativa

    agora = dt.datetime.now()
    dia_semana = [
        "segunda", "terça", "quarta", "quinta",
        "sexta", "sábado", "domingo",
    ][agora.weekday()]

    msg = (
        f"☀️ **Bom dia! Seu briefing financeiro**\n"
        f"📅 _{dia_semana}, {agora.strftime('%d/%m/%Y')}_\n\n"
    )

    # ── Carteira do usuário ──
    posicoes = await get_carteira_ativa(telegram_id)
    if posicoes:
        total_investido = 0
        total_atual = 0

        for pos in posicoes:
            tipo = pos["tipo"]
            ativo = pos["ativo"]
            preco_compra = pos["preco_compra"]
            valor_investido = pos["valor_investido"]

            preco_atual = preco_compra
            if tipo == "crypto":
                pd = await get_crypto_price(ativo)
                if pd:
                    preco_atual = pd["preco_brl"]
            else:
                sd = await get_stock_price(ativo)
                if sd:
                    preco_atual = sd["preco"]

            var = ((preco_atual - preco_compra) / preco_compra) * 100
            valor_atual = valor_investido * (1 + var / 100)

            total_investido += valor_investido
            total_atual += valor_atual

        lucro = total_atual - total_investido
        var_total = (lucro / total_investido * 100) if total_investido else 0
        emoji_p = "🟢" if lucro >= 0 else "🔴"
        sinal_p = "+" if lucro >= 0 else ""

        msg += (
            f"💼 **Sua carteira:**\n"
            f"   {emoji_p} R${total_atual:,.2f} "
            f"({sinal_p}R${lucro:,.2f} / {sinal_p}{var_total:.1f}%)\n"
            f"   📊 {len(posicoes)} ativo(s) monitorado(s)\n\n"
        )

    # ── Mercado ──
    msg += "🌍 **Mercado agora:**\n"

    # Bitcoin
    btc = await get_crypto_price("bitcoin")
    if btc:
        var_btc = btc.get("variacao_24h", 0)
        emoji_btc = "🟢" if var_btc >= 0 else "🔴"
        sinal_btc = "+" if var_btc >= 0 else ""
        msg += (
            f"   🪙 Bitcoin: R${btc['preco_brl']:,.0f} "
            f"({emoji_btc} {sinal_btc}{var_btc:.1f}%)\n"
        )

    # Ibovespa (BOVA11 como proxy)
    ibov = await get_stock_price("BOVA11")
    if ibov:
        var_ibov = ibov.get("variacao_dia", 0)
        emoji_ibov = "🟢" if var_ibov >= 0 else "🔴"
        sinal_ibov = "+" if var_ibov >= 0 else ""
        msg += (
            f"   📈 Ibovespa: R${ibov['preco']:.2f} "
            f"({emoji_ibov} {sinal_ibov}{var_ibov:.1f}%)\n"
        )

    # Fear & Greed
    fg = await get_fear_greed_index()
    if fg:
        fg_valor = fg["valor"]
        fg_class = fg["classificacao"]
        if fg_valor <= 25:
            fg_emoji = "😰"
            fg_dica = "Medo extremo — historicamente bom para comprar!"
        elif fg_valor <= 45:
            fg_emoji = "😟"
            fg_dica = "Mercado com medo — fique atento a oportunidades"
        elif fg_valor <= 55:
            fg_emoji = "😐"
            fg_dica = "Mercado neutro — sem pressão"
        elif fg_valor <= 75:
            fg_emoji = "😊"
            fg_dica = "Otimismo moderado — bom cenário"
        else:
            fg_emoji = "🤑"
            fg_dica = "Ganância extrema — cautela!"
        msg += (
            f"   {fg_emoji} Sentimento: {fg_valor}/100 ({fg_class})\n"
            f"   💡 _{fg_dica}_\n"
        )

    msg += "\n"

    # ── Melhor oportunidade ──
    # Análise rápida dos top 3 criptos
    best = None
    best_score = -999

    for coin_id, nome in [
        ("bitcoin", "Bitcoin"),
        ("ethereum", "Ethereum"),
        ("solana", "Solana"),
    ]:
        try:
            analise = await analise_completa_crypto(coin_id)
            if analise and analise["sinal"]["score"] > best_score:
                best_score = analise["sinal"]["score"]
                best = {
                    "nome": nome,
                    "preco": analise["preco"]["preco_brl"],
                    "score": analise["sinal"]["score"],
                    "sinal": analise["sinal"]["sinal"],
                }
        except Exception:
            pass

    # Também checar top ações
    for ticker, nome in [("PETR4", "Petrobras"), ("VALE3", "Vale")]:
        try:
            analise = await analise_completa_acao(ticker)
            if analise and analise["sinal"]["score"] > best_score:
                best_score = analise["sinal"]["score"]
                best = {
                    "nome": nome,
                    "preco": analise["stock"]["preco"],
                    "score": analise["sinal"]["score"],
                    "sinal": analise["sinal"]["sinal"],
                }
        except Exception:
            pass

    if best:
        emoji_best = SINAL_EMOJI.get(best["sinal"], "🟡")
        texto_best = SINAL_TEXTO.get(best["sinal"], "Neutro")
        msg += (
            f"⭐ **Destaque do dia:**\n"
            f"   {emoji_best} **{best['nome']}** — "
            f"R${best['preco']:,.2f}\n"
            f"   {texto_best} (score {best['score']:+d})\n\n"
        )

    # ── Frase motivacional ──
    indice = agora.timetuple().tm_yday % len(FRASES_MOTIVACIONAIS)
    frase = FRASES_MOTIVACIONAIS[indice]
    msg += f"{frase}\n\n"

    # ── Links rápidos ──
    msg += (
        "━━━━━━━━━━━━━━━━━━━\n"
        "📡 /radar — Todas as oportunidades\n"
        "📈 /oquefazer — O que comprar hoje\n"
        "📋 /carteira — Suas posições\n"
        "📊 /painel — Dashboard completo"
    )

    return msg


def get_resumo_matinal_handlers() -> list:
    """Retorna os handlers do resumo matinal."""
    return [
        CommandHandler("bomdia", bomdia_cmd),
        CommandHandler("briefing", bomdia_cmd),
        CallbackQueryHandler(
            resumo_matinal_toggle, pattern=r"^resumo_matinal_toggle$"
        ),
        CallbackQueryHandler(
            resumo_matinal_preview, pattern=r"^resumo_matinal_preview$"
        ),
    ]
