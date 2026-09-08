"""Handlers de gestão de dívidas."""

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

from services.finance_calc import estrategia_dividas
from services.user_service import add_divida, get_dividas, get_or_create_user

logger = logging.getLogger(__name__)

# Estados
DIV_NOME, DIV_VALOR, DIV_JUROS = range(3)


async def dividas_listar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista as dívidas do usuário ou inicia cadastro."""
    dividas = await get_dividas(update.effective_user.id)

    if not dividas:
        await update.message.reply_text(
            "💳 Você não tem dívidas cadastradas!\n\n"
            "Isso é ótimo... ou você ainda não cadastrou? 😄\n\n"
            "Use /novadivida para cadastrar uma dívida\n"
            "Use /estrategia para ver o plano de quitação",
        )
        return

    linhas = []
    total = 0
    for d in dividas:
        total += d["valor_total"]
        juros = (
            f" • Juros: {d['taxa_juros_mensal']:.1f}%/mês"
            if d["taxa_juros_mensal"]
            else ""
        )
        linhas.append(f"• **{d['nome']}**: R${d['valor_total']:,.2f}{juros}")

    await update.message.reply_text(
        f"💳 **Suas Dívidas**\n\n"
        + "\n".join(linhas)
        + f"\n\n💰 **Total: R${total:,.2f}**\n\n"
        "Use /novadivida para adicionar mais\n"
        "Use /estrategia para ver o plano de quitação",
        parse_mode="Markdown",
    )


async def nova_divida_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia o cadastro de uma nova dívida."""
    user = await get_or_create_user(update.effective_user.id)
    if not user.get("is_premium"):
        await update.message.reply_text(
            "💎 A gestão de dívidas é um recurso **Premium**!\n\n"
            "Com ele eu monto uma estratégia personalizada para "
            "você quitar suas dívidas o mais rápido possível.\n\n"
            "Use /premium para assinar 🚀",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "💳 **Cadastrar dívida**\n\n"
        "Qual o **nome** da dívida?\n"
        '_(Ex: "Cartão Nubank", "Empréstimo Caixa", "Cheque especial")_',
        parse_mode="Markdown",
    )
    return DIV_NOME


async def receber_div_nome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe o nome da dívida."""
    nome = update.message.text.strip()
    if len(nome) < 2:
        await update.message.reply_text("Nome muito curto. Tente novamente.")
        return DIV_NOME

    context.user_data["div_nome"] = nome
    await update.message.reply_text(
        f'✅ Dívida: **{nome}**\n\n'
        "Qual o **valor total** da dívida?\n"
        "_(O quanto você deve hoje)_",
        parse_mode="Markdown",
    )
    return DIV_VALOR


async def receber_div_valor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe o valor da dívida."""
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
        await update.message.reply_text("❌ Valor inválido. Ex: **5000**", parse_mode="Markdown")
        return DIV_VALOR

    context.user_data["div_valor"] = valor
    await update.message.reply_text(
        f"✅ Valor: **R${valor:,.2f}**\n\n"
        "Qual a **taxa de juros mensal**?\n"
        "_(Ex: 12 para 12%/mês. Digite 0 se não souber)_",
        parse_mode="Markdown",
    )
    return DIV_JUROS


async def receber_div_juros(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe os juros e salva a dívida."""
    try:
        juros = float(
            update.message.text.replace("%", "").replace(",", ".").strip()
        )
        if juros < 0:
            raise ValueError
    except (ValueError, AttributeError):
        await update.message.reply_text("❌ Valor inválido. Ex: **3.5** ou **0**", parse_mode="Markdown")
        return DIV_JUROS

    nome = context.user_data["div_nome"]
    valor = context.user_data["div_valor"]

    await add_divida(
        update.effective_user.id, nome, valor, taxa_juros_mensal=juros
    )

    msg = f"✅ **Dívida cadastrada!**\n\n"
    msg += f"📋 {nome}\n"
    msg += f"💰 R${valor:,.2f}\n"
    if juros > 0:
        msg += f"📈 Juros: {juros:.1f}% ao mês\n"
        # Mostrar quanto custa por mês em juros
        custo_juros = valor * juros / 100
        msg += f"⚠️ Essa dívida te custa **R${custo_juros:,.2f}/mês** só em juros!\n"

    msg += "\nUse /estrategia para ver o plano de quitação 💪"

    await update.message.reply_text(msg, parse_mode="Markdown")
    return ConversationHandler.END


async def estrategia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra a estratégia de quitação de dívidas."""
    dividas = await get_dividas(update.effective_user.id)

    if not dividas:
        await update.message.reply_text(
            "Você não tem dívidas cadastradas! Use /novadivida para cadastrar."
        )
        return

    user = await get_or_create_user(update.effective_user.id)
    renda = user.get("renda_mensal", 0)

    # Calcular valor disponível para dívidas (estimativa)
    valor_extra = renda * 0.2 if renda else 0  # 20% da renda

    plano = estrategia_dividas(dividas, valor_extra)

    msg = "🎯 **Estratégia para Quitar Dívidas**\n\n"
    msg += f"💰 Total de dívidas: **R${plano['total_dividas']:,.2f}**\n"

    if plano["juros_mensal_estimado"] > 0:
        msg += (
            f"🔥 Juros mensais: **R${plano['juros_mensal_estimado']:,.2f}**\n"
            f"_(Isso é o que você perde todo mês!)_\n\n"
        )

    msg += "**🏔️ Método Avalanche (recomendado)**\n"
    msg += "_(Pagar primeiro a de maior juros — economiza mais)_\n"
    for i, nome in enumerate(plano["avalanche"], 1):
        msg += f"  {i}. {nome}\n"

    msg += "\n**⛄ Método Bola de Neve**\n"
    msg += "_(Pagar primeiro a menor — motivação rápida)_\n"
    for i, nome in enumerate(plano["bola_neve"], 1):
        msg += f"  {i}. {nome}\n"

    if valor_extra > 0:
        msg += (
            f"\n💡 Se você destinar **R${valor_extra:,.2f}/mês** "
            "(20% da renda) para quitar dívidas, vai se livrar muito mais rápido!"
        )

    msg += "\n\n🤖 Me pergunte para uma análise mais detalhada!"

    await update.message.reply_text(msg, parse_mode="Markdown")


async def cancel_divida(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela o cadastro de dívida."""
    await update.message.reply_text("Cadastro cancelado.")
    return ConversationHandler.END


def get_dividas_handlers() -> list:
    """Retorna os handlers de dívidas."""
    conv = ConversationHandler(
        entry_points=[CommandHandler("novadivida", nova_divida_start)],
        states={
            DIV_NOME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receber_div_nome)
            ],
            DIV_VALOR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receber_div_valor)
            ],
            DIV_JUROS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receber_div_juros)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_divida)],
    )
    return [
        conv,
        CommandHandler("dividas", dividas_listar),
        CommandHandler("estrategia", estrategia),
    ]
