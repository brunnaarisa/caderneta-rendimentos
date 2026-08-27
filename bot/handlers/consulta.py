"""Handler de consultas à IA — o coração do bot."""

import logging

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from config import FREE_DAILY_LIMIT, PREMIUM_PRICE
from services.ai_advisor import consultar_ia
from services.user_service import (
    check_and_use_consulta,
    get_financial_context,
    get_or_create_user,
    get_remaining_consultas,
)

logger = logging.getLogger(__name__)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Processa qualquer mensagem de texto que não seja um comando.
    Funciona como a interface principal com a IA.
    """
    if not update.message or not update.message.text:
        return

    telegram_id = update.effective_user.id
    pergunta = update.message.text.strip()

    if len(pergunta) < 3:
        await update.message.reply_text(
            "Pode elaborar melhor sua pergunta? 😊"
        )
        return

    # Verificar limite de consultas
    pode_consultar = await check_and_use_consulta(telegram_id, FREE_DAILY_LIMIT)

    if not pode_consultar:
        await update.message.reply_text(
            f"😕 Você atingiu o limite de **{FREE_DAILY_LIMIT} consultas grátis** "
            f"por dia.\n\n"
            f"💎 Com o **Premium** (R${PREMIUM_PRICE:.2f}/mês) você tem:\n"
            "• Consultas ilimitadas com a IA\n"
            "• Registro de gastos\n"
            "• Plano financeiro personalizado\n"
            "• Relatórios semanais\n"
            "• E muito mais!\n\n"
            "Use /premium para assinar 🚀",
            parse_mode="Markdown",
        )
        return

    # Indicar que está "digitando"
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    # Buscar contexto financeiro do usuário
    contexto = await get_financial_context(telegram_id)

    # Consultar a IA
    resposta = await consultar_ia(pergunta, contexto)

    # Mostrar quantas consultas restam (só para free)
    restantes = await get_remaining_consultas(telegram_id, FREE_DAILY_LIMIT)
    rodape = ""
    if restantes is not None and restantes <= FREE_DAILY_LIMIT:
        if restantes == 0:
            rodape = f"\n\n---\n_Última consulta grátis de hoje. /premium para ilimitado._"
        else:
            rodape = f"\n\n---\n_{restantes}/{FREE_DAILY_LIMIT} consultas grátis restantes hoje._"

    await update.message.reply_text(
        resposta + rodape,
        parse_mode="Markdown",
    )


async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler do /ajuda — lista todos os comandos."""
    await update.message.reply_text(
        "🤖 **FinançasIA — Comandos disponíveis**\n\n"
        "💬 **Consultar a IA:**\n"
        "Simplesmente me envie uma mensagem com sua dúvida!\n"
        'Ex: "Onde rende mais, Nubank ou PicPay?"\n'
        'Ex: "Tenho R$5000, onde investir?"\n'
        'Ex: "O que é CDI?"\n\n'
        "🎓 **Aprender do zero:**\n"
        "/aprender — Aulas passo a passo (do zero mesmo!)\n\n"
        "📊 **Investimentos:**\n"
        "/oquefazer — 🔥 Me diz o valor e eu digo O QUE comprar\n"
        "/investir — Calcular rendimento de um investimento\n"
        "/comparar — Comparar bancos/corretoras\n"
        "/perfil — Descobrir seu perfil de investidor\n"
        "/sugestoes — Ver investimentos para o seu perfil\n\n"
        "💸 **Controle de gastos:**\n"
        "/gasto — Registrar um gasto\n"
        "/resumo — Ver resumo dos gastos do mês\n\n"
        "💳 **Dívidas:**\n"
        "/dividas — Ver/cadastrar dívidas\n"
        "/estrategia — Plano para quitar dívidas\n\n"
        "🎯 **Metas:**\n"
        "/meta — Criar uma meta financeira\n"
        "/metas — Ver suas metas\n\n"
        "⚙️ **Outros:**\n"
        "/premium — Ver plano premium\n"
        "/perfil — Atualizar seu perfil\n"
        "/start — Recomeçar o onboarding\n"
        "/ajuda — Esta mensagem\n",
        parse_mode="Markdown",
    )


def get_consulta_handlers() -> list:
    """Retorna os handlers de consulta."""
    from telegram.ext import CommandHandler

    return [
        CommandHandler("ajuda", ajuda),
        CommandHandler("help", ajuda),
        # Este deve ser adicionado por último (pega qualquer texto)
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message),
    ]
