"""Handler do /start — onboarding do usuário."""

import json
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

from services.user_service import get_or_create_user, update_profile

logger = logging.getLogger(__name__)

# Estados da conversa de onboarding
PERGUNTA_OBJETIVO, PERGUNTA_RENDA, PERGUNTA_CONHECIMENTO = range(3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mensagem de boas-vindas e início do onboarding."""
    user = update.effective_user
    await get_or_create_user(user.id, user.first_name)

    # Processar indicação (ref_XXXXX)
    if context.args and context.args[0].startswith("ref_"):
        try:
            referrer_id = int(context.args[0].replace("ref_", ""))
            from handlers.gamificacao import processar_indicacao

            bonus_msg = await processar_indicacao(referrer_id, user.id)
            if bonus_msg:
                await update.message.reply_text(
                    bonus_msg, parse_mode="Markdown"
                )
        except (ValueError, Exception) as e:
            logger.debug("Erro ao processar indicação: %s", e)

    await update.message.reply_text(
        f"Olá, {user.first_name}! 👋\n\n"
        "Eu sou o **FinançasIA** — seu assistente de educação "
        "financeira com inteligência artificial.\n\n"
        "Vou te ajudar a:\n"
        "💰 Organizar seus gastos\n"
        "📈 Estudar opções de investimento\n"
        "🎯 Alcançar seus objetivos financeiros\n"
        "💳 Sair de dívidas (se tiver)\n\n"
        "⚠️ _Conteúdo educacional — não somos consultores "
        "de investimentos certificados (CVM)._\n\n"
        "Para te ajudar melhor, quero te conhecer. "
        "Vamos lá? 😊\n\n"
        "**Qual seu principal objetivo financeiro agora?**",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🏦 Começar a investir", callback_data="obj_investir")],
                [InlineKeyboardButton("💳 Sair das dívidas", callback_data="obj_dividas")],
                [InlineKeyboardButton("🏠 Juntar para algo grande", callback_data="obj_juntar")],
                [InlineKeyboardButton("📊 Organizar meus gastos", callback_data="obj_organizar")],
                [InlineKeyboardButton("💡 Só quero aprender", callback_data="obj_aprender")],
            ]
        ),
    )
    return PERGUNTA_OBJETIVO


async def receber_objetivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe o objetivo e pergunta a renda."""
    query = update.callback_query
    await query.answer()

    objetivos = {
        "obj_investir": "Começar a investir",
        "obj_dividas": "Sair das dívidas",
        "obj_juntar": "Juntar para algo grande",
        "obj_organizar": "Organizar gastos",
        "obj_aprender": "Aprender sobre finanças",
    }

    objetivo = objetivos.get(query.data, "Não informado")
    context.user_data["objetivo"] = objetivo

    await query.edit_message_text(
        f"Ótimo! Seu objetivo: **{objetivo}** ✅\n\n"
        "Agora, qual sua **renda mensal aproximada**?\n"
        "(Pode ser o salário + outras rendas. Isso fica só entre nós! 🤫)",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Até R$1.500", callback_data="renda_1500")],
                [InlineKeyboardButton("R$1.500 – R$3.000", callback_data="renda_3000")],
                [InlineKeyboardButton("R$3.000 – R$5.000", callback_data="renda_5000")],
                [InlineKeyboardButton("R$5.000 – R$10.000", callback_data="renda_10000")],
                [InlineKeyboardButton("Acima de R$10.000", callback_data="renda_15000")],
                [InlineKeyboardButton("Prefiro não dizer", callback_data="renda_0")],
            ]
        ),
    )
    return PERGUNTA_RENDA


