"""
Handlers da carteira — registrar compras, ver posições,
análise de mercado e alertas de venda.
"""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from services.market_analysis import (
    SINAL_EMOJI,
    SINAL_TEXTO,
    analise_completa_acao,
    analise_completa_crypto,
    get_crypto_price,
    get_stock_price,
)
from services.portfolio_service import (
    CRYPTO_NOMES,
    get_carteira_ativa,
    normalizar_ativo,
    registrar_compra,
    toggle_alertas,
)
from services.user_service import get_or_create_user

logger = logging.getLogger(__name__)

# Estados
COMPRA_ATIVO, COMPRA_VALOR, COMPRA_PRECO = range(3)


# ── /analisar — Análise de mercado antes de comprar ────────────


async def analisar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Analisa um ativo antes de comprar."""
    args = context.args
    if not args:
        await update.message.reply_text(
            "📊 **Análise de Mercado**\n\n"
            "Use assim:\n"
            "/analisar btc — Analisar Bitcoin\n"
            "/analisar eth — Analisar Ethereum\n"
            "/analisar PETR4 — Analisar Petrobras\n"
            "/analisar HGLG11 — Analisar FII HGLG11\n",
            parse_mode="Markdown",
        )
        return

    nome = args[0]
    ativo_id, tipo = normalizar_ativo(nome)

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    if tipo == "crypto":
        analise = await analise_completa_crypto(ativo_id)
        if not analise:
            await update.message.reply_text(
                f"❌ Não encontrei dados para '{nome}'. "
                "Tente: btc, eth, sol, bnb, ada, xrp, doge"
            )
            return

        preco = analise["preco"]
        sinal = analise["sinal"]
        momentum = analise["momentum"]
        suporte = analise["suporte"]
        medias = analise["medias"]
        fg = analise.get("fear_greed")

        nome_bonito = CRYPTO_NOMES.get(ativo_id, ativo_id.upper())
        emoji_sinal = SINAL_EMOJI.get(sinal["sinal"], "🟡")
        texto_sinal = SINAL_TEXTO.get(sinal["sinal"], "Neutro")

        msg = (
            f"📊 **Análise: {nome_bonito}**\n\n"
            f"💰 Preço atual: **R${preco['preco_brl']:,.2f}**\n"
            f"📈 Variação 24h: {preco['variacao_24h']:+.1f}%\n\n"
        )

        # Tendência
        msg += "**📉 Tendência:**\n"
        if momentum:
            msg += f"  7 dias: {momentum['var_7d']:+.1f}%\n"
            msg += f"  30 dias: {momentum['var_30d']:+.1f}%\n"
            msg += f"  90 dias: {momentum['var_90d']:+.1f}%\n"
            msg += f"  RSI(14): {momentum['rsi_14']:.0f}"
            if momentum["rsi_14"] > 70:
                msg += " ⚠️ sobrecomprado"
            elif momentum["rsi_14"] < 30:
                msg += " 🟢 sobrevendido"
            msg += "\n"

        # Suporte/resistência
        if suporte:
            msg += (
                f"\n**📐 Suporte e Resistência (30d):**\n"
                f"  Máxima: R${suporte['max_30d']:,.2f}\n"
                f"  Mínima: R${suporte['min_30d']:,.2f}\n"
                f"  Distância do topo: {suporte['dist_topo_30d_pct']:.1f}%\n"
            )

        # Fear & Greed
        if fg:
            msg += f"\n😰 Fear & Greed: **{fg['valor']}** ({fg['classificacao']})\n"

        # Sinal final
        msg += (
            f"\n━━━━━━━━━━━━━━━━━━━\n"
            f"{emoji_sinal} **SINAL: {texto_sinal}**\n"
            f"Score: {sinal['score']:+d}/100\n\n"
            "**Motivos:**\n"
        )
        for motivo in sinal["motivos"]:
            msg += f"  {motivo}\n"

        # Recomendação prática
        msg += "\n━━━━━━━━━━━━━━━━━━━\n"
        if sinal["sinal"] in ("COMPRA_FORTE", "COMPRA"):
            msg += (
                f"💡 **Se eu fosse comprar {nome_bonito} hoje, eu compraria.**\n"
                f"Os indicadores estão favoráveis. Lembre-se: compre aos poucos "
                f"(um pouco por semana/mês), não tudo de uma vez.\n"
            )
        elif sinal["sinal"] in ("VENDA_FORTE", "VENDA"):
            msg += (
                f"⚠️ **Eu NÃO compraria {nome_bonito} agora.**\n"
                f"Os indicadores sugerem que pode cair mais. "
                f"Se já tem, considere realizar lucro. Se quer comprar, espere.\n"
            )
        else:
            msg += (
                f"🤔 **Momento neutro para {nome_bonito}.**\n"
                f"Sem sinal claro de compra ou venda. Se for comprar, "
                f"comece com pouco e vá aumentando.\n"
            )

        msg += (
            "\n⚠️ _Análise baseada em indicadores técnicos. "
            "Não é garantia de resultado. Use como um dos fatores "
            "na sua decisão._"
        )

        await update.message.reply_text(msg, parse_mode="Markdown")

    else:  # ação/FII
        analise = await analise_completa_acao(ativo_id)
        if not analise:
            await update.message.reply_text(
                f"❌ Não encontrei dados para '{nome}'. "
                "Verifique o código (ex: PETR4, VALE3, HGLG11)."
            )
            return

        stock = analise["stock"]
        sinal = analise["sinal"]
        emoji_sinal = SINAL_EMOJI.get(sinal["sinal"], "🟡")
        texto_sinal = SINAL_TEXTO.get(sinal["sinal"], "Neutro")

        msg = (
            f"📊 **Análise: {stock['nome']}** ({stock['ticker']})\n\n"
            f"💰 Preço: **R${stock['preco']:.2f}**\n"
            f"📈 Hoje: {stock['variacao_dia']:+.1f}%\n"
            f"📈 Máxima 52 sem: R${stock['max_52sem']:.2f}\n"
            f"📉 Mínima 52 sem: R${stock['min_52sem']:.2f}\n"
            f"📐 Distância do topo: {analise['dist_topo_52sem']:.1f}%\n\n"
            f"{emoji_sinal} **SINAL: {texto_sinal}**\n\n"
        )

        for motivo in sinal["motivos"]:
            msg += f"  {motivo}\n"

        msg += (
            "\n⚠️ _Análise baseada em dados de mercado. "
            "Não é recomendação de investimento._"
        )

        await update.message.reply_text(msg, parse_mode="Markdown")


# ── /comprei — Registrar uma compra na carteira ────────────────


async def comprei_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Registra que o usuário comprou um ativo."""
    user = await get_or_create_user(update.effective_user.id)
    if not user.get("is_premium"):
        await update.message.reply_text(
            "💎 A carteira com alertas é um recurso **Premium**!\n\n"
            "Com ela eu:\n"
            "• Acompanho suas compras em tempo real\n"
            "• Te aviso quando é hora de vender\n"
            "• Envio alertas de oportunidades\n"
            "• Mostro seu lucro/prejuízo atualizado\n\n"
            "Use /premium para assinar 🚀\n\n"
            "💡 Enquanto isso, use /analisar btc para ver a "
            "análise de mercado grátis!",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "📝 **Registrar compra**\n\n"
        "O que você comprou?\n"
        "_(Ex: btc, eth, PETR4, HGLG11, IVVB11)_",
        parse_mode="Markdown",
    )
    return COMPRA_ATIVO


