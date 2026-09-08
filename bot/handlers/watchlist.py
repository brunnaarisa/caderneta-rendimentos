"""
Handler da Watchlist personalizada.

/seguir BTC — Adiciona ativo à watchlist
/desseguir BTC — Remove ativo da watchlist
/meusativos — Lista watchlist com preços ao vivo
"""

import logging

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from database.db import get_db
from services.market_analysis import (
    SINAL_EMOJI,
    SINAL_TEXTO,
    analise_completa_acao,
    analise_completa_crypto,
    get_crypto_price,
    get_stock_price,
)
from services.portfolio_service import CRYPTO_MAP, CRYPTO_NOMES, normalizar_ativo

logger = logging.getLogger(__name__)


# ── Serviço de watchlist ────────────────────────────────────


async def adicionar_watchlist(telegram_id: int, ativo: str, tipo: str) -> bool:
    """Adiciona ativo à watchlist. Retorna False se já existe."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT 1 FROM watchlist WHERE telegram_id = ? AND ativo = ?",
            (telegram_id, ativo),
        )
        if await cursor.fetchone():
            return False
        await db.execute(
            "INSERT INTO watchlist (telegram_id, ativo, tipo) VALUES (?, ?, ?)",
            (telegram_id, ativo, tipo),
        )
        await db.commit()
        return True
    finally:
        await db.close()


async def remover_watchlist(telegram_id: int, ativo: str) -> bool:
    """Remove ativo da watchlist. Retorna True se removeu."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "DELETE FROM watchlist WHERE telegram_id = ? AND ativo = ?",
            (telegram_id, ativo),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def get_watchlist(telegram_id: int) -> list[dict]:
    """Retorna a watchlist do usuário."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM watchlist WHERE telegram_id = ? ORDER BY criado_em DESC",
            (telegram_id,),
        )
        return [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()


# ── Handlers ─────────────────────────────────────────────────


async def seguir_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/seguir BTC — Adiciona ativo à watchlist."""
    if not context.args:
        await update.message.reply_text(
            "👁️ **Watchlist — Seus Ativos Favoritos**\n\n"
            "Adicione ativos que você quer monitorar de perto!\n\n"
            "**Como usar:**\n"
            "`/seguir BTC` — Seguir Bitcoin\n"
            "`/seguir PETR4` — Seguir Petrobras\n"
            "`/seguir ETH SOL` — Seguir vários de uma vez\n\n"
            "📋 /meusativos — Ver sua watchlist\n"
            "❌ /desseguir BTC — Parar de seguir",
            parse_mode="Markdown",
        )
        return

    telegram_id = update.effective_user.id
    adicionados = []
    ja_existem = []
    nao_reconhecidos = []

    for nome in context.args:
        ativo_id, tipo = normalizar_ativo(nome)

        # Verificar se o ativo existe (buscar preço como teste)
        existe = False
        if tipo == "crypto":
            pd = await get_crypto_price(ativo_id)
            existe = pd is not None
        else:
            sd = await get_stock_price(ativo_id)
            existe = sd is not None

        if not existe:
            nao_reconhecidos.append(nome.upper())
            continue

        ok = await adicionar_watchlist(telegram_id, ativo_id, tipo)
        nome_display = CRYPTO_NOMES.get(ativo_id, ativo_id.upper())
        if ok:
            adicionados.append(nome_display)
        else:
            ja_existem.append(nome_display)

    msg = ""
    if adicionados:
        msg += "✅ **Adicionados à watchlist:**\n"
        for a in adicionados:
            msg += f"   👁️ {a}\n"
        msg += "\n"
    if ja_existem:
        msg += "ℹ️ _Já estão na watchlist:_ "
        msg += ", ".join(ja_existem) + "\n\n"
    if nao_reconhecidos:
        msg += "❌ _Não reconhecidos:_ "
        msg += ", ".join(nao_reconhecidos) + "\n\n"

    msg += "📋 /meusativos — Ver watchlist completa"

    await update.message.reply_text(msg, parse_mode="Markdown")

    # XP por personalizar
    from services.gamification_service import add_xp, registrar_acesso_diario

    await registrar_acesso_diario(telegram_id)
    await add_xp(telegram_id, "ver_dashboard")


