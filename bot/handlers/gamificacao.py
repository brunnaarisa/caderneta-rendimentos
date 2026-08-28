"""
Handlers de gamificação, indicação e orçamento:
- /conquistas — Ver XP, nível, conquistas e streak
- /ranking — Ranking global dos usuários
- /indicar — Sistema de indicação com recompensas
- /orcamento — Orçamento mensal inteligente (50/30/20)
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

from config import FREE_DAILY_LIMIT
from services.gamification_service import (
    CONQUISTAS,
    NIVEIS,
    add_xp,
    aplicar_bonus_indicacao,
    desbloquear_conquista,
    get_info_nivel,
    get_or_create_gamificacao,
    get_or_create_orcamento,
    get_posicao_ranking,
    get_proximo_nivel,
    get_ranking,
    get_total_indicacoes,
    registrar_acesso_diario,
    registrar_indicacao,
    salvar_orcamento,
)
from services.user_service import get_or_create_user, get_resumo_gastos_mes

logger = logging.getLogger(__name__)


# ── /conquistas — Perfil de gamificação ────────────────────────


async def conquistas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra XP, nível, conquistas e streak do usuário."""
    telegram_id = update.effective_user.id

    # Registrar acesso diário (ganha XP de streak)
    streak_info = await registrar_acesso_diario(telegram_id)
    gami = await get_or_create_gamificacao(telegram_id)

    xp = gami["xp"]
    nivel = gami["nivel"]
    streak = gami["streak_dias"]
    maior_streak = gami["maior_streak"]
    conquistas_ids = json.loads(gami.get("conquistas", "[]") or "[]")

    # Info do nível
    nivel_info = await get_info_nivel(nivel)
    proximo = await get_proximo_nivel(nivel, xp)

    # Posição no ranking
    posicao = await get_posicao_ranking(telegram_id)

    msg = (
        f"{nivel_info['emoji']} **Nível {nivel} — {nivel_info['nome']}**\n\n"
        f"⭐ XP: **{xp:,}**"
    )

    if proximo:
        barra = _barra_xp(xp, nivel_info["xp_min"], proximo["xp_min"])
        msg += f"\n{barra}\n"
        msg += f"📈 Faltam **{proximo['xp_faltando']:,} XP** para {proximo['emoji']} {proximo['nome']}\n"
    else:
        msg += "\n🏆 **Nível máximo alcançado!**\n"

    msg += f"\n🏅 Ranking: **#{posicao}**\n"

    # Streak
    if streak > 0:
        fogo = "🔥" * min(streak, 7)
        msg += f"\n{fogo} **Streak: {streak} dias seguidos!**\n"
        if maior_streak > streak:
            msg += f"   Recorde: {maior_streak} dias\n"
    else:
        msg += "\n🔥 Acesse amanhã para começar um streak!\n"

    # Streak XP
    if streak_info.get("xp_streak", 0) > 0:
        msg += f"   +{streak_info['xp_streak']} XP de streak hoje\n"

    # Conquistas
    msg += f"\n━━━ 🏆 **CONQUISTAS** ({len(conquistas_ids)}/{len(CONQUISTAS)}) ━━━\n"

    for cid, cdata in CONQUISTAS.items():
        if cid in conquistas_ids:
            msg += f"✅ {cdata['emoji']} **{cdata['nome']}** — _{cdata['descricao']}_\n"
        else:
            msg += f"🔒 {cdata['emoji']} {cdata['nome']} — _{cdata['descricao']}_\n"

    # Próximas ações para ganhar XP
    msg += (
        "\n━━━━━━━━━━━━━━━━━━━\n"
        "💡 **Ganhe XP:**\n"
        "• Consulte a IA (+10 XP)\n"
        "• Registre gastos (+5 XP)\n"
        "• Compre ativos (+20 XP)\n"
        "• Indique amigos (+100 XP)\n"
        "• Use o bot todo dia (streak)\n\n"
        "🏅 /ranking — Ver ranking global\n"
        "🤝 /indicar — Convidar amigos"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")

    # Notificar conquistas novas (do streak)
    novas = streak_info.get("conquistas", [])
    if novas:
        for c in novas:
            await update.message.reply_text(
                f"🎉 **Nova conquista desbloqueada!**\n\n"
                f"{c['emoji']} **{c['nome']}**\n"
                f"_{c['descricao']}_",
                parse_mode="Markdown",
            )


def _barra_xp(xp: int, xp_nivel_atual: int, xp_proximo: int) -> str:
    """Gera barra de XP visual."""
    progresso = xp - xp_nivel_atual
    total = xp_proximo - xp_nivel_atual
    pct = min(100, max(0, progresso / total * 100)) if total > 0 else 100
    filled = int(pct / 5)
    return "▓" * filled + "░" * (20 - filled) + f" {pct:.0f}%"


# ── /ranking ───────────────────────────────────────────────────


async def ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o ranking global."""
    telegram_id = update.effective_user.id
    top = await get_ranking(10)
    posicao = await get_posicao_ranking(telegram_id)

    msg = "🏅 **Ranking FinançasIA**\n\n"

    medalhas = ["🥇", "🥈", "🥉"]
    for i, user in enumerate(top):
        medalha = medalhas[i] if i < 3 else f"#{i + 1}"
        nivel_info = await get_info_nivel(user["nivel"])
        nome = user.get("nome", "Investidor") or "Investidor"
        destaque = " ← você!" if user["telegram_id"] == telegram_id else ""

        msg += (
            f"{medalha} {nivel_info['emoji']} **{nome}** "
            f"— {user['xp']:,} XP (Nv.{user['nivel']})"
            f"{destaque}\n"
        )

    if not top:
        msg += "_Nenhum usuário ainda. Seja o primeiro!_\n"

    msg += f"\n📊 Sua posição: **#{posicao}**\n"

    msg += (
        "\n━━━━━━━━━━━━━━━━━━━\n"
        "🏆 /conquistas — Suas conquistas\n"
        "🤝 /indicar — Subir no ranking mais rápido"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")


# ── /indicar — Sistema de indicação ────────────────────────────


async def indicar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o link de indicação e estatísticas."""
    telegram_id = update.effective_user.id
    bot_info = await context.bot.get_me()
    bot_username = bot_info.username

    total = await get_total_indicacoes(telegram_id)

    link = f"https://t.me/{bot_username}?start=ref_{telegram_id}"

    msg = (
        "🤝 **Indique e Ganhe!**\n\n"
        "Cada amigo que entrar pelo seu link:\n"
        f"• 📩 Você ganha **+{FREE_DAILY_LIMIT} consultas grátis extras**\n"
        "• ⭐ Você ganha **+100 XP**\n"
        f"• 📩 Seu amigo ganha **+{FREE_DAILY_LIMIT} consultas grátis extras**\n\n"
        f"📊 **Suas indicações:** {total}\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔗 **Seu link exclusivo:**\n"
        f"`{link}`\n\n"
        "_Compartilhe com amigos, família e grupos!_\n\n"
    )

    # Mensagem pronta para compartilhar
    msg += (
        "📱 **Copie e envie:**\n\n"
        f"_Estou usando um bot de finanças com IA que me diz "
        f"exatamente o que comprar. Olha:_\n{link}"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")


async def processar_indicacao(referrer_id: int, referred_id: int) -> str | None:
    """
    Processa uma indicação vinda do /start ref_XXXXX.
    Retorna mensagem de boas-vindas extra ou None.
    """
    ok = await registrar_indicacao(referrer_id, referred_id)
    if not ok:
        return None

    # Bonus para quem indicou
    resultado = await aplicar_bonus_indicacao(referrer_id)

    return (
        f"🎁 Você veio por indicação! Ganhou "
        f"**+{FREE_DAILY_LIMIT} consultas grátis extras** de bônus!\n"
    )


# ── /orcamento — Orçamento mensal inteligente ──────────────────

ORC_CONFIG = 0  # estado da conversa


async def orcamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o orçamento mensal do usuário."""
    telegram_id = update.effective_user.id
    user = await get_or_create_user(telegram_id)
    renda = user.get("renda_mensal", 0)

    if not renda:
        await update.message.reply_text(
            "💰 **Orçamento Inteligente**\n\n"
            "Para criar seu orçamento, preciso saber sua renda.\n"
            "Use /start para informar ou me diga: "
            "_\"Minha renda é R$3000\"_",
            parse_mode="Markdown",
        )
        return

    orc = await get_or_create_orcamento(telegram_id)
    gastos = await get_resumo_gastos_mes(telegram_id)

    pct_n = orc["necessidades_pct"]
    pct_d = orc["desejos_pct"]
    pct_i = orc["investimentos_pct"]

    limite_n = renda * pct_n / 100
    limite_d = renda * pct_d / 100
    limite_i = renda * pct_i / 100

    # Categorizar gastos
    from config import CATEGORIAS_GASTOS

    cat_necessidades = {"alimentação", "moradia", "transporte", "saúde", "educação", "contas"}
    cat_desejos = {"lazer", "compras", "restaurante", "entretenimento", "assinatura"}

    gasto_n = 0.0
    gasto_d = 0.0
    gasto_outro = 0.0

    for cat, val in gastos.get("categorias", {}).items():
        cat_lower = cat.lower()
        if cat_lower in cat_necessidades:
            gasto_n += val
        elif cat_lower in cat_desejos:
            gasto_d += val
        else:
            gasto_outro += val

    # Distribuir "outro" proporcionalmente
    gasto_n += gasto_outro * 0.7
    gasto_d += gasto_outro * 0.3

    total_gasto = gastos["total"]
    sobra = renda - total_gasto
    investido = max(0, sobra)  # simplificação

    msg = (
        "💰 **Orçamento Inteligente**\n\n"
        f"📊 Regra: **{pct_n:.0f}/{pct_d:.0f}/{pct_i:.0f}**\n"
        f"💵 Renda: R${renda:,.2f}\n\n"
    )

    # Necessidades
    pct_usado_n = gasto_n / limite_n * 100 if limite_n else 0
    emoji_n = "🟢" if pct_usado_n <= 90 else ("🟡" if pct_usado_n <= 100 else "🔴")
    barra_n = _barra_orcamento(pct_usado_n)
    msg += (
        f"{emoji_n} **Necessidades** ({pct_n:.0f}% = R${limite_n:,.0f})\n"
        f"{barra_n}\n"
        f"   Gasto: R${gasto_n:,.0f} / R${limite_n:,.0f}\n\n"
    )

    # Desejos
    pct_usado_d = gasto_d / limite_d * 100 if limite_d else 0
    emoji_d = "🟢" if pct_usado_d <= 90 else ("🟡" if pct_usado_d <= 100 else "🔴")
    barra_d = _barra_orcamento(pct_usado_d)
    msg += (
        f"{emoji_d} **Desejos** ({pct_d:.0f}% = R${limite_d:,.0f})\n"
        f"{barra_d}\n"
        f"   Gasto: R${gasto_d:,.0f} / R${limite_d:,.0f}\n\n"
    )

    # Investimentos
    pct_usado_i = investido / limite_i * 100 if limite_i else 0
    emoji_i = "🟢" if pct_usado_i >= 80 else ("🟡" if pct_usado_i >= 50 else "🔴")
    barra_i = _barra_orcamento(pct_usado_i)
    msg += (
        f"{emoji_i} **Investimentos** ({pct_i:.0f}% = R${limite_i:,.0f})\n"
        f"{barra_i}\n"
        f"   Disponível: R${investido:,.0f} / R${limite_i:,.0f}\n\n"
    )

    # Resumo
    if total_gasto > renda:
        msg += (
            f"🔴 **ATENÇÃO:** Gastou R${total_gasto - renda:,.0f} "
            f"acima da renda!\n\n"
        )
    elif sobra > 0:
        msg += f"✅ **Sobra do mês:** R${sobra:,.0f}\n\n"

    # Sugestões
    if pct_usado_n > 100:
        msg += "💡 Necessidades estouraram — revise moradia e transporte\n"
    if pct_usado_d > 100:
        msg += "💡 Desejos estouraram — corte assinaturas e lazer extra\n"
    if pct_usado_i < 50:
        msg += "💡 Investindo pouco — /aporte para automatizar\n"

    msg += (
        "\n━━━━━━━━━━━━━━━━━━━\n"
        "/gasto — Registrar gasto\n"
        "/resumo — Detalhes dos gastos\n"
        f"/orcamento ajustar — Mudar proporções\n"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")


async def ajustar_orcamento(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Inicia ajuste de orçamento."""
    await update.message.reply_text(
        "⚙️ **Ajustar Orçamento**\n\n"
        "A regra padrão é **50/30/20**:\n"
        "• 50% Necessidades (moradia, comida, contas)\n"
        "• 30% Desejos (lazer, compras)\n"
        "• 20% Investimentos\n\n"
        "Escolha um modelo:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "50/30/20 (Padrão)", callback_data="orc_50_30_20"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "60/20/20 (Conservador)", callback_data="orc_60_20_20"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "40/20/40 (Investidor)", callback_data="orc_40_20_40"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "30/20/50 (Agressivo)", callback_data="orc_30_20_50"
                    ),
                ],
            ]
        ),
    )


