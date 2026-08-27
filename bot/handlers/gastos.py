"""Handlers de controle de gastos."""

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

from config import CATEGORIAS_GASTOS
from services.user_service import add_gasto, get_or_create_user, get_resumo_gastos_mes

logger = logging.getLogger(__name__)

# Estados
GASTO_VALOR, GASTO_CATEGORIA, GASTO_DESCRICAO = range(3)


async def gasto_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia o registro de um gasto."""
    user = await get_or_create_user(update.effective_user.id)
    if not user.get("is_premium"):
        await update.message.reply_text(
            "💎 O registro de gastos é um recurso **Premium**!\n\n"
            "Com ele você:\n"
            "• Registra gastos rapidamente pelo chat\n"
            "• Vê para onde está indo seu dinheiro\n"
            "• Recebe alertas quando estiver gastando demais\n"
            "• Recebe relatório semanal automático\n\n"
            "Use /premium para assinar 🚀",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "💸 **Registrar gasto**\n\n"
        "Quanto você gastou?\n"
        "_(Digite só o valor, ex: 45.90)_",
        parse_mode="Markdown",
    )
    return GASTO_VALOR


async def receber_gasto_valor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe o valor do gasto."""
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
        await update.message.reply_text(
            "❌ Valor inválido. Digite apenas o número, ex: **45.90**",
            parse_mode="Markdown",
        )
        return GASTO_VALOR

    context.user_data["gasto_valor"] = valor

    # Montar teclado de categorias
    botoes = []
    for i in range(0, len(CATEGORIAS_GASTOS), 2):
        row = [
            InlineKeyboardButton(
                CATEGORIAS_GASTOS[i],
                callback_data=f"cat_{i}",
            )
        ]
        if i + 1 < len(CATEGORIAS_GASTOS):
            row.append(
                InlineKeyboardButton(
                    CATEGORIAS_GASTOS[i + 1],
                    callback_data=f"cat_{i+1}",
                )
            )
        botoes.append(row)

    await update.message.reply_text(
        f"✅ Valor: **R${valor:,.2f}**\n\nQual a categoria?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(botoes),
    )
    return GASTO_CATEGORIA


async def receber_gasto_categoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe a categoria do gasto."""
    query = update.callback_query
    await query.answer()

    idx = int(query.data.replace("cat_", ""))
    categoria = CATEGORIAS_GASTOS[idx]
    context.user_data["gasto_categoria"] = categoria

    await query.edit_message_text(
        f"✅ Categoria: **{categoria}**\n\n"
        "Quer adicionar uma **descrição**?\n"
        '_(Ex: "Almoço no restaurante" ou digite /pular)_',
        parse_mode="Markdown",
    )
    return GASTO_DESCRICAO


async def receber_gasto_descricao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe a descrição e salva o gasto."""
    descricao = update.message.text.strip() if update.message.text else ""

    valor = context.user_data["gasto_valor"]
    categoria = context.user_data["gasto_categoria"]

    await add_gasto(update.effective_user.id, valor, categoria, descricao)

    # Buscar resumo do mês
    resumo = await get_resumo_gastos_mes(update.effective_user.id)

    await update.message.reply_text(
        f"✅ **Gasto registrado!**\n\n"
        f"💸 R${valor:,.2f} — {categoria}\n"
        f"📝 {descricao or '(sem descrição)'}\n\n"
        f"📊 **Total do mês:** R${resumo['total']:,.2f} "
        f"({resumo['quantidade']} gastos)\n\n"
        "Use /resumo para ver o detalhamento completo.",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def pular_descricao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pula a descrição e salva o gasto."""
    valor = context.user_data["gasto_valor"]
    categoria = context.user_data["gasto_categoria"]

    await add_gasto(update.effective_user.id, valor, categoria)

    resumo = await get_resumo_gastos_mes(update.effective_user.id)

    await update.message.reply_text(
        f"✅ **Gasto registrado!**\n\n"
        f"💸 R${valor:,.2f} — {categoria}\n\n"
        f"📊 **Total do mês:** R${resumo['total']:,.2f}\n",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def resumo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o resumo de gastos do mês."""
    resumo = await get_resumo_gastos_mes(update.effective_user.id)

    if resumo["quantidade"] == 0:
        await update.message.reply_text(
            "📊 Nenhum gasto registrado este mês.\n\n"
            "Use /gasto para começar a registrar!"
        )
        return

    linhas = []
    for cat, val in sorted(
        resumo["categorias"].items(), key=lambda x: x[1], reverse=True
    ):
        pct = val / resumo["total"] * 100
        barra = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        linhas.append(f"{cat}\n  R${val:,.2f} ({pct:.0f}%) {barra}")

    await update.message.reply_text(
        f"📊 **Resumo de Gastos — Mês Atual**\n\n"
        f"💰 Total: **R${resumo['total']:,.2f}**\n"
        f"📝 {resumo['quantidade']} gastos registrados\n\n"
        + "\n\n".join(linhas)
        + "\n\n💡 Me pergunte como reduzir seus gastos!",
        parse_mode="Markdown",
    )


async def cancel_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela o registro de gasto."""
    await update.message.reply_text("Registro cancelado.")
    return ConversationHandler.END


def get_gastos_handlers() -> list:
    """Retorna os handlers de gastos."""
    conv = ConversationHandler(
        entry_points=[CommandHandler("gasto", gasto_start)],
        states={
            GASTO_VALOR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receber_gasto_valor)
            ],
            GASTO_CATEGORIA: [
                CallbackQueryHandler(receber_gasto_categoria, pattern="^cat_")
            ],
            GASTO_DESCRICAO: [
                CommandHandler("pular", pular_descricao),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, receber_gasto_descricao
                ),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_gasto)],
    )
    return [conv, CommandHandler("resumo", resumo)]
