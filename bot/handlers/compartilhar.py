"""
Handler de compartilhamento social.

/compartilhar — Gera um texto formatado para compartilhar
               resultados da carteira nas redes sociais.

Marketing viral: cada compartilhamento divulga o bot.
"""

import datetime
import logging

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from services.market_analysis import get_crypto_price, get_stock_price
from services.portfolio_service import CRYPTO_NOMES, get_carteira_ativa

logger = logging.getLogger(__name__)


async def compartilhar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /compartilhar — Gera texto para compartilhar resultados.
    O texto inclui menção ao bot para marketing viral.
    """
    telegram_id = update.effective_user.id
    posicoes = await get_carteira_ativa(telegram_id)

    if not posicoes:
        await update.message.reply_text(
            "🏆 **Compartilhar Resultados**\n\n"
            "Você ainda não tem posições registradas.\n"
            "Use /comprei para registrar e depois compartilhar! 📈",
            parse_mode="Markdown",
        )
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    total_investido = 0.0
    total_atual = 0.0
    melhor_ativo = None
    melhor_var = -999

    for pos in posicoes:
        ativo = pos["ativo"]
        tipo = pos["tipo"]
        preco_compra = pos["preco_compra"]
        valor_investido = pos["valor_investido"]

        preco_atual = preco_compra
        if tipo == "crypto":
            pd = await get_crypto_price(ativo)
            if pd:
                preco_atual = pd["preco_brl"]
        else:
            sd = await get_stock_price(ativo)
            if sd:
                preco_atual = sd["preco"]

        var = ((preco_atual - preco_compra) / preco_compra) * 100
        valor_atual = valor_investido * (1 + var / 100)

        total_investido += valor_investido
        total_atual += valor_atual

        if var > melhor_var:
            melhor_var = var
            melhor_ativo = CRYPTO_NOMES.get(ativo, ativo.upper())

    lucro = total_atual - total_investido
    var_total = (lucro / total_investido * 100) if total_investido else 0

    agora = datetime.datetime.now().strftime("%d/%m/%Y")

    # Gerar texto baseado na performance
    if var_total >= 50:
        emoji_header = "🚀🚀🚀"
        frase = "MEU PORTFOLIO EXPLODIU!"
    elif var_total >= 20:
        emoji_header = "🔥🔥"
        frase = "Carteira bombando!"
    elif var_total >= 5:
        emoji_header = "📈✨"
        frase = "Rendendo bem!"
    elif var_total >= 0:
        emoji_header = "💪📊"
        frase = "No positivo e crescendo!"
    elif var_total >= -10:
        emoji_header = "🧘📉"
        frase = "Comprar na baixa é a estratégia!"
    else:
        emoji_header = "💎🙌"
        frase = "HOLD! Diamantes se formam sob pressão!"

    sinal = "+" if lucro >= 0 else ""

    # Texto para compartilhamento
    share_text = (
        f"{emoji_header} {frase}\n\n"
        f"📊 Minha carteira hoje ({agora}):\n"
        f"💰 Resultado: {sinal}{var_total:.1f}%\n"
        f"📈 {len(posicoes)} ativo(s) monitorados\n"
    )

    if melhor_ativo and melhor_var > 0:
        share_text += f"⭐ Melhor: {melhor_ativo} ({'+' if melhor_var >= 0 else ''}{melhor_var:.1f}%)\n"

    share_text += (
        f"\n🤖 Usando o FinançasIA — Meu consultor financeiro com IA!\n"
        f"#investimentos #finançasia #investir"
    )

    # Enviar para o usuário copiar
    await update.message.reply_text(
        "🏆 **Compartilhe seus resultados!**\n\n"
        "Copie o texto abaixo e cole no Instagram, Twitter, "
        "WhatsApp ou onde quiser:\n\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"{share_text}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "📋 _Toque para copiar e compartilhe!_\n"
        "💡 _Cada compartilhamento ajuda outros a conhecer "
        "investimentos!_",
        parse_mode="Markdown",
    )

    # Também enviar como texto puro para facilitar copiar
    await update.message.reply_text(share_text)

    # XP por compartilhar
    from services.gamification_service import add_xp, registrar_acesso_diario

    await registrar_acesso_diario(telegram_id)
    resultado = await add_xp(telegram_id, "compartilhar")

    if resultado.get("xp_ganho"):
        await update.message.reply_text(
            f"⭐ +{resultado['xp_ganho']} XP por compartilhar! 🎉"
        )


def get_compartilhar_handlers() -> list:
    """Retorna os handlers de compartilhamento."""
    return [
        CommandHandler("compartilhar", compartilhar_cmd),
        CommandHandler("share", compartilhar_cmd),
    ]
