"""
Handler de evolução/histórico da carteira.

/evolucao — Mostra a evolução da carteira ao longo do tempo
/snapshot — Salva um snapshot manual da carteira

O sistema também salva snapshots diários automáticos via job.
"""

import datetime
import logging

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from database.db import get_db
from services.market_analysis import get_crypto_price, get_stock_price
from services.portfolio_service import CRYPTO_NOMES, get_carteira_ativa

logger = logging.getLogger(__name__)


# ── Serviço de snapshots ────────────────────────────────────


async def salvar_snapshot(telegram_id: int) -> dict | None:
    """
    Calcula e salva um snapshot do valor da carteira agora.
    Retorna o snapshot salvo ou None se não tem posições.
    """
    posicoes = await get_carteira_ativa(telegram_id)
    if not posicoes:
        return None

    total_investido = 0.0
    total_atual = 0.0

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

    lucro = total_atual - total_investido
    hoje = datetime.date.today().isoformat()

    db = await get_db()
    try:
        # Verificar se já tem snapshot de hoje
        cursor = await db.execute(
            "SELECT id FROM portfolio_snapshots "
            "WHERE telegram_id = ? AND data = ?",
            (telegram_id, hoje),
        )
        existing = await cursor.fetchone()

        if existing:
            await db.execute(
                "UPDATE portfolio_snapshots SET valor_total = ?, "
                "lucro_total = ?, num_ativos = ? "
                "WHERE telegram_id = ? AND data = ?",
                (total_atual, lucro, len(posicoes), telegram_id, hoje),
            )
        else:
            await db.execute(
                "INSERT INTO portfolio_snapshots "
                "(telegram_id, data, valor_total, lucro_total, num_ativos) "
                "VALUES (?, ?, ?, ?, ?)",
                (telegram_id, hoje, total_atual, lucro, len(posicoes)),
            )
        await db.commit()

        return {
            "data": hoje,
            "valor_total": total_atual,
            "lucro_total": lucro,
            "investido": total_investido,
            "num_ativos": len(posicoes),
        }
    finally:
        await db.close()