async def receber_renda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe a renda e pergunta o nível de conhecimento."""
    query = update.callback_query
    await query.answer()

    rendas = {
        "renda_1500": 1500,
        "renda_3000": 3000,
        "renda_5000": 5000,
        "renda_10000": 10000,
        "renda_15000": 15000,
        "renda_0": 0,
    }

    renda = rendas.get(query.data, 0)
    context.user_data["renda"] = renda

    await query.edit_message_text(
        "Entendi! 👍\n\n"
        "Última pergunta: como você avalia seu **conhecimento sobre finanças**?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🌱 Iniciante — sei pouco", callback_data="nivel_iniciante"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🌿 Intermediário — sei o básico",
                        callback_data="nivel_intermediario",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🌳 Avançado — já invisto",
                        callback_data="nivel_avancado",
                    )
                ],
            ]
        ),
    )
    return PERGUNTA_CONHECIMENTO


async def receber_conhecimento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe o nível de conhecimento e finaliza o onboarding."""
    query = update.callback_query
    await query.answer()

    niveis = {
        "nivel_iniciante": "Iniciante",
        "nivel_intermediario": "Intermediário",
        "nivel_avancado": "Avançado",
    }

    conhecimento = niveis.get(query.data, "Iniciante")
    objetivo = context.user_data.get("objetivo", "")
    renda = context.user_data.get("renda", 0)

    # Salvar no banco
    telegram_id = query.from_user.id
    perfil = json.dumps({"objetivo": objetivo, "conhecimento": conhecimento})

    await update_profile(telegram_id, renda_mensal=renda, perfil_json=perfil)

    # Montar mensagem de boas-vindas personalizada por objetivo
    blocos_objetivo = {
        "Começar a investir": (
            "🚀 **Comece por aqui:**\n"
            "1️⃣ /aprender — Curso do zero (não precisa saber nada!)\n"
            "2️⃣ /oquefazer — Estudo de alocação para seu perfil\n"
            "3️⃣ /aporte — Configuro lembrete mensal no dia do salário\n"
            "4️⃣ /comocomprar — Passo a passo educacional\n\n"
            "💡 _Depois de investir, use /comprei para acompanhar "
            "e receber alertas de variação!_"
        ),
        "Sair das dívidas": (
            "🚀 **Comece por aqui:**\n"
            "1️⃣ /dividas — Cadastre suas dívidas\n"
            "2️⃣ /estrategia — Estudo de estratégia para quitar tudo\n"
            "3️⃣ /gasto — Registre gastos para achar onde economizar\n"
            "4️⃣ /aprender — Aprenda a nunca mais se endividar\n\n"
            "💡 _Depois de quitar, use /aporte para começar a investir!_"
        ),
        "Juntar para algo grande": (
            "🚀 **Comece por aqui:**\n"
            "1️⃣ /meta — Crie sua meta (eu calculo quanto guardar/mês)\n"
            "2️⃣ /simular — Veja quanto terá em 1, 5, 10 anos\n"
            "3️⃣ /aporte — Configuro aviso mensal automático\n"
            "4️⃣ /oquefazer — Estudo de onde alocar o dinheiro da meta\n\n"
            "💡 _Use /painel para acompanhar tudo num só lugar!_"
        ),
        "Organizar gastos": (
            "🚀 **Comece por aqui:**\n"
            "1️⃣ /gasto — Registre seus gastos (leva 5 segundos)\n"
            "2️⃣ /resumo — Veja para onde vai seu dinheiro\n"
            "3️⃣ /painel — Dashboard completo da sua vida financeira\n"
            "4️⃣ /aporte — Sobrou? Configure investimento mensal\n\n"
            "💡 _Registre gastos todo dia — é o hábito que mais "
            "transforma suas finanças!_"
        ),
        "Aprender sobre finanças": (
            "🚀 **Comece por aqui:**\n"
            "1️⃣ /aprender — Curso completo do zero (aulas curtinhas)\n"
            "2️⃣ /dicadodia — Dica financeira todo dia\n"
            "3️⃣ /perfil — Descubra seu perfil de investidor\n"
            "4️⃣ Mande qualquer pergunta que eu respondo com IA!\n\n"
            "💡 _Exemplos: \"O que é CDI?\", \"Como funciona o IR?\", "
            "\"Bitcoin é seguro?\"_"
        ),
    }

    bloco = blocos_objetivo.get(
        objetivo,
        "🚀 **Comece por aqui:**\n"
        "1️⃣ /aprender — Curso do zero\n"
        "2️⃣ /oquefazer — Estudo de alocação\n"
        "3️⃣ /aporte — Lembrete de aporte mensal\n"
        "4️⃣ /ajuda — Ver todos os comandos\n",
    )

    await query.edit_message_text(
        "Pronto! Agora te conheço melhor 🎉\n\n"
        f"{bloco}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "📊 /painel — Dashboard financeiro\n"
        "🏖️ /aposentar — Quando posso parar de trabalhar?\n"
        "📖 /ajuda — Todos os comandos\n\n"
        "Ou simplesmente **me mande uma mensagem** com qualquer "
        "dúvida sobre finanças que eu respondo! 🧠",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela o onboarding."""
    await update.message.reply_text(
        "Tudo bem! Quando quiser começar, é só digitar /start 😊"
    )
    return ConversationHandler.END


def get_start_handler() -> ConversationHandler:
    """Retorna o ConversationHandler completo do onboarding."""
    return ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PERGUNTA_OBJETIVO: [
                CallbackQueryHandler(receber_objetivo, pattern="^obj_"),
            ],
            PERGUNTA_RENDA: [
                CallbackQueryHandler(receber_renda, pattern="^renda_"),
            ],
            PERGUNTA_CONHECIMENTO: [
                CallbackQueryHandler(receber_conhecimento, pattern="^nivel_"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