async def comprei_ativo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe o ativo comprado."""
    nome = update.message.text.strip()
    ativo_id, tipo = normalizar_ativo(nome)
    context.user_data["compra_ativo"] = ativo_id
    context.user_data["compra_tipo"] = tipo

    # Buscar preço atual como sugestão
    if tipo == "crypto":
        preco_data = await get_crypto_price(ativo_id)
        preco_atual = preco_data["preco_brl"] if preco_data else None
    else:
        stock = await get_stock_price(ativo_id)
        preco_atual = stock["preco"] if stock else None

    if preco_atual:
        context.user_data["compra_preco_sugerido"] = preco_atual
        await update.message.reply_text(
            f"✅ Ativo: **{ativo_id.upper()}**\n"
            f"💰 Preço atual: R${preco_atual:,.2f}\n\n"
            "Quanto (em R$) você investiu nessa compra?\n"
            "_(Ex: 100, 500, 1000)_",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            f"✅ Ativo: **{ativo_id.upper()}**\n\n"
            "Quanto (em R$) você investiu?\n_(Ex: 100, 500, 1000)_",
            parse_mode="Markdown",
        )

    return COMPRA_VALOR


async def comprei_valor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe o valor investido."""
    try:
        valor = float(
            update.message.text.replace("R$", "")
            .replace(".", "")
            .replace(",", ".")
            .strip()
        )
        if valor <= 0:
            raise ValueError
    except (ValueError, AttributeError):
        await update.message.reply_text("❌ Valor inválido. Ex: **500**", parse_mode="Markdown")
        return COMPRA_VALOR

    context.user_data["compra_valor"] = valor

    preco_sugerido = context.user_data.get("compra_preco_sugerido")
    if preco_sugerido:
        await update.message.reply_text(
            f"✅ Valor: **R${valor:,.2f}**\n\n"
            f"Qual foi o preço unitário na hora da compra?\n"
            f"_(Preço atual é R${preco_sugerido:,.2f}. "
            f"Digite o valor ou envie 0 para usar o preço atual)_",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            f"✅ Valor: **R${valor:,.2f}**\n\n"
            "Qual foi o preço unitário na hora da compra?\n"
            "_(Se não souber, digite 0 que eu busco o preço atual)_",
            parse_mode="Markdown",
        )

    return COMPRA_PRECO


