"""
Handlers do plano premium — com pagamento via Pix (Mercado Pago).

/premium — Mostra planos e permite assinar
/meupremiun — Verifica status do premium
/verificarpix — Verifica se o Pix foi pago
"""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from config import MERCADOPAGO_ACCESS_TOKEN, PREMIUM_PRICE
from services.user_service import get_or_create_user

logger = logging.getLogger(__name__)


async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra informações do plano premium."""
    user = await get_or_create_user(update.effective_user.id)

    if user.get("is_premium"):
        premium_ate = user.get("premium_ate", "indefinido")
        await update.message.reply_text(
            "💎 **Você é Premium!** ✅\n\n"
            f"📅 Ativo até: {premium_ate}\n\n"
            "Aproveite todos os recursos:\n"
            "• ♾️ Consultas ilimitadas com a IA\n"
            "• 💼 Carteira com alertas inteligentes\n"
            "• 📊 Evolução e gráficos da carteira\n"
            "• 🛑 Stop-loss e take-profit automáticos\n"
            "• 📋 Relatórios semanais\n"
            "• 🏆 Compartilhamento de resultados\n\n"
            "Obrigado por apoiar o FinançasIA! 🙏",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(
        f"💎 **Plano Premium — R${PREMIUM_PRICE:.2f}/mês**\n\n"
        "O que você ganha:\n\n"
        "🤖 **IA sem limites**\n"
        "• Consultas ilimitadas ao consultor IA\n"
        "• Planos de investimento ilimitados\n\n"
        "💼 **Carteira inteligente**\n"
        "• Registro de compras e vendas\n"
        "• Alertas automáticos de venda/compra\n"
        "• 🛑 Stop-loss e take-profit automáticos\n"
        "• 📈 Evolução e gráfico da carteira\n\n"
        "📋 **Planejamento completo**\n"
        "• Controle de gastos e dívidas\n"
        "• Metas financeiras com acompanhamento\n"
        "• Relatório semanal automático\n"
        "• Calculadora de IR sobre investimentos\n\n"
        "🔔 **Alertas exclusivos**\n"
        "• Alertas urgentes de mercado (compra/venda)\n"
        "• Alertas de preço-alvo personalizados\n"
        "• Resumo matinal diário\n\n"
        "💰 **Quanto custa um consultor financeiro?**\n"
        "R$200-500 por hora. Com o FinançasIA, você tem "
        f"orientação 24h por apenas **R${PREMIUM_PRICE:.2f}/mês**.\n\n"
        "🔒 Cancele quando quiser. Sem multa, sem burocracia.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"💳 Pagar R${PREMIUM_PRICE:.2f} via PIX",
                        callback_data="premium_pix_1",
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"💰 3 meses por R${PREMIUM_PRICE * 3 * 0.85:.2f} (-15%)",
                        callback_data="premium_pix_3",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔍 Verificar pagamento pendente",
                        callback_data="premium_verificar",
                    )
                ],
            ]
        ),
    )


async def premium_pix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gera cobrança Pix via Mercado Pago."""
    query = update.callback_query
    await query.answer()

    telegram_id = query.from_user.id

    # Extrair quantidade de meses
    meses_str = query.data.split("_")[-1]
    meses = int(meses_str)

    if not MERCADOPAGO_ACCESS_TOKEN:
        # Modo sem integração — mostra instruções manuais
        valor = PREMIUM_PRICE * meses
        if meses == 3:
            valor = PREMIUM_PRICE * 3 * 0.85

        await query.edit_message_text(
            f"💳 **Pagamento via PIX**\n\n"
            f"Valor: **R${valor:.2f}** ({meses} mês(es))\n\n"
            "📱 **Como pagar:**\n\n"
            "1️⃣ Abra seu app bancário\n"
            "2️⃣ Escolha pagar com Pix\n"
            "3️⃣ Use a chave Pix abaixo:\n\n"
            "🔑 _Chave Pix será configurada em breve!_\n\n"
            "⚙️ _O sistema de pagamento automático está sendo "
            "configurado. Para ativar agora, entre em contato._\n\n"
            "📩 Envie o comprovante e ativaremos em minutos!",
            parse_mode="Markdown",
        )
        return

    # Gerar cobrança real via Mercado Pago
    from services.payment_service import criar_cobranca_pix

    await query.edit_message_text(
        "⏳ Gerando cobrança Pix...",
        parse_mode="Markdown",
    )

    cobranca = await criar_cobranca_pix(
        telegram_id=telegram_id,
        meses=meses,
    )

    if not cobranca:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                "❌ Erro ao gerar o Pix. Tente novamente em alguns "
                "segundos ou entre em contato.\n\n"
                "Use /premium para tentar novamente."
            ),
        )
        return

    qr_code = cobranca["qr_code"]
    valor = cobranca["valor"]

    msg = (
        f"💳 **PIX Gerado — R${valor:.2f}**\n\n"
        f"📋 **Copia e Cola (Pix):**\n"
        f"`{qr_code}`\n\n"
        "📱 **Como pagar:**\n"
        "1️⃣ Abra seu banco/app de pagamento\n"
        "2️⃣ Escolha **Pix Copia e Cola**\n"
        "3️⃣ Cole o código acima e confirme\n\n"
        "⏰ _O Pix expira em 24 horas._\n\n"
        "✅ Assim que pagar, seu Premium é ativado "
        "**automaticamente** em até 5 minutos!\n\n"
        "🔍 /verificarpix — Verificar pagamento"
    )

    # Salvar payment_id para verificação posterior
    context.user_data["ultimo_payment_id"] = str(cobranca["payment_id"])

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=msg,
        parse_mode="Markdown",
    )


