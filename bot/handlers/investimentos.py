"""Handlers de investimentos — calculadora e comparador."""

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

from services.cdi_service import cdi_anual, get_cdi_atual
from services.finance_calc import BANCOS_POPULARES, calcular_rendimento, comparar_investimentos

logger = logging.getLogger(__name__)

# Estados da conversa
VALOR_INICIAL, APORTE_MENSAL, PRAZO, PERCENTUAL_CDI = range(4)


# ── /investir — Calculadora interativa ──────────────────────────


async def investir_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia a calculadora de investimentos."""
    await update.message.reply_text(
        "📈 **Calculadora de Investimentos**\n\n"
        "Vou calcular quanto seu dinheiro vai render!\n\n"
        "Qual o **valor inicial** que você quer investir?\n"
        "_(Digite só o número, ex: 1000)_",
        parse_mode="Markdown",
    )
    return VALOR_INICIAL


async def receber_valor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe o valor inicial."""
    try:
        valor = float(
            update.message.text.replace("R$", "")
            .replace(".", "")
            .replace(",", ".")
            .strip()
        )
        if valor < 0:
            raise ValueError
    except (ValueError, AttributeError):
        await update.message.reply_text(
            "❌ Valor inválido. Digite apenas o número, ex: **1000**",
            parse_mode="Markdown",
        )
        return VALOR_INICIAL

    context.user_data["inv_valor"] = valor
    await update.message.reply_text(
        f"✅ Valor inicial: **R${valor:,.2f}**\n\n"
        "Quanto você pretende **aportar por mês**?\n"
        "_(Digite 0 se não vai aportar)_",
        parse_mode="Markdown",
    )
    return APORTE_MENSAL


async def receber_aporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe o aporte mensal."""
    try:
        aporte = float(
            update.message.text.replace("R$", "")
            .replace(".", "")
            .replace(",", ".")
            .strip()
        )
        if aporte < 0:
            raise ValueError
    except (ValueError, AttributeError):
        await update.message.reply_text("❌ Valor inválido. Ex: **200** ou **0**", parse_mode="Markdown")
        return APORTE_MENSAL

    context.user_data["inv_aporte"] = aporte
    await update.message.reply_text(
        f"✅ Aporte mensal: **R${aporte:,.2f}**\n\n"
        "Por **quantos meses** quer investir?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("3 meses", callback_data="prazo_3"),
                    InlineKeyboardButton("6 meses", callback_data="prazo_6"),
                ],
                [
                    InlineKeyboardButton("12 meses", callback_data="prazo_12"),
                    InlineKeyboardButton("24 meses", callback_data="prazo_24"),
                ],
                [
                    InlineKeyboardButton("36 meses", callback_data="prazo_36"),
                    InlineKeyboardButton("60 meses", callback_data="prazo_60"),
                ],
            ]
        ),
    )
    return PRAZO


async def receber_prazo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe o prazo e mostra o resultado."""
    query = update.callback_query
    await query.answer()

    meses = int(query.data.replace("prazo_", ""))
    context.user_data["inv_prazo"] = meses

    valor = context.user_data["inv_valor"]
    aporte = context.user_data["inv_aporte"]

    # Buscar CDI ao vivo
    cdi = await get_cdi_atual()
    taxa_anual = cdi_anual(cdi["taxa"])

    # Calcular com 100% CDI como base
    resultado = calcular_rendimento(valor, aporte, taxa_anual, meses, 100)

    # Também calcular poupança para comparação
    poupanca = calcular_rendimento(valor, aporte, taxa_anual, meses, 61.8)

    diferenca = resultado["valor_liquido"] - poupanca["valor_liquido"]

    await query.edit_message_text(
        f"📊 **Resultado da simulação**\n\n"
        f"💵 Valor inicial: R${valor:,.2f}\n"
        f"📥 Aporte mensal: R${aporte:,.2f}\n"
        f"📅 Prazo: {meses} meses\n"
        f"📈 CDI atual: {taxa_anual:.2f}% ao ano\n\n"
        f"**━━━ Rendimento a 100% CDI ━━━**\n"
        f"💰 Valor bruto: R${resultado['valor_final_bruto']:,.2f}\n"
        f"📈 Rendimento bruto: R${resultado['rendimento_bruto']:,.2f}\n"
        f"🏛️ IR ({resultado['aliquota_ir']*100:.1f}%): -R${resultado['ir']:,.2f}\n"
        f"✅ **Valor líquido: R${resultado['valor_liquido']:,.2f}**\n"
        f"💚 Rendimento líquido: R${resultado['rendimento_liquido']:,.2f}\n\n"
        f"**━━━ Na Poupança (~61.8% CDI) ━━━**\n"
        f"✅ Valor líquido: R${poupanca['valor_liquido']:,.2f}\n"
        f"💚 Rendimento líquido: R${poupanca['rendimento_liquido']:,.2f}\n\n"
        f"🏆 **No CDI você ganha R${diferenca:,.2f} a mais** que na poupança!\n\n"
        "Use /comparar para ver qual banco rende mais 🏦",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


# ── /comparar — Comparador de bancos ───────────────────────────


async def comparar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Compara os rendimentos dos principais bancos."""
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    # Buscar CDI ao vivo
    cdi = await get_cdi_atual()
    taxa_anual = cdi_anual(cdi["taxa"])

    # Simular R$1.000 por 12 meses em cada banco
    valor = 1000
    meses = 12
    resultados = comparar_investimentos(valor, 0, meses, taxa_anual, BANCOS_POPULARES)

    linhas = []
    for i, r in enumerate(resultados):
        emoji = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "  "
        linhas.append(
            f"{emoji} **{r['nome']}** ({r['percentual_cdi']}% CDI)\n"
            f"    → R${r['valor_liquido']:,.2f} "
            f"(+R${r['rendimento_liquido']:,.2f} líquido)"
        )

    texto = (
        f"🏦 **Comparação de Bancos/Corretoras**\n\n"
        f"Simulação: R${valor:,.2f} por {meses} meses\n"
        f"CDI atual: {taxa_anual:.2f}% ao ano\n\n"
        + "\n\n".join(linhas)
        + "\n\n💡 Quer simular com outro valor? Use /investir"
    )

    await update.message.reply_text(texto, parse_mode="Markdown")


async def cancel_investir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela a calculadora."""
    await update.message.reply_text("Calculadora cancelada. Use /investir para recomeçar.")
    return ConversationHandler.END


def get_investimentos_handlers() -> list:
    """Retorna os handlers de investimentos."""
    conv = ConversationHandler(
        entry_points=[CommandHandler("investir", investir_start)],
        states={
            VALOR_INICIAL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receber_valor)
            ],
            APORTE_MENSAL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receber_aporte)
            ],
            PRAZO: [CallbackQueryHandler(receber_prazo, pattern="^prazo_")],
        },
        fallbacks=[CommandHandler("cancel", cancel_investir)],
    )
    return [conv, CommandHandler("comparar", comparar)]