async def salvar_ajuste_orcamento(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Salva o ajuste de orçamento."""
    query = update.callback_query
    await query.answer()

    partes = query.data.split("_")
    n, d, i = float(partes[1]), float(partes[2]), float(partes[3])

    telegram_id = query.from_user.id
    await salvar_orcamento(telegram_id, n, d, i)

    # XP por configurar
    await add_xp(telegram_id, "ver_dashboard")

    await query.edit_message_text(
        f"✅ Orçamento atualizado: **{n:.0f}/{d:.0f}/{i:.0f}**\n\n"
        "Use /orcamento para ver o acompanhamento!",
        parse_mode="Markdown",
    )


def _barra_orcamento(pct: float) -> str:
    """Barra de progresso do orçamento."""
    pct = min(150, max(0, pct))
    filled = int(min(pct, 100) / 5)
    over = int(max(0, pct - 100) / 10)
    barra = "▓" * filled + "░" * (20 - filled)
    if over:
        barra += "🔴" * over
    return f"   {barra} {pct:.0f}%"


# ── Formatação de notificações de XP ───────────────────────────


def formatar_xp_ganho(resultado: dict) -> str:
    """Formata uma notificação de XP ganho para incluir em mensagens."""
    partes = []

    xp = resultado.get("xp_ganho", 0)
    if xp > 0:
        partes.append(f"⭐ +{xp} XP")

    if resultado.get("subiu_nivel"):
        nivel = resultado["nivel_novo"]
        for n in NIVEIS:
            if n["nivel"] == nivel:
                partes.append(f"🎉 Subiu para {n['emoji']} Nível {nivel} — {n['nome']}!")
                break

    conquistas = resultado.get("conquistas_novas", [])
    for c in conquistas:
        partes.append(f"🏆 {c['emoji']} {c['nome']}!")

    return "\n".join(partes)


# ── Handlers ───────────────────────────────────────────────────


def get_gamificacao_handlers() -> list:
    """Retorna os handlers de gamificação, indicação e orçamento."""
    return [
        CommandHandler("conquistas", conquistas),
        CommandHandler("nivel", conquistas),
        CommandHandler("xp", conquistas),
        CommandHandler("ranking", ranking),
        CommandHandler("indicar", indicar),
        CommandHandler("convidar", indicar),
        CommandHandler("orcamento", orcamento),
        CommandHandler("budget", orcamento),
        CallbackQueryHandler(salvar_ajuste_orcamento, pattern=r"^orc_\d+_\d+_\d+$"),
    ]