async def comprei_preco(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe o preço de compra e salva."""
    try:
        preco = float(
            update.message.text.replace("R$", "")
            .replace(".", "")
            .replace(",", ".")
            .strip()
        )
        if preco < 0:
            raise ValueError
    except (ValueError, AttributeError):
        await update.message.reply_text("❌ Valor inválido.", parse_mode="Markdown")
        return COMPRA_PRECO

    if preco == 0:
        preco = context.user_data.get("compra_preco_sugerido", 0)
        if not preco:
            await update.message.reply_text(
                "Não consegui buscar o preço atual. Digite manualmente."
            )
            return COMPRA_PRECO

    ativo = context.user_data["compra_ativo"]
    tipo = context.user_data["compra_tipo"]
    valor = context.user_data["compra_valor"]
    quantidade = valor / preco if preco else 0

    compra_id = await registrar_compra(
        telegram_id=update.effective_user.id,
        ativo=ativo,
        tipo=tipo,
        preco_compra=preco,
        valor_investido=valor,
        quantidade=quantidade,
    )

    tipo_label = "cripto" if tipo == "crypto" else "ação/FII"
    qtd_fmt = f"{quantidade:.8f}" if tipo == "crypto" else f"{quantidade:.2f}"

    await update.message.reply_text(
        f"✅ **Compra registrada!**\n\n"
        f"📦 Ativo: {ativo.upper()} ({tipo_label})\n"
        f"💰 Valor: R${valor:,.2f}\n"
        f"💵 Preço de compra: R${preco:,.2f}\n"
        f"📊 Quantidade: {qtd_fmt}\n\n"
        f"Vou acompanhar esse ativo pra você! 🔔\n"
        f"Quando for hora de vender, eu te aviso.\n\n"
        f"📋 Use /carteira para ver suas posições\n"
        f"📊 Use /analisar {ativo} para ver a análise atual",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def cancel_compra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Registro cancelado.")
    return ConversationHandler.END


# ── /carteira — Ver posições atuais ────────────────────────────


async def carteira(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra a carteira atual com lucro/prejuízo em tempo real."""
    user = await get_or_create_user(update.effective_user.id)
    if not user.get("is_premium"):
        await update.message.reply_text(
            "💎 A carteira é um recurso **Premium**!\n"
            "Use /premium para assinar 🚀",
            parse_mode="Markdown",
        )
        return

    posicoes = await get_carteira_ativa(update.effective_user.id)
    if not posicoes:
        await update.message.reply_text(
            "📋 Sua carteira está vazia!\n\n"
            "Use /comprei para registrar uma compra.\n"
            'Ex: comprou Bitcoin? Use /comprei e siga as instruções.',
        )
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    linhas = []
    total_investido = 0
    total_atual = 0

    for pos in posicoes:
        ativo = pos["ativo"]
        tipo = pos["tipo"]
        preco_compra = pos["preco_compra"]
        valor_investido = pos["valor_investido"]

        # Buscar preço atual
        if tipo == "crypto":
            preco_data = await get_crypto_price(ativo)
            preco_atual = preco_data["preco_brl"] if preco_data else preco_compra
        else:
            stock = await get_stock_price(ativo)
            preco_atual = stock["preco"] if stock else preco_compra

        variacao = ((preco_atual - preco_compra) / preco_compra) * 100
        valor_atual = valor_investido * (1 + variacao / 100)
        lucro = valor_atual - valor_investido

        total_investido += valor_investido
        total_atual += valor_atual

        emoji = "🟢" if lucro >= 0 else "🔴"
        sinal = "+" if lucro >= 0 else ""

        nome_display = CRYPTO_NOMES.get(ativo, ativo.upper())

        linhas.append(
            f"{emoji} **{nome_display}**\n"
            f"  Compra: R${preco_compra:,.2f} → Atual: R${preco_atual:,.2f}\n"
            f"  Investido: R${valor_investido:,.2f} → Hoje: R${valor_atual:,.2f}\n"
            f"  Resultado: **{sinal}R${lucro:,.2f} ({sinal}{variacao:.1f}%)**"
        )

    lucro_total = total_atual - total_investido
    emoji_total = "🟢" if lucro_total >= 0 else "🔴"
    sinal_total = "+" if lucro_total >= 0 else ""
    var_total = (
        ((total_atual - total_investido) / total_investido * 100)
        if total_investido
        else 0
    )

    msg = (
        "📋 **Sua Carteira**\n\n"
        + "\n\n".join(linhas)
        + f"\n\n━━━━━━━━━━━━━━━━━━━\n"
        f"{emoji_total} **TOTAL:**\n"
        f"Investido: R${total_investido:,.2f}\n"
        f"Valor atual: R${total_atual:,.2f}\n"
        f"Resultado: **{sinal_total}R${lucro_total:,.2f} "
        f"({sinal_total}{var_total:.1f}%)**\n\n"
        "📊 /analisar [ativo] — Ver análise detalhada\n"
        "🔔 /alertas — Configurar notificações"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")


# ── /alertas — Configurar notificações ─────────────────────────


async def alertas_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gerencia alertas de compra/venda."""
    await update.message.reply_text(
        "🔔 **Alertas Inteligentes**\n\n"
        "Eu monitoro seus ativos e te aviso quando:\n"
        "• 📈 É um bom momento para vender (com lucro)\n"
        "• 📉 Caiu muito e pode ser hora de comprar mais\n"
        "• 🚀 Seu investimento dobrou de valor\n"
        "• ⚠️ Algo precisa da sua atenção\n\n"
        "O que deseja?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ Ativar alertas", callback_data="alertas_on"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "❌ Desativar alertas", callback_data="alertas_off"
                    )
                ],
            ]
        ),
    )


async def alertas_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Liga ou desliga alertas."""
    query = update.callback_query
    await query.answer()

    ativo = query.data == "alertas_on"
    await toggle_alertas(query.from_user.id, ativo)

    if ativo:
        await query.edit_message_text(
            "✅ **Alertas ativados!**\n\n"
            "Vou monitorar sua carteira e te mandar mensagem "
            "quando identificar uma oportunidade de venda ou compra.\n\n"
            "📋 Certifique-se de registrar suas compras com /comprei "
            "para que eu possa acompanhar!",
            parse_mode="Markdown",
        )
    else:
        await query.edit_message_text(
            "❌ Alertas desativados.\n\n"
            "Use /alertas para reativar quando quiser.",
        )


# ── Registro rápido (1 toque) ────────────────────────────────


async def quick_register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Registra uma compra com 1 toque a partir do callback data.
    Formato: qreg_{tipo}_{ativo}_{valor}
    Ex: qreg_c_bitcoin_100, qreg_a_IVVB11_125
    """
    query = update.callback_query
    await query.answer("Registrando compra...")

    try:
        _, tipo_code, ativo, valor_str = query.data.split("_", 3)
        valor = float(valor_str)
        tipo = "crypto" if tipo_code == "c" else "acao"

        # Buscar preço atual
        if tipo == "crypto":
            preco_data = await get_crypto_price(ativo)
            preco = preco_data["preco_brl"] if preco_data else 0
        else:
            stock = await get_stock_price(ativo)
            preco = stock["preco"] if stock else 0

        if not preco:
            await query.edit_message_text(
                "❌ Não consegui buscar o preço atual. "
                f"Use /comprei para registrar manualmente."
            )
            return

        quantidade = valor / preco if preco else 0
        nome = CRYPTO_NOMES.get(ativo, ativo.upper())

        await registrar_compra(
            telegram_id=query.from_user.id,
            ativo=ativo,
            tipo=tipo,
            preco_compra=preco,
            valor_investido=valor,
            quantidade=quantidade,
        )

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                f"✅ **Compra registrada!** {nome}\n"
                f"💰 R${valor:,.2f} a R${preco:,.2f}\n\n"
                f"📋 /carteira — Ver suas posições\n"
                f"🔔 Vou te avisar quando for hora de vender!"
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error("Erro no quick register: %s", e)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="❌ Erro ao registrar. Use /comprei para registrar manualmente.",
        )


def get_carteira_handlers() -> list:
    """Retorna os handlers da carteira."""
    conv_compra = ConversationHandler(
        entry_points=[CommandHandler("comprei", comprei_start)],
        states={
            COMPRA_ATIVO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, comprei_ativo)
            ],
            COMPRA_VALOR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, comprei_valor)
            ],
            COMPRA_PRECO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, comprei_preco)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_compra)],
    )

    return [
        conv_compra,
        CommandHandler("analisar", analisar),
        CommandHandler("carteira", carteira),
        CommandHandler("alertas", alertas_cmd),
        CallbackQueryHandler(alertas_toggle, pattern=r"^alertas_(on|off)$"),
        CallbackQueryHandler(quick_register, pattern=r"^qreg_"),
    ]
