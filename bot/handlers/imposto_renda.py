"""
Handler de cálculo de Imposto de Renda sobre investimentos.

/ir — Calcula o IR devido sobre ganhos de capital com base na carteira.

Regras brasileiras simplificadas:
- Ações (swing trade): 15% sobre lucro. Isento se vendas no mês < R$20.000.
- Ações (day trade): 20% sobre lucro.
- Cripto: 15% sobre lucro se vendas no mês > R$35.000. Isento abaixo.
- FIIs: 20% sobre ganho de capital. Dividendos isentos.
- Renda fixa (CDB, LCI, etc.): Tabela regressiva (22.5% a 15%).
"""

import logging
from datetime import datetime

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from database.db import get_db
from services.market_analysis import get_crypto_price, get_stock_price
from services.portfolio_service import CRYPTO_NOMES

logger = logging.getLogger(__name__)

# Tabela regressiva de IR sobre renda fixa
TABELA_RF = [
    (180, 22.5),   # Até 180 dias: 22.5%
    (360, 20.0),   # 181 a 360 dias: 20%
    (720, 17.5),   # 361 a 720 dias: 17.5%
    (99999, 15.0), # Acima de 720 dias: 15%
]


def _aliquota_rf(dias: int) -> float:
    """Retorna a alíquota de IR para renda fixa pelo prazo."""
    for limite, aliquota in TABELA_RF:
        if dias <= limite:
            return aliquota
    return 15.0


