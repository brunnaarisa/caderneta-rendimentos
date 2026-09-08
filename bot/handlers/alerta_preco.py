"""
Handler de alertas de preço-alvo.

/alvo BTC 400000 — Avisa quando Bitcoin chegar em R$400.000
/alvo PETR4 45   — Avisa quando Petrobras chegar em R$45
/alvos           — Lista seus alertas ativos
/removeralvo 1   — Remove um alerta pelo ID

Suporta direção automática:
- Se o preço-alvo > preço atual → alerta quando SUBIR até lá
- Se o preço-alvo < preço atual → alerta quando CAIR até lá
"""

import logging

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from database.db import get_db
from services.market_analysis import get_crypto_price, get_stock_price
from services.portfolio_service import CRYPTO_MAP, CRYPTO_NOMES

logger = logging.getLogger(__name__)


# ── Serviço de alertas de preço ──────────────────────────────


async def criar_alerta_preco(
    telegram_id: int,
    ativo: str,
    tipo: str,
    direcao: str,
    preco_alvo: float,
) -> int:
    """Cria um alerta de preço. Retorna o ID."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO alertas_preco "
            "(telegram_id, ativo, tipo, direcao, preco_alvo) "
            "VALUES (?, ?, ?, ?, ?)",
            (telegram_id, ativo, tipo, direcao, preco_alvo),
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def get_alertas_preco(telegram_id: int) -> list[dict]:
    """Busca alertas de preço ativos do usuário."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM alertas_preco "
            "WHERE telegram_id = ? AND ativo_flag = 1 AND notificado = 0 "
            "ORDER BY criado_em DESC",
            (telegram_id,),
        )
        return [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()


async def get_todos_alertas_preco_ativos() -> list[dict]:
    """Busca todos os alertas de preço ativos de todos os usuários."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM alertas_preco "
            "WHERE ativo_flag = 1 AND notificado = 0"
        )
        return [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()


async def marcar_alerta_notificado(alerta_id: int):
    """Marca um alerta como notificado."""
    db = await get_db()
    try:
        await db.execute(
            "UPDATE alertas_preco SET notificado = 1 WHERE id = ?",
            (alerta_id,),
        )
        await db.commit()
    finally:
        await db.close()


async def remover_alerta_preco(telegram_id: int, alerta_id: int) -> bool:
    """Remove um alerta de preço. Retorna True se removeu."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "DELETE FROM alertas_preco "
            "WHERE id = ? AND telegram_id = ?",
            (alerta_id, telegram_id),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


# ── Identificação de ativo ───────────────────────────────────


def _identificar_ativo(nome: str) -> tuple[str, str] | None:
    """
    Identifica um ativo pelo nome/ticker.
    Retorna (ativo_id, tipo) ou None.
    """
    nome_upper = nome.upper().strip()
    nome_lower = nome.lower().strip()

    # Mapa de aliases para cripto
    crypto_aliases = {
        "BTC": "bitcoin",
        "BITCOIN": "bitcoin",
        "ETH": "ethereum",
        "ETHEREUM": "ethereum",
        "SOL": "solana",
        "SOLANA": "solana",
    }

    # Também verificar o CRYPTO_MAP do portfolio_service
    if nome_lower in CRYPTO_MAP:
        return (CRYPTO_MAP[nome_lower], "crypto")

    if nome_upper in crypto_aliases:
        return (crypto_aliases[nome_upper], "crypto")

    # Verificar se parece ticker da B3 (4-6 letras + números)
    import re

    if re.match(r"^[A-Z]{4}\d{1,2}$", nome_upper):
        return (nome_upper, "acao")

    return None


# ── Handlers ─────────────────────────────────────────────────


async def alvo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /alvo BTC 400000 — Cria alerta de preço-alvo.
    Detecta automaticamente se deve alertar quando subir ou cair.
    """
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "🎯 **Alertas de Preço-Alvo**\n\n"
            "Eu aviso quando um ativo chegar no preço que você quer!\n\n"
            "**Como usar:**\n"
            "`/alvo BTC 400000` — Avisa quando BTC chegar em R$400k\n"
            "`/alvo PETR4 45` — Avisa quando PETR4 chegar em R$45\n"
            "`/alvo ETH 10000` — Avisa quando ETH chegar em R$10k\n\n"
            "📋 /alvos — Ver seus alertas ativos\n"
            "🗑️ /removeralvo [id] — Remover um alerta",
            parse_mode="Markdown",
        )
        return

    nome_ativo = context.args[0]
    try:
        preco_alvo = float(
            context.args[1]
            .replace(",", ".")
            .replace("R$", "")
            .replace("r$", "")
        )
    except ValueError:
        await update.message.reply_text(
            "❌ Preço inválido. Use números, ex: `/alvo BTC 400000`",
            parse_mode="Markdown",
        )
        return

    if preco_alvo <= 0:
        await update.message.reply_text("❌ O preço deve ser maior que zero.")
        return

    # Identificar o ativo
    ativo_info = _identificar_ativo(nome_ativo)
    if not ativo_info:
        await update.message.reply_text(
            f"❌ Não reconheci o ativo **{nome_ativo}**.\n\n"
            "Exemplos: BTC, ETH, SOL, PETR4, VALE3, BOVA11",
            parse_mode="Markdown",
        )
        return

    ativo_id, tipo = ativo_info

    # Buscar preço atual para determinar direção
    preco_atual = None
    if tipo == "crypto":
        pd = await get_crypto_price(ativo_id)
        if pd:
            preco_atual = pd["preco_brl"]
    else:
        sd = await get_stock_price(ativo_id)
        if sd:
            preco_atual = sd["preco"]

    if not preco_atual:
        await update.message.reply_text(
            f"❌ Não consegui buscar o preço atual de **{nome_ativo}**. "
            "Tente novamente em alguns segundos.",
            parse_mode="Markdown",
        )
        return

    # Determinar direção
    if preco_alvo > preco_atual:
        direcao = "acima"
        emoji_dir = "📈"
        texto_dir = "subir"
    else:
        direcao = "abaixo"
        emoji_dir = "📉"
        texto_dir = "cair"

    # Calcular diferença percentual
    diff_pct = ((preco_alvo - preco_atual) / preco_atual) * 100

    # Criar alerta
    telegram_id = update.effective_user.id
    alerta_id = await criar_alerta_preco(
        telegram_id, ativo_id, tipo, direcao, preco_alvo
    )

    nome_display = CRYPTO_NOMES.get(ativo_id, ativo_id.upper())

    await update.message.reply_text(
        f"🎯 **Alerta de preço criado!**\n\n"
        f"📌 Ativo: **{nome_display}**\n"
        f"💰 Preço atual: R${preco_atual:,.2f}\n"
        f"🎯 Alvo: R${preco_alvo:,.2f}\n"
        f"{emoji_dir} Direção: {texto_dir} ({diff_pct:+.1f}%)\n\n"
        f"🔔 Eu te aviso quando o preço chegar lá!\n"
        f"_ID do alerta: #{alerta_id}_\n\n"
        f"📋 /alvos — Ver todos os seus alertas",
        parse_mode="Markdown",
    )


async def alvos_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista alertas de preço ativos do usuário."""
    telegram_id = update.effective_user.id
    alertas = await get_alertas_preco(telegram_id)

    if not alertas:
        await update.message.reply_text(
            "📋 Você não tem alertas de preço ativos.\n\n"
            "Use `/alvo BTC 400000` para criar um!",
            parse_mode="Markdown",
        )
        return

    msg = "🎯 **Seus Alertas de Preço:**\n\n"

    for a in alertas:
        nome = CRYPTO_NOMES.get(a["ativo"], a["ativo"].upper())
        emoji = "📈" if a["direcao"] == "acima" else "📉"
        direcao_txt = "subir" if a["direcao"] == "acima" else "cair"

        # Buscar preço atual
        preco_atual = None
        if a["tipo"] == "crypto":
            pd = await get_crypto_price(a["ativo"])
            if pd:
                preco_atual = pd["preco_brl"]
        else:
            sd = await get_stock_price(a["ativo"])
            if sd:
                preco_atual = sd["preco"]

        msg += f"{emoji} **#{a['id']}** — {nome}\n"
        msg += f"   🎯 Alvo: R${a['preco_alvo']:,.2f} ({direcao_txt})\n"
        if preco_atual:
            diff = ((a['preco_alvo'] - preco_atual) / preco_atual) * 100
            msg += f"   💰 Atual: R${preco_atual:,.2f} ({diff:+.1f}% falta)\n"
        msg += "\n"

    msg += "🗑️ `/removeralvo [id]` para remover um alerta"

    await update.message.reply_text(msg, parse_mode="Markdown")


async def remover_alvo_cmd(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Remove um alerta de preço pelo ID."""
    if not context.args:
        await update.message.reply_text(
            "Use: `/removeralvo [id]`\n"
            "Ex: `/removeralvo 1`\n\n"
            "Veja seus alertas com /alvos",
            parse_mode="Markdown",
        )
        return

    try:
        alerta_id = int(context.args[0].replace("#", ""))
    except ValueError:
        await update.message.reply_text("❌ ID inválido. Use um número.")
        return

    telegram_id = update.effective_user.id
    removido = await remover_alerta_preco(telegram_id, alerta_id)

    if removido:
        await update.message.reply_text(
            f"✅ Alerta #{alerta_id} removido com sucesso!"
        )
    else:
        await update.message.reply_text(
            f"❌ Alerta #{alerta_id} não encontrado. "
            "Verifique com /alvos"
        )


def get_alerta_preco_handlers() -> list:
    """Retorna os handlers de alerta de preço."""
    return [
        CommandHandler("alvo", alvo_cmd),
        CommandHandler("alvos", alvos_cmd),
        CommandHandler("removeralvo", remover_alvo_cmd),
    ]
