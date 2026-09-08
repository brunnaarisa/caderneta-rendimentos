"""Handler do /perfil — descobre o perfil de risco do investidor."""

import json
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)

from services.user_service import get_or_create_user, update_profile

logger = logging.getLogger(__name__)

# Estados
P1, P2, P3, P4, P5 = range(5)

# Perguntas do questionário suitability (inspirado em CVM/ANBIMA)
PERGUNTAS = [
    {
        "texto": (
            "🧠 **Teste de Perfil de Investidor**\n\n"
            "Pergunta 1/5:\n"
            "Imagine que você investiu R$1.000 e em 1 mês **perdeu R$200** "
            "(caiu 20%). O que você faz?"
        ),
        "opcoes": [
            ("😰 Tiro tudo na hora!", "risco_1_a"),
            ("😟 Tiro metade por segurança", "risco_1_b"),
            ("🤔 Espero recuperar", "risco_1_c"),
            ("🤑 Coloco mais dinheiro!", "risco_1_d"),
        ],
        "pontos": {"risco_1_a": 1, "risco_1_b": 2, "risco_1_c": 3, "risco_1_d": 4},
    },
    {
        "texto": (
            "Pergunta 2/5:\n"
            "Você precisa do dinheiro investido em quanto tempo?"
        ),
        "opcoes": [
            ("📅 Menos de 6 meses", "risco_2_a"),
            ("📅 6 meses a 1 ano", "risco_2_b"),
            ("📅 1 a 3 anos", "risco_2_c"),
            ("📅 Mais de 3 anos", "risco_2_d"),
        ],
        "pontos": {"risco_2_a": 1, "risco_2_b": 2, "risco_2_c": 3, "risco_2_d": 4},
    },
    {
        "texto": (
            "Pergunta 3/5:\n"
            "Qual frase mais combina com você?"
        ),
        "opcoes": [
            ("🛡️ Prefiro ganhar pouco mas nunca perder", "risco_3_a"),
            ("⚖️ Aceito pequenas perdas por mais ganho", "risco_3_b"),
            ("📈 Aceito perdas médias por ganhos maiores", "risco_3_c"),
            ("🚀 Aceito perdas grandes por chances de ganho alto", "risco_3_d"),
        ],
        "pontos": {"risco_3_a": 1, "risco_3_b": 2, "risco_3_c": 3, "risco_3_d": 4},
    },
    {
        "texto": (
            "Pergunta 4/5:\n"
            "Qual desses investimentos você JÁ fez ou faria sem medo?"
        ),
        "opcoes": [
            ("🏦 Poupança / CDB", "risco_4_a"),
            ("📊 Tesouro Direto / Fundos", "risco_4_b"),
            ("🏢 Ações / Fundos Imobiliários", "risco_4_c"),
            ("₿ Cripto / Day Trade / Opções", "risco_4_d"),
        ],
        "pontos": {"risco_4_a": 1, "risco_4_b": 2, "risco_4_c": 3, "risco_4_d": 4},
    },
    {
        "texto": (
            "Pergunta 5/5:\n"
            "Você tem uma **reserva de emergência** (3-6 meses de gastos guardados)?"
        ),
        "opcoes": [
            ("❌ Não tenho nada guardado", "risco_5_a"),
            ("😬 Tenho menos de 3 meses", "risco_5_b"),
            ("✅ Tenho 3 a 6 meses", "risco_5_c"),
            ("💪 Tenho mais de 6 meses", "risco_5_d"),
        ],
        "pontos": {"risco_5_a": 0, "risco_5_b": 1, "risco_5_c": 3, "risco_5_d": 4},
    },
]