async def desseguir_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/desseguir BTC — Remove ativo da watchlist."""
    if not context.args:
        await update.message.reply_text(
            "Use: `/desseguir BTC` para parar de seguir.\n"
            "📋 /meusativos para ver sua lista.",
            parse_mode="Markdown",
        )
        return

    telegram_id = update.effective_user.id
    removidos = []
    nao_encontrados = []

    for nome in context.args:
        ativo_id, _ = normalizar_ativo(nome)
        ok = await remover_watchlist(telegram_id, ativo_id)
        nome_display = CRYPTO_NOMES.get(ativo_id, ativo_id.upper())
        if ok:
            removidos.append(nome_display)
        else:
            nao_encontrados.append(nome_display)

    msg = ""
    if removidos:
        msg += "❌ Removidos: " + ", ".join(removidos) + "\n"
    if nao_encontrados:
        msg += "ℹ️ Não estavam na lista: " + ", ".join(nao_encontrados) + "\n"

    await update.message.reply_text(msg, parse_mode="Markdown")


async def meusativos_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/meusativos — Lista watchlist com preços e sinais ao vivo."""
    telegram_id = update.effective_user.id
    watchlist = await get_watchlist(telegram_id)

    if not watchlist:
        await update.message.reply_text(
            "👁️ Sua watchlist está vazia!\n\n"
            "Use `/seguir BTC` para adicionar ativos.\n"
            "Ex: `/seguir BTC ETH PETR4 VALE3`",
            parse_mode="Markdown",
        )
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    msg = "👁️ **Sua Watchlist**\n\n"

    for item in watchlist:
        ativo = item["ativo"]
        tipo = item["tipo"]
        nome = CRYPTO_NOMES.get(ativo, ativo.upper())

        if tipo == "crypto":
            try:
                analise = await analise_completa_crypto(ativo)
                if analise:
                    preco = analise["preco"]["preco_brl"]
                    var = analise["preco"].get("variacao_24h", 0)
                    sinal = analise["sinal"]
                    emoji_s = SINAL_EMOJI.get(sinal["sinal"], "🟡")
                    texto_s = SINAL_TEXTO.get(sinal["sinal"], "Neutro")
                    emoji_v = "🟢" if var >= 0 else "🔴"
                    sinal_v = "+" if var >= 0 else ""

                    msg += (
                        f"{emoji_s} **{nome}**\n"
                        f"   💰 R${preco:,.2f} ({emoji_v} {sinal_v}{var:.1f}%)\n"
                        f"   📊 {texto_s} (score {sinal['score']:+d})\n\n"
                    )
                    continue
            except Exception:
                pass
        else:
            try:
                analise = await analise_completa_acao(ativo)
                if analise:
                    preco = analise["stock"]["preco"]
                    var = analise["stock"].get("variacao_dia", 0)
                    sinal = analise["sinal"]
                    emoji_s = SINAL_EMOJI.get(sinal["sinal"], "🟡")
                    texto_s = SINAL_TEXTO.get(sinal["sinal"], "Neutro")
                    emoji_v = "🟢" if var >= 0 else "🔴"
                    sinal_v = "+" if var >= 0 else ""

                    msg += (
                        f"{emoji_s} **{nome}**\n"
                        f"   💰 R${preco:.2f} ({emoji_v} {sinal_v}{var:.1f}%)\n"
                        f"   📊 {texto_s} (score {sinal['score']:+d})\n\n"
                    )
                    continue
            except Exception:
                pass

        # Fallback: só preço
        msg += f"🟡 **{nome}** — _dados indisponíveis_\n\n"

    msg += (
        "━━━━━━━━━━━━━━━━━━━\n"
        "➕ /seguir [ativo] — Adicionar\n"
        "➖ /desseguir [ativo] — Remover\n"
        "📈 /analisar [ativo] — Análise detalhada\n"
        "🎯 /alvo [ativo] [preço] — Criar alerta"
    )

    # Dividir se necessário
    if len(msg) > 4000:
        partes = []
        remaining = msg
        while remaining:
            if len(remaining) <= 4000:
                partes.append(remaining)
                break
            corte = remaining.rfind("\n", 0, 4000)
            if corte == -1:
                corte = 4000
            partes.append(remaining[:corte])
            remaining = remaining[corte:].lstrip("\n")
        for parte in partes:
            await update.message.reply_text(parte, parse_mode="Markdown")
    else:
        await update.message.reply_text(msg, parse_mode="Markdown")


def get_watchlist_handlers() -> list:
    """Retorna os handlers da watchlist."""
    return [
        CommandHandler("seguir", seguir_cmd),
        CommandHandler("watch", seguir_cmd),
        CommandHandler("desseguir", desseguir_cmd),
        CommandHandler("unwatch", desseguir_cmd),
        CommandHandler("meusativos", meusativos_cmd),
        CommandHandler("watchlist", meusativos_cmd),
    ]
