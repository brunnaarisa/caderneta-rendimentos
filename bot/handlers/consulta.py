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
        "Envie uma mensagem com qualquer dúvida financeira!\n\n"
        "🎓 **Aprender do zero:**\n"
        "/aprender — Aulas passo a passo (do zero mesmo!)\n"
        "/comocomprar — 📖 Como comprar cada tipo de ativo\n\n"
        "📊 **Investimentos:**\n"
        "/oquefazer — 🔥 Digo O QUE comprar com análise ao vivo\n"
        "/desafio — 🎯 \"Quero ganhar X investindo Y em Z tempo\"\n"
        "/analisar [ativo] — 📈 Análise de mercado em tempo real\n"
        "/simular — 📈 Projeção de patrimônio futuro\n"
        "/investir — Calcular rendimento\n"
        "/comparar — Comparar bancos/corretoras\n"
        "/perfil — Seu perfil de investidor\n"
        "/sugestoes — Investimentos para o seu perfil\n\n"
        "🤖 **Investimento automático:**\n"
        "/aporte — 🚀 Plano mensal (aviso o que comprar no dia do salário!)\n"
        "/meuplano — Ver seu plano mensal\n"
        "/pausaraporte — Pausar lembretes\n\n"
        "💼 **Carteira:**\n"
        "/comprei — Registrar uma compra\n"
        "/carteira — Posições com lucro/prejuízo ao vivo\n"
        "/alertas — Notificações automáticas de venda/compra\n\n"
        "💸 **Controle de gastos:**\n"
        "/gasto — Registrar um gasto\n"
        "/resumo — Resumo dos gastos do mês\n\n"
        "💳 **Dívidas:**\n"
        "/dividas — Ver/cadastrar dívidas\n"
        "/estrategia — Plano para quitar dívidas\n\n"
        "🎯 **Metas:**\n"
        "/meta — Criar uma meta financeira\n"
        "/metas — Ver suas metas\n\n"
        "🛠️ **Ferramentas:**\n"
        "/painel — 📊 Dashboard financeiro completo\n"
        "/versus — ⚔️ Comparar dois ativos ao vivo\n"
        "/aposentar — 🏖️ Calculadora de independência financeira\n"
        "/dicadodia — 💡 Dica financeira do dia\n\n"
        "⚙️ **Outros:**\n"
        "/premium — Plano premium\n"
        "/start — Recomeçar\n"
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