def _calcular_perfil(pontuacao: int) -> dict:
    """Determina o perfil com base na pontuação total (0-20)."""
    if pontuacao <= 6:
        return {
            "nome": "Conservador",
            "emoji": "🛡️",
            "descricao": (
                "Você prioriza segurança. Prefere ganhar menos "
                "mas dormir tranquilo sabendo que seu dinheiro está protegido."
            ),
        }
    elif pontuacao <= 10:
        return {
            "nome": "Moderado",
            "emoji": "⚖️",
            "descricao": (
                "Você aceita um pouco de risco em troca de retornos "
                "melhores. Quer equilíbrio entre segurança e crescimento."
            ),
        }
    elif pontuacao <= 15:
        return {
            "nome": "Arrojado",
            "emoji": "📈",
            "descricao": (
                "Você aceita oscilações e possíveis perdas temporárias "
                "em busca de retornos acima da média no médio/longo prazo."
            ),
        }
    else:
        return {
            "nome": "Agressivo",
            "emoji": "🚀",
            "descricao": (
                "Você busca retornos altos e aceita riscos elevados. "
                "Entende que pode perder parte significativa do investimento."
            ),
        }


async def perfil_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia o questionário de perfil de risco."""
    context.user_data["risco_pontos"] = 0

    botoes = [
        [InlineKeyboardButton(texto, callback_data=cb)]
        for texto, cb in PERGUNTAS[0]["opcoes"]
    ]

    await update.message.reply_text(
        PERGUNTAS[0]["texto"],
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(botoes),
    )
    return P1


async def _handle_resposta(
    update: Update, context: ContextTypes.DEFAULT_TYPE, pergunta_idx: int
):
    """Processa uma resposta e mostra a próxima pergunta (ou resultado)."""
    query = update.callback_query
    await query.answer()

    # Somar pontos
    pontos = PERGUNTAS[pergunta_idx]["pontos"].get(query.data, 0)
    context.user_data["risco_pontos"] = (
        context.user_data.get("risco_pontos", 0) + pontos
    )

    prox = pergunta_idx + 1

    # Se ainda tem perguntas
    if prox < len(PERGUNTAS):
        botoes = [
            [InlineKeyboardButton(texto, callback_data=cb)]
            for texto, cb in PERGUNTAS[prox]["opcoes"]
        ]
        await query.edit_message_text(
            PERGUNTAS[prox]["texto"],
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(botoes),
        )
        return prox  # próximo estado

    # Acabou — calcular resultado
    total = context.user_data["risco_pontos"]
    perfil = _calcular_perfil(total)

    # Salvar no banco
    telegram_id = query.from_user.id
    user = await get_or_create_user(telegram_id)
    perfil_json = json.loads(user.get("perfil_json", "{}") or "{}")
    perfil_json["perfil_risco"] = perfil["nome"]
    perfil_json["risco_pontuacao"] = total
    await update_profile(telegram_id, perfil_json=json.dumps(perfil_json))

    await query.edit_message_text(
        f"🎯 **Seu Perfil de Investidor**\n\n"
        f"{perfil['emoji']} **{perfil['nome']}** (pontuação: {total}/20)\n\n"
        f"{perfil['descricao']}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "Agora use /sugestoes para ver investimentos "
        "recomendados para o seu perfil! 🎯\n\n"
        "Quer refazer? Use /perfil novamente.",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def resp_p1(update, context):
    return await _handle_resposta(update, context, 0)


async def resp_p2(update, context):
    return await _handle_resposta(update, context, 1)


async def resp_p3(update, context):
    return await _handle_resposta(update, context, 2)


async def resp_p4(update, context):
    return await _handle_resposta(update, context, 3)


async def resp_p5(update, context):
    return await _handle_resposta(update, context, 4)


async def cancel_perfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Teste cancelado. Use /perfil para recomeçar.")
    return ConversationHandler.END


def get_perfil_risco_handler() -> ConversationHandler:
    """Retorna o ConversationHandler do questionário de perfil."""
    return ConversationHandler(
        entry_points=[CommandHandler("perfil", perfil_start)],
        states={
            P1: [CallbackQueryHandler(resp_p1, pattern="^risco_1_")],
            P2: [CallbackQueryHandler(resp_p2, pattern="^risco_2_")],
            P3: [CallbackQueryHandler(resp_p3, pattern="^risco_3_")],
            P4: [CallbackQueryHandler(resp_p4, pattern="^risco_4_")],
            P5: [CallbackQueryHandler(resp_p5, pattern="^risco_5_")],
        },
        fallbacks=[CommandHandler("cancel", cancel_perfil)],
    )
