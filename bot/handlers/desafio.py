"""
Handler do /desafio — Estudo de rendimento educacional.

O usuário informa quanto quer investir, o retorno desejado e o prazo.
O bot analisa o mercado ao vivo e mostra cenários educacionais com os riscos.
Conteúdo educacional — não é recomendação de investimento.

Uso:
  /desafio            — Modo guiado (passo a passo)
  /desafio 1000 100 7 — Modo rápido (investir, ganhar, dias)
"""

import asyncio
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

from services.market_analysis import (
    SINAL_EMOJI,
    SINAL_TEXTO,
    analise_completa_acao,
    analise_completa_crypto,
)

logger = logging.getLogger(__name__)

# Estados da conversa
VALOR_INVESTIR, VALOR_GANHAR, PRAZO = range(3)

# Ativos para análise ao vivo
_CRYPTOS = [
    ("bitcoin", "Bitcoin"),
    ("ethereum", "Ethereum"),
    ("solana", "Solana"),
]

_ACOES = [
    ("BOVA11", "BOVA11 (Ibovespa)"),
    ("IVVB11", "IVVB11 (S&P 500)"),
    ("WEGE3", "WEG"),
    ("PETR4", "Petrobras"),
    ("VALE3", "Vale"),
]


# ── Fluxo da conversa ─────────────────────────────────────────


async def desafio_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia o fluxo de objetivo de rendimento."""
    # Modo rápido: /desafio 1000 100 7
    if context.args and len(context.args) >= 3:
        try:
            investir = _parse_valor(context.args[0])
            ganhar = _parse_valor(context.args[1])
            dias = int(context.args[2])
            if investir and ganhar and dias > 0:
                await context.bot.send_chat_action(
                    chat_id=update.effective_chat.id, action="typing"
                )
                msg = await _montar_plano(investir, ganhar, dias)
                # Dividir se necessário (Telegram limita em 4096)
                await _enviar_msg(update, msg)
                return ConversationHandler.END
        except (ValueError, IndexError):
            pass

    await update.message.reply_text(
        "🎯 **Desafio de Rendimento**\n\n"
        "Vou analisar o mercado ao vivo e montar um plano\n"
        "para o seu objetivo!\n\n"
        "**Quanto você quer investir?**\n"
        "_(Ex: 500, 1000, 5000)_",
        parse_mode="Markdown",
    )
    return VALOR_INVESTIR


async def receber_valor_investir(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Recebe quanto o usuário quer investir."""
    valor = _parse_valor(update.message.text)

    if not valor or valor < 10:
        await update.message.reply_text(
            "❌ Valor inválido. Digite um número, ex: **1000**",
            parse_mode="Markdown",
        )
        return VALOR_INVESTIR

    context.user_data["desafio_investir"] = valor

    await update.message.reply_text(
        f"✅ Investir: **R${valor:,.2f}**\n\n"
        "**Quanto você quer ganhar em cima disso?**\n"
        "_(Ex: 50, 100, 500)_",
        parse_mode="Markdown",
    )
    return VALOR_GANHAR


