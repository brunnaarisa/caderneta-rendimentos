"""Handlers de metas financeiras."""

import logging

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from services.user_service import add_meta, get_metas, get_or_create_user

logger = logging.getLogger(__name__)

META_NOME, META_VALOR, META_PRAZO = range(3)


async def metas_listar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista as metas do usuário."""
    metas = await get_metas(update.effective_user.id)

    if not metas:
        await update.message.reply_text(
            "🎯 Você não tem metas cadastradas!\n\n"
            "Use /meta para criar sua primeira meta financeira."
        )
        return

    linhas = []
    for m in metas:
        pct = (m["valor_atual"] / m["valor_alvo"] * 100) if m["valor_alvo"] else 0
        barra_cheia = int(pct / 5)
        barra = "🟩" * barra_cheia + "⬜" * (20 - barra_cheia)
        linhas.append(
            f"**{m['nome']}**\n"
            f"R${m['valor_atual']:,.2f} / R${m['valor_alvo']:,.2f} ({pct:.0f}%)\n"
            f"{barra}"
        )

    await update.message.reply_text(
        "🎯 **Suas Metas Financeiras**\n\n" + "\n\n".join(linhas),
        parse_mode="Markdown",
    )


async def meta_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia a criação de uma meta."""
    user = await get_or_create_user(update.effective_user.id)
    if not user.get("is_premium"):
        await update.message.reply_text(
            "💎 Metas financeiras é um recurso **Premium**!\n\n"
            "Com ele você:\n"
            "• Cria metas com acompanhamento visual\n"
            "• Recebe lembretes para poupar\n"
            "• Vê projeções de quando vai atingir\n\n"
            "Use /premium para assinar 🚀",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "🎯 **Criar Meta Financeira**\n\n"
        "Qual o **nome** da sua meta?\n"
        '_(Ex: "Viagem para Europa", "Entrada do apê", "Reserva de emergência")_',
        parse_mode="Markdown",
    )
    return META_NOME


async def receber_meta_nome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe o nome da meta."""
    nome = update.message.text.strip()
    context.user_data["meta_nome"] = nome

    await update.message.reply_text(
        f'✅ Meta: **{nome}**\n\n'
        "Qual o **valor total** que você precisa?\n"
        "_(Ex: 15000)_",
        parse_mode="Markdown",
    )
    return META_VALOR


async def receber_meta_valor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe o valor alvo da meta."""
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
        await update.message.reply_text("❌ Valor inválido. Ex: **15000**", parse_mode="Markdown")
        return META_VALOR

    context.user_data["meta_valor"] = valor

    await update.message.reply_text(
        f"✅ Valor: **R${valor:,.2f}**\n\n"
        "Em **quantos meses** quer atingir essa meta?\n"
        "_(Ex: 12, 24, 36)_",
        parse_mode="Markdown",
    )
    return META_PRAZO


async def receber_meta_prazo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe o prazo e salva a meta."""
    try:
        prazo = int(update.message.text.strip())
        if prazo <= 0:
            raise ValueError
    except (ValueError, AttributeError):
        await update.message.reply_text("❌ Prazo inválido. Ex: **12**", parse_mode="Markdown")
        return META_PRAZO

    nome = context.user_data["meta_nome"]
    valor = context.user_data["meta_valor"]

    await add_meta(update.effective_user.id, nome, valor, prazo)

    mensal = valor / prazo

    await update.message.reply_text(
        f"🎯 **Meta criada!**\n\n"
        f"📋 {nome}\n"
        f"💰 Objetivo: R${valor:,.2f}\n"
        f"📅 Prazo: {prazo} meses\n\n"
        f"📥 Você precisa guardar **R${mensal:,.2f}/mês** para atingir!\n\n"
        f"💡 Investindo a 100% CDI, você pode guardar um pouco menos, "
        f"porque o rendimento ajuda. Me pergunte para uma projeção detalhada!",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def cancel_meta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela a criação de meta."""
    await update.message.reply_text("Criação de meta cancelada.")
    return ConversationHandler.END


def get_metas_handlers() -> list:
    """Retorna os handlers de metas."""
    conv = ConversationHandler(
        entry_points=[CommandHandler("meta", meta_start)],
        states={
            META_NOME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receber_meta_nome)
            ],
            META_VALOR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receber_meta_valor)
            ],
            META_PRAZO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receber_meta_prazo)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_meta)],
    )
    return [conv, CommandHandler("metas", metas_listar)]
