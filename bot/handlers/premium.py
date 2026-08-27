"""Handlers do plano premium."""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from config import PREMIUM_PRICE
from services.user_service import get_or_create_user

logger = logging.getLogger(__name__)


async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra informações do plano premium."""
    user = await get_or_create_user(update.effective_user.id)

    if user.get("is_premium"):
        await update.message.reply_text(
            "💎 **Você é Premium!** ✅\n\n"
            "Aproveite todos os recursos:\n"
            "• ♾️ Consultas ilimitadas com a IA\n"
            "• 💸 Registro e análise de gastos\n"
            "• 💳 Gestão de dívidas com estratégia\n"
            "• 🎯 Metas com acompanhamento\n"
            "• 📊 Relatórios semanais\n\n"
            "Obrigado por apoiar o FinançasIA! 🙏",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(
        f"💎 **Plano Premium — R${PREMIUM_PRICE:.2f}/mês**\n\n"
        "O que você ganha:\n\n"
        "🤖 **IA sem limites**\n"
        "• Consultas ilimitadas ao consultor IA\n"
        "• Respostas mais detalhadas e personalizadas\n\n"
        "💸 **Controle de gastos**\n"
        "• Registre gastos pelo chat em segundos\n"
        "• Veja para onde vai seu dinheiro\n"
        "• Alertas quando estiver gastando demais\n\n"
        "📋 **Planejamento completo**\n"
        "• Estratégia personalizada para quitar dívidas\n"
        "• Metas financeiras com acompanhamento\n"
        "• Relatório semanal automático\n\n"
        "💰 **Quanto custa um consultor financeiro?**\n"
        "R$200-500 por hora. Com o FinançasIA, você tem "
        f"orientação 24h por apenas **R${PREMIUM_PRICE:.2f}/mês**.\n\n"
        "🔒 Cancele quando quiser. Sem multa, sem burocracia.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"✅ Assinar por R${PREMIUM_PRICE:.2f}/mês",
                        callback_data="premium_assinar",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🎁 Tenho um código de desconto",
                        callback_data="premium_codigo",
                    )
                ],
            ]
        ),
    )


async def premium_assinar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler para quando o usuário quer assinar.

    NOTA: Aqui você integraria com um gateway de pagamento real.
    Opções populares no Brasil:
    - Stripe (internacional, aceita PIX)
    - Mercado Pago (muito usado no Brasil)
    - PagSeguro
    - Asaas (bom para recorrência)
    - Hotmart (se quiser vender como produto digital)
    """
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🚀 **Quase lá!**\n\n"
        "Para assinar o Premium, escolha a forma de pagamento:\n\n"
        "💳 **PIX** — Aprovação instantânea\n"
        "💳 **Cartão de crédito** — Cobrança recorrente automática\n\n"
        "━━━━━━━━━━━━━━━\n\n"
        "⚙️ _O sistema de pagamento está sendo configurado._\n"
        "_Em breve você poderá assinar diretamente aqui!_\n\n"
        "📩 Enquanto isso, entre em contato para assinar manualmente:\n"
        "Use /contato para falar com o suporte.",
        parse_mode="Markdown",
    )


async def premium_codigo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para código de desconto."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🎁 **Código de Desconto**\n\n"
        "Envie seu código de desconto como mensagem.\n"
        '_(Ex: "PROMO50")_\n\n'
        "💡 Dica: siga nosso Instagram para promoções exclusivas!",
        parse_mode="Markdown",
    )


def get_premium_handlers() -> list:
    """Retorna os handlers do premium."""
    return [
        CommandHandler("premium", premium),
        CallbackQueryHandler(premium_assinar, pattern="^premium_assinar$"),
        CallbackQueryHandler(premium_codigo, pattern="^premium_codigo$"),
    ]
