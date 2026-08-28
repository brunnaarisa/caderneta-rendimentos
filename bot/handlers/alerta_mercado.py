"""
Handler de alertas de mercado — notificações URGENTES de oportunidades.

/alertamercado — Ativar/desativar alertas de oportunidades do mercado.

Quando ativado, o bot monitora criptos e ações a cada 2 horas
e envia alertas URGENTES quando detecta:
- Quedas bruscas (oportunidade de compra)
- RSI sobrevendido (< 25) ou sobrecomprado (> 80)
- Fear & Greed extremo (< 20 pânico, > 80 euforia)
- Altas fortes (oportunidade de venda)
"""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from database.db import get_db

logger = logging.getLogger(__name__)


# ── Serviço de configuração ──────────────────────────────────


async def get_alerta_mercado_config(telegram_id: int) -> dict | None:
    """Busca configuração de alertas de mercado do usuário."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM alerta_mercado_config WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def toggle_alerta_mercado(telegram_id: int) -> bool:
    """Ativa/desativa alertas de mercado. Retorna o novo estado."""
    config = await get_alerta_mercado_config(telegram_id)
    db = await get_db()
    try:
        if config:
            novo = 0 if config["ativo"] else 1
            await db.execute(
                "UPDATE alerta_mercado_config SET ativo = ? "
                "WHERE telegram_id = ?",
                (novo, telegram_id),
            )
        else:
            novo = 1
            await db.execute(
                "INSERT INTO alerta_mercado_config (telegram_id, ativo) "
                "VALUES (?, 1)",
                (telegram_id,),
            )
        await db.commit()
        return bool(novo)
    finally:
        await db.close()


async def get_usuarios_alerta_mercado() -> list[dict]:
    """Retorna todos os usuários com alertas de mercado ativos."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT telegram_id, ultimo_alerta FROM alerta_mercado_config "
            "WHERE ativo = 1"
        )
        return [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()


async def update_ultimo_alerta_mercado(telegram_id: int):
    """Atualiza timestamp do último alerta de mercado enviado."""
    db = await get_db()
    try:
        await db.execute(
            "UPDATE alerta_mercado_config SET ultimo_alerta = datetime('now') "
            "WHERE telegram_id = ?",
            (telegram_id,),
        )
        await db.commit()
    finally:
        await db.close()


# ── Handler do /alertamercado ─────────────────────────────────


async def alerta_mercado_cmd(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Mostra painel de controle dos alertas de mercado."""
    telegram_id = update.effective_user.id
    config = await get_alerta_mercado_config(telegram_id)
    ativo = config["ativo"] if config else False

    status = "🟢 **ATIVADOS**" if ativo else "🔴 **DESATIVADOS**"

    await update.message.reply_text(
        "🚨 **Alertas Urgentes de Mercado**\n\n"
        f"Status: {status}\n\n"
        "Quando ativados, eu monitoro o mercado 24/7 e te aviso:\n\n"
        "📉 **COMPRE AGORA** quando:\n"
        "• Cripto cai mais de 5% em 24h\n"
        "• RSI < 25 (sobrevendido — possível fundo)\n"
        "• Índice de Medo < 20 (pânico = hora de comprar)\n\n"
        "📈 **VENDA AGORA** quando:\n"
        "• Cripto sobe mais de 15% em 24h\n"
        "• RSI > 80 (sobrecomprado — mercado pode cair)\n"
        "• Índice de Ganância > 80 (euforia = hora de sair)\n\n"
        "⚡ _Alertas verificados a cada 2 horas._\n"
        "🔔 _Máximo 1 alerta a cada 6 horas para não incomodar._",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔴 Desativar" if ativo else "🟢 Ativar alertas!",
                        callback_data="alertamercado_toggle",
                    )
                ]
            ]
        ),
    )


async def alerta_mercado_toggle(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Toggle dos alertas de mercado."""
    query = update.callback_query
    await query.answer()

    telegram_id = query.from_user.id
    novo_estado = await toggle_alerta_mercado(telegram_id)

    if novo_estado:
        await query.edit_message_text(
            "🟢 **Alertas de mercado ATIVADOS!**\n\n"
            "Vou te avisar quando detectar oportunidades urgentes.\n"
            "Fique de olho nas notificações! 🔔\n\n"
            "📊 Monitorando: Bitcoin, Ethereum, Solana, BOVA11, "
            "IVVB11, WEGE3, PETR4, VALE3\n\n"
            "_Use /alertamercado para desativar._",
            parse_mode="Markdown",
        )
    else:
        await query.edit_message_text(
            "🔴 **Alertas de mercado desativados.**\n\n"
            "Você não receberá mais alertas de oportunidades.\n"
            "_Use /alertamercado para reativar._",
            parse_mode="Markdown",
        )


# ── Handlers ──────────────────────────────────────────────────


def get_alerta_mercado_handlers() -> list:
    """Retorna os handlers de alerta de mercado."""
    return [
        CommandHandler("alertamercado", alerta_mercado_cmd),
        CommandHandler("alertasmercado", alerta_mercado_cmd),
        CallbackQueryHandler(
            alerta_mercado_toggle, pattern=r"^alertamercado_toggle$"
        ),
    ]