async def imposto_renda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Calcula IR sobre ganhos de capital da carteira do usuário."""
    telegram_id = update.effective_user.id

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    db = await get_db()
    try:
        # Buscar vendas realizadas (carteira vendida)
        cursor = await db.execute(
            "SELECT * FROM carteira WHERE telegram_id = ? AND vendido = 1 "
            "ORDER BY data_venda DESC",
            (telegram_id,),
        )
        vendas = [dict(r) for r in await cursor.fetchall()]

        # Buscar posições abertas (lucro não realizado)
        cursor = await db.execute(
            "SELECT * FROM carteira WHERE telegram_id = ? AND vendido = 0",
            (telegram_id,),
        )
        posicoes = [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()

    if not vendas and not posicoes:
        await update.message.reply_text(
            "📊 **Calculadora de IR — Investimentos**\n\n"
            "Você ainda não tem posições registradas.\n\n"
            "Use /comprei para registrar suas compras e eu calculo "
            "o imposto automaticamente! 📝",
            parse_mode="Markdown",
        )
        return

    msg = "📊 **Calculadora de Imposto de Renda**\n\n"

    # ── LUCRO REALIZADO (vendas) ──
    if vendas:
        msg += "💰 **Vendas Realizadas (lucro/prejuízo):**\n\n"

        total_lucro_acoes = 0.0
        total_vendas_acoes_mes = 0.0
        total_lucro_crypto = 0.0
        total_vendas_crypto_mes = 0.0
        total_lucro_fii = 0.0
        mes_atual = datetime.now().strftime("%Y-%m")

        for v in vendas:
            lucro = 0.0
            if v.get("preco_venda") and v.get("preco_compra"):
                var_pct = (
                    (v["preco_venda"] - v["preco_compra"])
                    / v["preco_compra"]
                )
                lucro = v["valor_investido"] * var_pct

            tipo = v.get("tipo", "crypto")
            nome = CRYPTO_NOMES.get(v["ativo"], v["ativo"].upper())
            emoji = "🟢" if lucro >= 0 else "🔴"
            sinal = "+" if lucro >= 0 else ""

            # Verificar se é do mês atual
            venda_mes = (v.get("data_venda") or "")[:7]

            msg += (
                f"{emoji} {nome}: {sinal}R${lucro:,.2f}\n"
            )

            if tipo == "crypto":
                total_lucro_crypto += lucro
                if venda_mes == mes_atual:
                    total_vendas_crypto_mes += v["valor_investido"] + lucro
            elif tipo == "acao":
                total_lucro_acoes += lucro
                if venda_mes == mes_atual:
                    total_vendas_acoes_mes += v["valor_investido"] + lucro
            elif tipo == "fii":
                total_lucro_fii += lucro

        msg += "\n"

        # ── Cálculo do IR ──
        msg += "━━━━━━━━━━━━━━━━━━━\n\n"
        msg += "🧮 **Cálculo do IR este mês:**\n\n"

        ir_total = 0.0

        # Ações
        if total_lucro_acoes != 0:
            if total_vendas_acoes_mes < 20000:
                msg += (
                    f"📈 **Ações:** Lucro R${total_lucro_acoes:,.2f}\n"
                    f"   ✅ ISENTO (vendas < R$20.000 no mês)\n"
                    f"   _Total vendido: R${total_vendas_acoes_mes:,.2f}_\n\n"
                )
            elif total_lucro_acoes > 0:
                ir_acoes = total_lucro_acoes * 0.15
                ir_total += ir_acoes
                msg += (
                    f"📈 **Ações:** Lucro R${total_lucro_acoes:,.2f}\n"
                    f"   💸 IR: **R${ir_acoes:,.2f}** (15%)\n"
                    f"   _Vendas > R$20.000 — tributável_\n\n"
                )
            else:
                msg += (
                    f"📈 **Ações:** Prejuízo R${total_lucro_acoes:,.2f}\n"
                    f"   💡 _Prejuízo pode ser compensado em meses futuros_\n\n"
                )

        # Cripto
        if total_lucro_crypto != 0:
            if total_vendas_crypto_mes < 35000:
                msg += (
                    f"🪙 **Cripto:** Lucro R${total_lucro_crypto:,.2f}\n"
                    f"   ✅ ISENTO (vendas < R$35.000 no mês)\n"
                    f"   _Total vendido: R${total_vendas_crypto_mes:,.2f}_\n\n"
                )
            elif total_lucro_crypto > 0:
                ir_crypto = total_lucro_crypto * 0.15
                ir_total += ir_crypto
                msg += (
                    f"🪙 **Cripto:** Lucro R${total_lucro_crypto:,.2f}\n"
                    f"   💸 IR: **R${ir_crypto:,.2f}** (15%)\n"
                    f"   _Vendas > R$35.000 — tributável_\n\n"
                )
            else:
                msg += (
                    f"🪙 **Cripto:** Prejuízo R${total_lucro_crypto:,.2f}\n"
                    f"   💡 _Prejuízo pode ser compensado em meses futuros_\n\n"
                )

        # FIIs
        if total_lucro_fii > 0:
            ir_fii = total_lucro_fii * 0.20
            ir_total += ir_fii
            msg += (
                f"🏢 **FIIs:** Lucro R${total_lucro_fii:,.2f}\n"
                f"   💸 IR: **R${ir_fii:,.2f}** (20%)\n"
                f"   _FIIs sempre tributam 20% sobre ganho de capital_\n\n"
            )

        if ir_total > 0:
            msg += (
                f"💰 **Total de IR a pagar: R${ir_total:,.2f}**\n"
                f"   📅 _Pagar até último dia útil do mês seguinte_\n"
                f"   📱 _Use o app SICALC da Receita Federal_\n\n"
            )
        elif vendas:
            msg += "✅ **Nenhum IR a pagar este mês!**\n\n"

    # ── LUCRO NÃO REALIZADO (posições abertas) ──
    if posicoes:
        msg += "━━━━━━━━━━━━━━━━━━━\n\n"
        msg += "📋 **Lucro NÃO realizado (se vendesse hoje):**\n\n"

        total_lucro_nr = 0.0
        total_valor_nr = 0.0

        for pos in posicoes:
            tipo = pos.get("tipo", "crypto")
            ativo = pos["ativo"]
            preco_compra = pos["preco_compra"]

            # Buscar preço atual
            preco_atual = preco_compra
            if tipo == "crypto":
                pd = await get_crypto_price(ativo)
                if pd:
                    preco_atual = pd["preco_brl"]
            else:
                sd = await get_stock_price(ativo)
                if sd:
                    preco_atual = sd["preco"]

            var_pct = (
                (preco_atual - preco_compra) / preco_compra
            ) if preco_compra else 0
            lucro = pos["valor_investido"] * var_pct

            nome = CRYPTO_NOMES.get(ativo, ativo.upper())
            emoji = "🟢" if lucro >= 0 else "🔴"
            sinal = "+" if lucro >= 0 else ""

            total_lucro_nr += lucro
            total_valor_nr += pos["valor_investido"] + lucro

            msg += (
                f"{emoji} {nome}: {sinal}R${lucro:,.2f} "
                f"({sinal}{var_pct * 100:.1f}%)\n"
            )

        msg += f"\n📊 Total não realizado: "
        sinal_nr = "+" if total_lucro_nr >= 0 else ""
        msg += f"**{sinal_nr}R${total_lucro_nr:,.2f}**\n"

        if total_lucro_nr > 0:
            # Estimar IR se vendesse tudo hoje
            ir_estimado = total_lucro_nr * 0.15
            msg += (
                f"💡 _Se vendesse tudo hoje, IR estimado: "
                f"~R${ir_estimado:,.2f}_\n"
            )

    msg += (
        "\n━━━━━━━━━━━━━━━━━━━\n"
        "📌 **Dicas de IR:**\n"
        "• Ações: isento se vendas < R$20k/mês\n"
        "• Cripto: isento se vendas < R$35k/mês\n"
        "• Prejuízo pode compensar lucro futuro\n"
        "• DARF via SICALC (código 6015 ações, 4600 cripto)\n\n"
        "⚠️ _Cálculo simplificado. Consulte um contador "
        "para declaração oficial._"
    )

    # Dividir se necessário
    if len(msg) > 4000:
        partes = []
        while msg:
            if len(msg) <= 4000:
                partes.append(msg)
                break
            corte = msg.rfind("\n", 0, 4000)
            if corte == -1:
                corte = 4000
            partes.append(msg[:corte])
            msg = msg[corte:].lstrip("\n")
        for parte in partes:
            await update.message.reply_text(parte, parse_mode="Markdown")
    else:
        await update.message.reply_text(msg, parse_mode="Markdown")


def get_ir_handlers() -> list:
    """Retorna os handlers de imposto de renda."""
    return [
        CommandHandler("ir", imposto_renda),
        CommandHandler("imposto", imposto_renda),
        CommandHandler("impostos", imposto_renda),
    ]