async def premium_verificar_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Verifica pagamento pendente via callback."""
    query = update.callback_query
    await query.answer("Verificando...")
    await _verificar_pagamento(
        query.from_user.id, query.message.chat_id, context
    )


async def verificar_pix_cmd(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """/verificarpix — Verifica se o Pix foi pago."""
    await _verificar_pagamento(
        update.effective_user.id, update.effective_chat.id, context
    )


async def _verificar_pagamento(
    telegram_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE
):
    """Lógica compartilhada de verificação de pagamento."""
    from services.payment_service import (
        ativar_premium,
        atualizar_status_pagamento,
        get_pagamentos_pendentes,
        verificar_pagamento,
    )

    if not MERCADOPAGO_ACCESS_TOKEN:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "⚙️ Verificação automática não disponível ainda.\n"
                "Envie seu comprovante e ativaremos manualmente! 📩"
            ),
        )
        return

    from database.db import get_db

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM pagamentos "
            "WHERE telegram_id = ? AND status = 'pending' "
            "ORDER BY criado_em DESC LIMIT 1",
            (telegram_id,),
        )
        row = await cursor.fetchone()
    finally:
        await db.close()

    if not row:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "ℹ️ Nenhum pagamento pendente encontrado.\n\n"
                "Use /premium para gerar um novo Pix."
            ),
        )
        return

    pag = dict(row)
    payment_id = pag["external_id"]

    status = await verificar_pagamento(payment_id)

    if status == "approved":
        await atualizar_status_pagamento(payment_id, "approved")

        # Extrair meses da referência (fallback: 1 mês)
        meses = 1
        await ativar_premium(telegram_id, meses)

        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "🎉🎉🎉 **PAGAMENTO CONFIRMADO!** 🎉🎉🎉\n\n"
                "💎 Seu **Premium** está ATIVO!\n\n"
                "Agora você tem acesso a:\n"
                "• ♾️ Consultas ilimitadas\n"
                "• 💼 Carteira completa\n"
                "• 📊 Todos os relatórios\n"
                "• 🔔 Todos os alertas\n\n"
                "Comece agora:\n"
                "📈 /oquefazer — O que comprar hoje\n"
                "📝 /comprei — Registrar compra\n"
                "📊 /painel — Dashboard completo\n\n"
                "Obrigado por apoiar o FinançasIA! 🚀"
            ),
            parse_mode="Markdown",
        )

        # XP por assinar premium
        from services.gamification_service import add_xp

        await add_xp(telegram_id, "assinar_premium")

    elif status == "pending":
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "⏳ **Pagamento ainda pendente.**\n\n"
                "O Pix pode levar até 5 minutos para ser confirmado.\n"
                "Verifique se completou o pagamento no seu banco.\n\n"
                "🔍 /verificarpix — Verificar novamente"
            ),
            parse_mode="Markdown",
        )

    elif status in ("rejected", "cancelled"):
        await atualizar_status_pagamento(payment_id, status)
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "❌ **Pagamento não aprovado.**\n\n"
                "O pagamento foi rejeitado ou cancelado.\n"
                "Use /premium para gerar um novo Pix."
            ),
            parse_mode="Markdown",
        )

    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "⚠️ Não consegui verificar o status agora.\n"
                "Tente novamente em alguns segundos.\n\n"
                "🔍 /verificarpix"
            ),
        )


def get_premium_handlers() -> list:
    """Retorna os handlers do premium."""
    return [
        CommandHandler("premium", premium),
        CommandHandler("verificarpix", verificar_pix_cmd),
        CommandHandler("meupremium", verificar_pix_cmd),
        CallbackQueryHandler(premium_pix, pattern=r"^premium_pix_\d+$"),
        CallbackQueryHandler(
            premium_verificar_callback, pattern="^premium_verificar$"
        ),
    ]