async def receber_valor_ganhar(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Recebe quanto o usuário quer ganhar."""
    valor = _parse_valor(update.message.text)

    if not valor or valor <= 0:
        await update.message.reply_text(
            "❌ Valor inválido. Digite um número, ex: **100**",
            parse_mode="Markdown",
        )
        return VALOR_GANHAR

    context.user_data["desafio_ganhar"] = valor
    investir = context.user_data["desafio_investir"]
    pct = valor / investir * 100

    await update.message.reply_text(
        f"✅ Ganhar: **R${valor:,.2f}** ({pct:.1f}% de retorno)\n\n"
        "**Em quanto tempo?**",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("1 semana", callback_data="prazo_7"),
                    InlineKeyboardButton("2 semanas", callback_data="prazo_14"),
                ],
                [
                    InlineKeyboardButton("1 mês", callback_data="prazo_30"),
                    InlineKeyboardButton("3 meses", callback_data="prazo_90"),
                ],
                [
                    InlineKeyboardButton("6 meses", callback_data="prazo_180"),
                    InlineKeyboardButton("1 ano", callback_data="prazo_365"),
                ],
            ]
        ),
    )
    return PRAZO


async def receber_prazo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe o prazo e gera o plano."""
    query = update.callback_query
    await query.answer()

    dias = int(query.data.split("_")[1])
    investir = context.user_data["desafio_investir"]
    ganhar = context.user_data["desafio_ganhar"]

    await query.edit_message_text(
        "🔍 **Analisando o mercado ao vivo...**\n"
        "_(verificando 8 ativos — pode levar alguns segundos)_",
        parse_mode="Markdown",
    )

    msg = await _montar_plano(investir, ganhar, dias)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=msg,
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela o fluxo."""
    await update.message.reply_text(
        "Cancelado! Use /desafio quando quiser tentar 😊"
    )
    return ConversationHandler.END


# ── Parsing de valores ─────────────────────────────────────────


def _parse_valor(texto: str) -> float | None:
    """Parse valor do texto, aceitando formatos brasileiros."""
    texto = texto.lower().strip()
    texto = texto.replace("r$", "").replace("reais", "").replace(" ", "")

    # "mil" = × 1000
    if "mil" in texto:
        texto = texto.replace("mil", "")
        try:
            base = float(texto.replace(",", ".")) if texto else 1
            return base * 1000
        except ValueError:
            return None

    # Formato brasileiro: 1.000,50 → 1000.50
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:
        texto = texto.replace(",", ".")

    try:
        return float(texto)
    except ValueError:
        return None


# ── Classificação de risco ─────────────────────────────────────


def _classificar(pct_mensal: float) -> tuple[str, str, str, str]:
    """Classifica o objetivo por nível de risco."""
    if pct_mensal <= 1.0:
        return (
            "conservador",
            "🟢",
            "Tranquilo",
            "Alcançável com renda fixa. Risco muito baixo.",
        )
    if pct_mensal <= 3.0:
        return (
            "moderado",
            "🟡",
            "Possível",
            "Precisa de renda variável. Risco moderado.",
        )
    if pct_mensal <= 8.0:
        return (
            "arrojado",
            "🟠",
            "Difícil",
            "Alto risco. Possível, mas pode perder parte do investido.",
        )
    if pct_mensal <= 20.0:
        return (
            "agressivo",
            "🔴",
            "Muito arriscado",
            "Risco muito alto. Pode ganhar, mas pode perder metade.",
        )
    return (
        "impossivel",
        "⛔",
        "Irreal",
        "Nenhum investimento legítimo entrega isso. Cuidado com golpes!",
    )


def _label_prazo(dias: int) -> str:
    """Retorna label legível do prazo."""
    if dias <= 7:
        return "1 semana"
    if dias <= 14:
        return "2 semanas"
    if dias <= 30:
        return "1 mês"
    if dias <= 60:
        return "2 meses"
    if dias <= 90:
        return "3 meses"
    if dias <= 180:
        return "6 meses"
    return "1 ano"


# ── Montagem do plano ─────────────────────────────────────────


async def _montar_plano(
    investir: float, ganhar: float, dias: int
) -> str:
    """Monta o plano completo com análise ao vivo."""
    pct_total = ganhar / investir * 100
    pct_mensal = pct_total / max(dias / 30, 0.1)
    pct_anual = ((1 + pct_total / 100) ** (365 / dias) - 1) * 100
    prazo = _label_prazo(dias)

    nivel, emoji_n, titulo, descricao = _classificar(pct_mensal)

    msg = (
        f"🎯 **Seu Desafio de Rendimento**\n\n"
        f"💰 Investir: **R${investir:,.2f}**\n"
        f"🎯 Ganhar: **R${ganhar:,.2f}** ({pct_total:.1f}%)\n"
        f"⏰ Prazo: **{prazo}** ({dias} dias)\n"
        f"📊 Equivale a: {pct_mensal:.1f}%/mês | {pct_anual:.0f}%/ano\n\n"
        f"{emoji_n} **Avaliação: {titulo}**\n"
        f"_{descricao}_\n\n"
    )

    # Se impossível, alertar e mostrar o realista
    if nivel == "impossivel":
        msg += _bloco_impossivel(investir, dias, prazo)
        return msg

    # Alocação por nível
    aloc = _alocacao_por_nivel(nivel)

    msg += "━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"📋 **Plano de Ação:**\n\n"

    # Renda fixa
    if aloc["rf"] > 0:
        msg += _bloco_renda_fixa(investir, aloc["rf"], dias, prazo)

    # Análise ao vivo
    analises = await _analisar_mercado()

    # Ações / ETFs
    if aloc["rv"] > 0:
        msg += _bloco_acoes(investir, aloc["rv"], analises.get("acoes", []))

    # Cripto
    if aloc["crypto"] > 0:
        msg += _bloco_crypto(investir, aloc["crypto"], analises.get("crypto", []))

    # Cenários
    msg += _bloco_cenarios(investir, ganhar, prazo)

    # Regras do jogo
    msg += _bloco_regras(nivel)

    # Projeção se repetir mensalmente
    if dias >= 28:
        msg += _bloco_projecao_mensal(investir, pct_total, dias)

    # Links finais
    msg += (
        "\n━━━━━━━━━━━━━━━━━━━\n"
        "📝 /comprei — Registrar compra\n"
        "📋 /carteira — Acompanhar resultado\n"
        "🔔 /alertas — Aviso automático de venda\n"
        "📖 /comocomprar — Passo a passo educacional\n\n"
        "⚠️ _Conteúdo educacional — não é recomendação de investimento. "
        "Rentabilidade passada não garante resultados futuros. "
        "Consulte um profissional certificado pela CVM._"
    )

    return msg


def _alocacao_por_nivel(nivel: str) -> dict:
    """Retorna % de alocação por nível de risco."""
    return {
        "conservador": {"rf": 80, "rv": 15, "crypto": 5},
        "moderado": {"rf": 40, "rv": 40, "crypto": 20},
        "arrojado": {"rf": 10, "rv": 40, "crypto": 50},
        "agressivo": {"rf": 0, "rv": 30, "crypto": 70},
    }.get(nivel, {"rf": 40, "rv": 40, "crypto": 20})


# ── Blocos de texto ────────────────────────────────────────────


def _bloco_impossivel(investir: float, dias: int, prazo: str) -> str:
    """Bloco para objetivo irreal."""
    fator = dias / 30
    return (
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"💡 **O que é realista em {prazo}:**\n"
        f"Com R${investir:,.2f}:\n"
        f"• 🏦 Renda fixa: ~R${investir * 0.01 * fator:,.2f}\n"
        f"• 📈 Renda variável: ~R${investir * 0.03 * fator:,.2f} (com risco)\n"
        f"• 🪙 Cripto (alto risco): ~R${investir * 0.08 * fator:,.2f}\n\n"
        "⚠️ _Retorno acima de 5%/mês é quase sempre golpe. "
        "Construa patrimônio com paciência!_\n\n"
        "📈 /simular — Projeções realistas\n"
        "🎓 /aprender — Entenda investimentos"
    )


def _bloco_renda_fixa(
    investir: float, pct_aloc: int, dias: int, prazo: str
) -> str:
    """Bloco de renda fixa do plano."""
    valor = investir * pct_aloc / 100
    rend = valor * 0.13 / 365 * dias  # ~13% a.a.
    return (
        f"🏦 **{pct_aloc}% Renda Fixa — R${valor:,.2f}**\n"
        f"   CDB 110% CDI (~13% a.a.)\n"
        f"   Rende ~**R${rend:,.2f}** em {prazo}\n"
        f"   📱 _Nubank: Investir → Renda Fixa → CDB_\n\n"
    )


def _bloco_acoes(investir: float, pct_aloc: int, analises: list) -> str:
    """Bloco de ações/ETFs do plano."""
    valor = investir * pct_aloc / 100
    msg = f"📈 **{pct_aloc}% Ações/ETFs — R${valor:,.2f}**\n"

    if analises:
        melhores = sorted(analises, key=lambda x: x["score"], reverse=True)
        n = min(3, len(melhores))
        cada = valor / n if n else valor

        for a in melhores[:n]:
            msg += (
                f"   {a['emoji']} **{a['nome']}** — R${cada:,.2f}\n"
                f"      Preço: R${a['preco']:.2f} | "
                f"Sinal: {a['sinal_texto']} ({a['score']:+d})\n"
            )
    else:
        msg += "   BOVA11 + IVVB11 (diversificados)\n"

    msg += "   📱 _Nubank: Investir → Ações → buscar ticker_\n\n"
    return msg


def _bloco_crypto(investir: float, pct_aloc: int, analises: list) -> str:
    """Bloco de cripto do plano."""
    valor = investir * pct_aloc / 100
    msg = f"🪙 **{pct_aloc}% Cripto — R${valor:,.2f}**\n"

    if analises:
        melhores = sorted(analises, key=lambda x: x["score"], reverse=True)
        n = min(3, len(melhores))
        cada = valor / n if n else valor

        for a in melhores[:n]:
            msg += (
                f"   {a['emoji']} **{a['nome']}** — R${cada:,.2f}\n"
                f"      Preço: R${a['preco']:,.2f} | "
                f"Sinal: {a['sinal_texto']} ({a['score']:+d})\n"
            )
    else:
        msg += "   Bitcoin + Ethereum (consolidados)\n"

    msg += "   📱 _Binance: Comprar → buscar ativo → valor_\n\n"
    return msg


def _bloco_cenarios(investir: float, ganhar: float, prazo: str) -> str:
    """Bloco de cenários otimista/realista/pessimista."""
    return (
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎲 **Cenários possíveis em {prazo}:**\n"
        f"🟢 Otimista: R${investir + ganhar:,.2f} "
        f"(+R${ganhar:,.2f})\n"
        f"🟡 Realista: R${investir + ganhar * 0.5:,.2f} "
        f"(+R${ganhar * 0.5:,.2f})\n"
        f"🔴 Pessimista: R${investir - ganhar * 0.7:,.2f} "
        f"(-R${ganhar * 0.7:,.2f})\n\n"
    )


def _bloco_regras(nivel: str) -> str:
    """Bloco de regras/dicas baseado no nível."""
    regras_map = {
        "conservador": [
            "✅ Deixe render e não mexa — tempo é seu aliado",
            "📊 Renda fixa é previsível — relaxe e espere",
        ],
        "moderado": [
            "📊 Acompanhe 1x por semana, não todo dia",
            "🔀 Compre em 2 dias diferentes para diluir risco",
            "🎯 Se atingir a meta, realize parte do lucro",
        ],
        "arrojado": [
            "⚠️ Nunca invista dinheiro que precisa para contas",
            "📉 Se cair 15%+, NÃO venda no pânico",
            "🎯 Defina preço de saída ANTES de comprar",
            "🔀 Divida em 2-3 compras em dias diferentes",
        ],
        "agressivo": [
            "⚠️ Invista SÓ o que aceita perder",
            "📉 Pode cair 30%+ — tenha estômago",
            "🎯 Defina stop-loss (vender se cair X%)",
            "🔀 Divida em 3+ compras em dias diferentes",
            "🧘 Não olhe o preço a cada hora",
        ],
    }

    regras = regras_map.get(nivel, regras_map["moderado"])
    msg = "📝 **Regras do jogo:**\n"
    for r in regras:
        msg += f"{r}\n"
    return msg


def _bloco_projecao_mensal(
    investir: float, pct_total: float, dias: int
) -> str:
    """Mostra projeção se repetir o aporte mensalmente."""
    # Retorno mensal estimado (conservador: metade do alvo)
    r_mensal = (pct_total / 2) / 100 / max(dias / 30, 1)
    aporte = investir

    # Projetar 1, 3, 5 anos
    projecoes = []
    for anos in [1, 3, 5]:
        meses = anos * 12
        saldo = 0.0
        for _ in range(meses):
            saldo = saldo * (1 + r_mensal) + aporte
        projecoes.append((anos, saldo))

    msg = (
        "\n💡 **Se repetir todo mês** "
        f"(R${investir:,.0f}/mês):\n"
    )
    for anos, saldo in projecoes:
        total_aportado = investir * anos * 12
        lucro = saldo - total_aportado
        msg += (
            f"  • {anos} {'ano' if anos == 1 else 'anos'}: "
            f"**R${saldo:,.0f}** "
            f"(+R${lucro:,.0f} de lucro)\n"
        )
    msg += "  🚀 /aporte — Configurar aporte mensal automático\n"
    return msg


# ── Análise ao vivo ────────────────────────────────────────────


async def _analisar_mercado() -> dict:
    """Analisa os principais ativos em paralelo."""
    tasks = []
    for coin_id, nome in _CRYPTOS:
        tasks.append(_safe_analise_crypto(coin_id, nome))
    for ticker, nome in _ACOES:
        tasks.append(_safe_analise_acao(ticker, nome))

    resultados = await asyncio.gather(*tasks)

    n_crypto = len(_CRYPTOS)
    crypto_list = [r for r in resultados[:n_crypto] if r]
    acoes_list = [r for r in resultados[n_crypto:] if r]

    return {"crypto": crypto_list, "acoes": acoes_list}


async def _safe_analise_crypto(coin_id: str, nome: str) -> dict | None:
    """Analisa uma crypto com tratamento de erro."""
    try:
        analise = await analise_completa_crypto(coin_id)
        if not analise:
            return None
        sinal = analise["sinal"]
        return {
            "nome": nome,
            "preco": analise["preco"]["preco_brl"],
            "score": sinal["score"],
            "sinal_texto": SINAL_TEXTO.get(sinal["sinal"], "Neutro"),
            "emoji": SINAL_EMOJI.get(sinal["sinal"], "🟡"),
        }
    except Exception:
        return None


async def _safe_analise_acao(ticker: str, nome: str) -> dict | None:
    """Analisa uma ação com tratamento de erro."""
    try:
        analise = await analise_completa_acao(ticker)
        if not analise:
            return None
        sinal = analise["sinal"]
        return {
            "nome": nome,
            "preco": analise["stock"]["preco"],
            "score": sinal["score"],
            "sinal_texto": SINAL_TEXTO.get(sinal["sinal"], "Neutro"),
            "emoji": SINAL_EMOJI.get(sinal["sinal"], "🟡"),
        }
    except Exception:
        return None


# ── Utilidades ─────────────────────────────────────────────────


async def _enviar_msg(update: Update, msg: str):
    """Envia mensagem, dividindo se passar de 4000 chars."""
    if len(msg) <= 4000:
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    # Dividir em partes no último \n antes de 4000
    while msg:
        if len(msg) <= 4000:
            await update.message.reply_text(msg, parse_mode="Markdown")
            break
        corte = msg.rfind("\n", 0, 4000)
        if corte == -1:
            corte = 4000
        await update.message.reply_text(msg[:corte], parse_mode="Markdown")
        msg = msg[corte:].lstrip("\n")


# ── Handlers ───────────────────────────────────────────────────


def get_desafio_handlers() -> list:
    """Retorna os handlers do desafio de rendimento."""
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("desafio", desafio_start),
            CommandHandler("ganhar", desafio_start),
            CommandHandler("objetivo", desafio_start),
        ],
        states={
            VALOR_INVESTIR: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, receber_valor_investir
                ),
            ],
            VALOR_GANHAR: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, receber_valor_ganhar
                ),
            ],
            PRAZO: [
                CallbackQueryHandler(receber_prazo, pattern=r"^prazo_"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancelar)],
    )
    return [conv]
