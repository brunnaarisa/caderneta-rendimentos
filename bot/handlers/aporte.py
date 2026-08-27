"""
Handler do /aporte — plano de investimento mensal automático.

O mais próximo de "investir pra mim" que o bot consegue:
configura valor e dia do salário, e no dia certo o bot avisa
EXATAMENTE o que comprar, com análise de mercado ao vivo
e passo a passo de como executar cada compra.
"""

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

from services.aporte_service import get_plano_mensal, salvar_plano_mensal, toggle_plano
from services.user_service import get_or_create_user

logger = logging.getLogger(__name__)

# Estados da conversa
AP_VALOR, AP_DIA, AP_PERFIL = range(3)

# Retornos estimados por perfil (a.a.) para simulação
RETORNOS_ESTIMADOS = {
    "conservador": {"min": 0.09, "med": 0.11, "max": 0.13},
    "moderado": {"min": 0.10, "med": 0.14, "max": 0.18},
    "arrojado": {"min": 0.10, "med": 0.17, "max": 0.25},
    "agressivo": {"min": 0.08, "med": 0.20, "max": 0.35},
}


# ── /aporte — Configurar plano mensal ─────────────────────────


async def aporte_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia configuração do plano mensal."""
    telegram_id = update.effective_user.id
    plano = await get_plano_mensal(telegram_id)

    if plano and plano.get("ativo"):
        emoji = {
            "conservador": "🛡️",
            "moderado": "⚖️",
            "arrojado": "📈",
            "agressivo": "🚀",
        }
        perfil = plano["perfil_risco"]
        await update.message.reply_text(
            f"📋 **Seu plano mensal atual:**\n\n"
            f"💰 Valor: **R${plano['valor_mensal']:,.2f}**/mês\n"
            f"📅 Dia do aporte: **dia {plano['dia_pagamento']}**\n"
            f"🎯 Perfil: {emoji.get(perfil, '')} **{perfil.title()}**\n\n"
            f"Quer alterar? Digite o novo valor mensal.\n"
            f"Ou /cancelar para manter como está.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "💰 **Plano de Aporte Mensal — Investimento no Automático**\n\n"
            "Vou fazer o trabalho pesado por você:\n\n"
            "📅 No dia do seu salário, te aviso **exatamente** o que comprar\n"
            "📊 Analiso o mercado **em tempo real** antes de sugerir\n"
            "📱 Digo **passo a passo** como executar cada compra\n"
            "✅ Com um toque você registra que comprou\n\n"
            "É o mais próximo de investir no automático! 🚀\n\n"
            "**Quanto você pode investir por mês?**\n"
            "_(Digite o valor, ex: 200, 500, 1000)_",
            parse_mode="Markdown",
        )
    return AP_VALOR


async def receber_valor_aporte(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Recebe o valor mensal."""
    try:
        valor = float(
            update.message.text.replace("R$", "")
            .replace(".", "")
            .replace(",", ".")
            .strip()
        )
        if valor < 30:
            await update.message.reply_text(
                "O valor mínimo recomendado é R$30/mês. Quanto pode investir?"
            )
            return AP_VALOR
    except (ValueError, AttributeError):
        await update.message.reply_text(
            "❌ Valor inválido. Digite um número, ex: **500**",
            parse_mode="Markdown",
        )
        return AP_VALOR

    context.user_data["aporte_valor"] = valor

    await update.message.reply_text(
        f"✅ Valor: **R${valor:,.2f}/mês**\n\n"
        "📅 **Qual dia do mês cai seu salário?**\n"
        "_(Vou te avisar nesse dia o que comprar)_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Dia 1", callback_data="apdia_1"),
                    InlineKeyboardButton("Dia 5", callback_data="apdia_5"),
                    InlineKeyboardButton("Dia 10", callback_data="apdia_10"),
                ],
                [
                    InlineKeyboardButton("Dia 15", callback_data="apdia_15"),
                    InlineKeyboardButton("Dia 20", callback_data="apdia_20"),
                    InlineKeyboardButton("Dia 25", callback_data="apdia_25"),
                ],
                [
                    InlineKeyboardButton(
                        "Último dia do mês", callback_data="apdia_28"
                    )
                ],
            ]
        ),
    )
    return AP_DIA