async def get_snapshots(
    telegram_id: int, dias: int = 30
) -> list[dict]:
    """Retorna os snapshots dos últimos N dias."""
    db = await get_db()
    try:
        data_inicio = (
            datetime.date.today() - datetime.timedelta(days=dias)
        ).isoformat()
        cursor = await db.execute(
            "SELECT * FROM portfolio_snapshots "
            "WHERE telegram_id = ? AND data >= ? "
            "ORDER BY data ASC",
            (telegram_id, data_inicio),
        )
        return [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()


# ── Handlers ─────────────────────────────────────────────────


async def evolucao_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /evolucao — Mostra a evolução da carteira ao longo do tempo.
    Inclui gráfico ASCII e estatísticas.
    """
    telegram_id = update.effective_user.id

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    # Salvar snapshot atualizado de hoje
    snap_hoje = await salvar_snapshot(telegram_id)
    if not snap_hoje:
        await update.message.reply_text(
            "📈 **Evolução da Carteira**\n\n"
            "Você ainda não tem posições registradas.\n"
            "Use /comprei para registrar suas compras!\n\n"
            "Assim que tiver, vou acompanhar a evolução diária.",
            parse_mode="Markdown",
        )
        return

    # Buscar histórico
    dias = 30
    if context.args:
        try:
            dias = int(context.args[0])
            dias = max(7, min(365, dias))
        except ValueError:
            pass

    snapshots = await get_snapshots(telegram_id, dias)

    msg = f"📈 **Evolução da Carteira — {dias} dias**\n\n"

    # Status atual
    emoji = "🟢" if snap_hoje["lucro_total"] >= 0 else "🔴"
    sinal = "+" if snap_hoje["lucro_total"] >= 0 else ""
    var_pct = (
        (snap_hoje["lucro_total"] / snap_hoje["investido"] * 100)
        if snap_hoje["investido"]
        else 0
    )

    msg += (
        f"💼 **Agora:**\n"
        f"   Investido: R${snap_hoje['investido']:,.2f}\n"
        f"   Valor atual: R${snap_hoje['valor_total']:,.2f}\n"
        f"   {emoji} Resultado: {sinal}R${snap_hoje['lucro_total']:,.2f} "
        f"({sinal}{var_pct:.1f}%)\n"
        f"   📊 {snap_hoje['num_ativos']} ativo(s)\n\n"
    )

    if len(snapshots) >= 2:
        # Gráfico ASCII
        valores = [s["valor_total"] for s in snapshots]
        msg += _gerar_grafico_ascii(valores, snapshots) + "\n"

        # Estatísticas de evolução
        primeiro = snapshots[0]
        ultimo = snapshots[-1]
        var_periodo = ultimo["valor_total"] - primeiro["valor_total"]
        var_pct_periodo = (
            (var_periodo / primeiro["valor_total"] * 100)
            if primeiro["valor_total"]
            else 0
        )

        melhor = max(snapshots, key=lambda s: s["valor_total"])
        pior = min(snapshots, key=lambda s: s["valor_total"])

        emoji_p = "🟢" if var_periodo >= 0 else "🔴"
        sinal_p = "+" if var_periodo >= 0 else ""

        msg += (
            f"📊 **Estatísticas ({len(snapshots)} registros):**\n"
            f"   {emoji_p} Variação: {sinal_p}R${var_periodo:,.2f} "
            f"({sinal_p}{var_pct_periodo:.1f}%)\n"
            f"   📈 Máximo: R${melhor['valor_total']:,.2f} ({melhor['data'][5:]})\n"
            f"   📉 Mínimo: R${pior['valor_total']:,.2f} ({pior['data'][5:]})\n\n"
        )

        # Tendência
        if len(snapshots) >= 7:
            ultimos_7 = snapshots[-7:]
            var_7d = ultimos_7[-1]["valor_total"] - ultimos_7[0]["valor_total"]
            emoji_7 = "📈" if var_7d >= 0 else "📉"
            sinal_7 = "+" if var_7d >= 0 else ""
            msg += (
                f"   {emoji_7} Últimos 7 dias: {sinal_7}R${var_7d:,.2f}\n"
            )
    else:
        msg += (
            "📊 _Poucos dados ainda. Snapshots diários são salvos "
            "automaticamente. Volte em alguns dias para ver o gráfico!_\n\n"
        )

    msg += (
        "\n━━━━━━━━━━━━━━━━━━━\n"
        "📋 /carteira — Posições detalhadas\n"
        "📊 /ir — Imposto de Renda\n"
        "🏆 /compartilhar — Compartilhar resultados"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")


def _gerar_grafico_ascii(valores: list[float], snapshots: list[dict]) -> str:
    """Gera um gráfico ASCII da evolução da carteira."""
    if not valores:
        return ""

    altura = 8
    largura = min(len(valores), 30)

    # Se temos mais pontos que a largura, fazer amostragem
    if len(valores) > largura:
        step = len(valores) / largura
        valores_amostrados = [
            valores[int(i * step)] for i in range(largura)
        ]
        datas_amostrados = [
            snapshots[int(i * step)]["data"] for i in range(largura)
        ]
    else:
        valores_amostrados = valores
        datas_amostrados = [s["data"] for s in snapshots]

    v_min = min(valores_amostrados)
    v_max = max(valores_amostrados)
    v_range = v_max - v_min if v_max > v_min else 1

    grafico = "```\n"

    for row in range(altura, -1, -1):
        threshold = v_min + (v_range * row / altura)
        line = ""
        for val in valores_amostrados:
            if val >= threshold:
                line += "█"
            else:
                line += " "

        # Labels no eixo Y
        if row == altura:
            label = f"R${v_max:>10,.0f} │"
        elif row == 0:
            label = f"R${v_min:>10,.0f} │"
        elif row == altura // 2:
            mid = (v_max + v_min) / 2
            label = f"R${mid:>10,.0f} │"
        else:
            label = "             │"

        grafico += f"{label}{line}\n"

    # Eixo X
    grafico += "             └" + "─" * len(valores_amostrados) + "\n"

    # Labels do eixo X
    if len(datas_amostrados) >= 2:
        primeira = datas_amostrados[0][5:]  # MM-DD
        ultima = datas_amostrados[-1][5:]
        espacos = max(0, len(valores_amostrados) - len(primeira) - len(ultima))
        grafico += f"              {primeira}" + " " * espacos + f"{ultima}\n"

    grafico += "```"
    return grafico


async def snapshot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/snapshot — Salva um snapshot manual da carteira."""
    telegram_id = update.effective_user.id
    snap = await salvar_snapshot(telegram_id)

    if not snap:
        await update.message.reply_text(
            "📸 Nenhuma posição para salvar.\n"
            "Use /comprei para registrar compras primeiro."
        )
        return

    emoji = "🟢" if snap["lucro_total"] >= 0 else "🔴"
    sinal = "+" if snap["lucro_total"] >= 0 else ""

    await update.message.reply_text(
        f"📸 **Snapshot salvo!**\n\n"
        f"📅 {snap['data']}\n"
        f"💰 Valor: R${snap['valor_total']:,.2f}\n"
        f"{emoji} Resultado: {sinal}R${snap['lucro_total']:,.2f}\n"
        f"📊 {snap['num_ativos']} ativo(s)\n\n"
        f"📈 /evolucao — Ver gráfico completo",
        parse_mode="Markdown",
    )


def get_evolucao_handlers() -> list:
    """Retorna os handlers de evolução."""
    return [
        CommandHandler("evolucao", evolucao_cmd),
        CommandHandler("historico", evolucao_cmd),
        CommandHandler("performance", evolucao_cmd),
        CommandHandler("snapshot", snapshot_cmd),
    ]