async def receber_dia_aporte(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Recebe o dia de pagamento."""
    query = update.callback_query
    await query.answer()

    dia = int(query.data.replace("apdia_", ""))
    context.user_data["aporte_dia"] = dia

    # Verificar se já tem perfil salvo
    user = await get_or_create_user(query.from_user.id)
    perfil_json = json.loads(user.get("perfil_json", "{}") or "{}")
    perfil_salvo = perfil_json.get("perfil_risco")

    if perfil_salvo:
        context.user_data["aporte_perfil"] = perfil_salvo.lower()
        return await _salvar_plano(query, context)

    await query.edit_message_text(
        f"📅 Dia do aporte: **dia {dia}**\n\n"
        "Qual nível de risco você aceita?\n"
        "_(Define a proporção entre renda fixa e variável)_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🛡️ Conservador — máxima segurança",
                        callback_data="apperfil_conservador",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⚖️ Moderado — equilíbrio",
                        callback_data="apperfil_moderado",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "📈 Arrojado — aceita oscilações",
                        callback_data="apperfil_arrojado",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🚀 Agressivo — busca retornos altos",
                        callback_data="apperfil_agressivo",
                    )
                ],
            ]
        ),
    )
    return AP_PERFIL


async def receber_perfil_aporte(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Recebe o perfil de risco."""
    query = update.callback_query
    await query.answer()

    perfil = query.data.replace("apperfil_", "")
    context.user_data["aporte_perfil"] = perfil
    return await _salvar_plano(query, context)


async def _salvar_plano(query, context):
    """Salva o plano e confirma com simulação de futuro."""
    telegram_id = query.from_user.id
    valor = context.user_data["aporte_valor"]
    dia = context.user_data["aporte_dia"]
    perfil = context.user_data["aporte_perfil"]

    await salvar_plano_mensal(telegram_id, valor, dia, perfil)

    emoji = {
        "conservador": "🛡️",
        "moderado": "⚖️",
        "arrojado": "📈",
        "agressivo": "🚀",
    }

    # Simular futuro para motivar
    retornos = RETORNOS_ESTIMADOS.get(perfil, RETORNOS_ESTIMADOS["moderado"])
    r_mensal = (1 + retornos["med"]) ** (1 / 12) - 1

    fv_1a = _fv_aportes(valor, r_mensal, 12)
    fv_3a = _fv_aportes(valor, r_mensal, 36)
    fv_5a = _fv_aportes(valor, r_mensal, 60)
    fv_10a = _fv_aportes(valor, r_mensal, 120)

    investido_5a = valor * 60
    lucro_5a = fv_5a - investido_5a

    await query.edit_message_text(
        f"✅ **Plano mensal ativado!**\n\n"
        f"💰 Valor: **R${valor:,.2f}/mês**\n"
        f"📅 Dia do aporte: **dia {dia}**\n"
        f"🎯 Perfil: {emoji.get(perfil, '')} **{perfil.title()}**\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"📈 **Projeção do seu patrimônio:**\n"
        f"  📅 1 ano: ~R${fv_1a:,.0f}\n"
        f"  📅 3 anos: ~R${fv_3a:,.0f}\n"
        f"  📅 5 anos: ~R${fv_5a:,.0f} "
        f"(R${lucro_5a:,.0f} só de rendimento!)\n"
        f"  📅 10 anos: ~R${fv_10a:,.0f}\n"
        f"  _(estimativa com retorno médio de "
        f"{retornos['med']*100:.0f}% a.a.)_\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"A partir de agora, todo **dia {dia}** eu vou te mandar:\n"
        f"✅ Exatamente o que comprar com R${valor:,.2f}\n"
        f"📊 Análise de mercado de cada ativo\n"
        f"📱 Passo a passo de COMO comprar\n"
        f"🔘 Botão para registrar com 1 toque\n\n"
        f"É só seguir as instruções! 🚀",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


def _fv_aportes(pmt: float, r: float, n: int) -> float:
    """Valor futuro de aportes mensais constantes."""
    if r == 0:
        return pmt * n
    return pmt * ((1 + r) ** n - 1) / r


# ── /meuplano — Ver plano atual ──────────────────────────────


async def ver_plano(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o plano mensal atual."""
    telegram_id = update.effective_user.id
    plano = await get_plano_mensal(telegram_id)

    if not plano:
        await update.message.reply_text(
            "Você ainda não tem um plano mensal.\n"
            "Use /aporte para configurar! 💰"
        )
        return

    emoji = {
        "conservador": "🛡️",
        "moderado": "⚖️",
        "arrojado": "📈",
        "agressivo": "🚀",
    }
    perfil = plano["perfil_risco"]

    await update.message.reply_text(
        f"📋 **Seu Plano Mensal de Investimento**\n\n"
        f"💰 Valor: **R${plano['valor_mensal']:,.2f}/mês**\n"
        f"📅 Dia do aporte: **dia {plano['dia_pagamento']}**\n"
        f"🎯 Perfil: {emoji.get(perfil, '')} **{perfil.title()}**\n"
        f"📊 Status: {'✅ Ativo' if plano['ativo'] else '⏸️ Pausado'}\n\n"
        f"💡 /aporte — Alterar plano\n"
        f"⏸️ /pausaraporte — Pausar\n"
        f"📈 /simular — Projetar patrimônio futuro\n"
        f"📋 /oquefazer — Simular com valor diferente",
        parse_mode="Markdown",
    )


# ── /pausaraporte — Pausar plano ─────────────────────────────


async def pausar_aporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pausa o plano mensal."""
    await toggle_plano(update.effective_user.id, ativo=False)
    await update.message.reply_text(
        "⏸️ Plano de aporte mensal **pausado**.\n\n"
        "Você não receberá lembretes mensais.\n"
        "Para reativar: /aporte",
        parse_mode="Markdown",
    )


# ── /simular — Simulação de patrimônio futuro ────────────────


async def simular(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simula o crescimento do patrimônio com aportes mensais."""
    telegram_id = update.effective_user.id
    plano = await get_plano_mensal(telegram_id)

    # Tentar pegar valor dos args ou do plano
    valor = None
    perfil = "moderado"

    if context.args:
        try:
            valor = float(
                context.args[0]
                .replace("R$", "")
                .replace(".", "")
                .replace(",", ".")
            )
        except ValueError:
            pass

    if not valor and plano:
        valor = plano["valor_mensal"]
        perfil = plano["perfil_risco"]
    elif not valor:
        await update.message.reply_text(
            "📈 **Simulador de Patrimônio**\n\n"
            "Use:\n"
            "/simular **500** — Simular com R$500/mês\n"
            "/simular **1000** — Simular com R$1.000/mês\n\n"
            "Ou configure /aporte para que eu use seu valor mensal.",
            parse_mode="Markdown",
        )
        return

    if plano:
        perfil = plano["perfil_risco"]

    retornos = RETORNOS_ESTIMADOS.get(perfil, RETORNOS_ESTIMADOS["moderado"])
    emoji = {
        "conservador": "🛡️",
        "moderado": "⚖️",
        "arrojado": "📈",
        "agressivo": "🚀",
    }

    # Cenário pessimista, médio e otimista
    cenarios = [
        ("😐 Pessimista", retornos["min"]),
        ("📊 Esperado", retornos["med"]),
        ("🚀 Otimista", retornos["max"]),
    ]

    msg = (
        f"📈 **Simulação de Patrimônio**\n\n"
        f"💰 Aporte: **R${valor:,.2f}/mês**\n"
        f"🎯 Perfil: {emoji.get(perfil, '')} {perfil.title()}\n\n"
    )

    for nome_cenario, taxa in cenarios:
        r_mensal = (1 + taxa) ** (1 / 12) - 1
        fv_1 = _fv_aportes(valor, r_mensal, 12)
        fv_3 = _fv_aportes(valor, r_mensal, 36)
        fv_5 = _fv_aportes(valor, r_mensal, 60)
        fv_10 = _fv_aportes(valor, r_mensal, 120)
        fv_20 = _fv_aportes(valor, r_mensal, 240)

        msg += (
            f"**{nome_cenario}** ({taxa*100:.0f}% a.a.):\n"
            f"  1 ano: R${fv_1:,.0f}\n"
            f"  3 anos: R${fv_3:,.0f}\n"
            f"  5 anos: R${fv_5:,.0f}\n"
            f"  10 anos: R${fv_10:,.0f}\n"
            f"  20 anos: R${fv_20:,.0f}\n\n"
        )

    investido_10a = valor * 120
    lucro_medio_10a = _fv_aportes(
        valor, (1 + retornos["med"]) ** (1 / 12) - 1, 120
    ) - investido_10a

    msg += (
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💡 Em 10 anos, você terá investido **R${investido_10a:,.0f}**.\n"
        f"No cenário esperado, só de rendimento seriam "
        f"**R${lucro_medio_10a:,.0f}** — seu dinheiro trabalhando por você!\n\n"
    )

    # Comparação com quem não investe
    sem_investir = valor * 120  # debaixo do colchão
    msg += (
        f"📌 Se guardar debaixo do colchão: R${sem_investir:,.0f}\n"
        f"📌 Se investir com disciplina: ~R${_fv_aportes(valor, (1 + retornos['med']) ** (1/12) - 1, 120):,.0f}\n\n"
        f"**A diferença é de R${lucro_medio_10a:,.0f}!** 🤯\n\n"
        f"🔑 O segredo é **começar e não parar**.\n"
        f"💰 /aporte — Configurar aporte mensal automático"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")


# ── Cancelar ─────────────────────────────────────────────────


async def cancel_aporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Cancelado. Use /aporte para configurar."
    )
    return ConversationHandler.END


# ── Handlers ─────────────────────────────────────────────────


def get_aporte_handlers() -> list:
    """Retorna os handlers do plano mensal."""
    conv = ConversationHandler(
        entry_points=[CommandHandler("aporte", aporte_start)],
        states={
            AP_VALOR: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, receber_valor_aporte
                )
            ],
            AP_DIA: [
                CallbackQueryHandler(receber_dia_aporte, pattern=r"^apdia_")
            ],
            AP_PERFIL: [
                CallbackQueryHandler(
                    receber_perfil_aporte, pattern=r"^apperfil_"
                )
            ],
        },
        fallbacks=[CommandHandler("cancelar", cancel_aporte)],
    )
    return [
        conv,
        CommandHandler("meuplano", ver_plano),
        CommandHandler("pausaraporte", pausar_aporte),
        CommandHandler("simular", simular),
    ]
