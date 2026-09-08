"""
Ferramentas financeiras avançadas:
- /painel — Dashboard financeiro completo
- /versus — Comparador de ativos ao vivo
- /aposentar — Calculadora de independência financeira
- /dicadodia — Dica financeira do dia
"""

import logging
import random
from datetime import date, datetime

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from services.market_analysis import (
    SINAL_EMOJI,
    SINAL_TEXTO,
    analise_completa_acao,
    analise_completa_crypto,
    get_crypto_price,
    get_stock_price,
)
from services.portfolio_service import CRYPTO_MAP, CRYPTO_NOMES, get_carteira_ativa
from services.user_service import (
    get_dividas,
    get_financial_context,
    get_gastos_mes,
    get_metas,
    get_or_create_user,
    get_resumo_gastos_mes,
)

logger = logging.getLogger(__name__)


# ── /painel — Dashboard financeiro ───────────────────────────


async def painel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o dashboard financeiro completo do usuário."""
    telegram_id = update.effective_user.id

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    user = await get_or_create_user(telegram_id)
    renda = user.get("renda_mensal", 0)

    # Carteira
    posicoes = await get_carteira_ativa(telegram_id)
    total_investido = 0
    total_carteira = 0
    for pos in posicoes:
        valor_inv = pos["valor_investido"]
        preco_compra = pos["preco_compra"]
        if pos["tipo"] == "crypto":
            pd = await get_crypto_price(pos["ativo"])
            preco_atual = pd["preco_brl"] if pd else preco_compra
        else:
            sd = await get_stock_price(pos["ativo"])
            preco_atual = sd["preco"] if sd else preco_compra
        var = ((preco_atual - preco_compra) / preco_compra) * 100
        total_investido += valor_inv
        total_carteira += valor_inv * (1 + var / 100)

    # Gastos do mês
    gastos = await get_resumo_gastos_mes(telegram_id)

    # Dívidas
    dividas = await get_dividas(telegram_id)
    total_dividas = sum(d["valor_total"] for d in dividas) if dividas else 0

    # Metas
    metas = await get_metas(telegram_id)

    # Plano mensal
    from services.aporte_service import get_plano_mensal

    plano = await get_plano_mensal(telegram_id)

    # ── Montar dashboard ──
    hoje = date.today().strftime("%d/%m/%Y")
    nome = user.get("nome", "Investidor")

    msg = f"📊 **Painel Financeiro** — {hoje}\n"
    msg += f"Olá, {nome}!\n\n"

    # Patrimônio
    patrimonio = total_carteira
    msg += "━━━ 💰 **PATRIMÔNIO** ━━━\n"
    if posicoes:
        lucro = total_carteira - total_investido
        emoji_p = "🟢" if lucro >= 0 else "🔴"
        sinal_p = "+" if lucro >= 0 else ""
        var_p = (lucro / total_investido * 100) if total_investido else 0
        msg += (
            f"📈 Carteira: **R${total_carteira:,.2f}**\n"
            f"   {emoji_p} {sinal_p}R${lucro:,.2f} ({sinal_p}{var_p:.1f}%)\n"
        )
    else:
        msg += "📈 Carteira: _Vazia — use /comprei para começar_\n"

    if total_dividas:
        msg += f"💳 Dívidas: **-R${total_dividas:,.2f}**\n"
        patrimonio -= total_dividas

    msg += f"\n💎 **Patrimônio líquido: R${patrimonio:,.2f}**\n\n"

    # Gastos do mês
    msg += "━━━ 💸 **GASTOS DO MÊS** ━━━\n"
    if gastos["total"] > 0:
        msg += f"Total: **R${gastos['total']:,.2f}**"
        if renda:
            pct_gasto = gastos["total"] / renda * 100
            sobra = renda - gastos["total"]
            msg += f" ({pct_gasto:.0f}% da renda)\n"
            msg += f"Sobra: R${sobra:,.2f}\n"
        else:
            msg += "\n"
        # Top 3 categorias
        cats = sorted(
            gastos["categorias"].items(), key=lambda x: x[1], reverse=True
        )
        for cat, val in cats[:3]:
            msg += f"  • {cat}: R${val:,.2f}\n"
    else:
        msg += "_Nenhum gasto registrado. Use /gasto_\n"
    msg += "\n"

    # Metas
    if metas:
        msg += "━━━ 🎯 **METAS** ━━━\n"
        for m in metas[:3]:
            pct = (m["valor_atual"] / m["valor_alvo"] * 100) if m["valor_alvo"] else 0
            barra = _barra_progresso(pct)
            msg += f"{barra} {m['nome']}: R${m['valor_atual']:,.0f}/R${m['valor_alvo']:,.0f}\n"
        msg += "\n"

    # Plano mensal
    msg += "━━━ 🤖 **STATUS** ━━━\n"
    if plano and plano.get("ativo"):
        msg += (
            f"✅ Aporte mensal: R${plano['valor_mensal']:,.2f}/mês (dia {plano['dia_pagamento']})\n"
        )
    else:
        msg += "⚠️ Sem aporte mensal — /aporte para configurar\n"

    if posicoes:
        from services.portfolio_service import get_alerta_config

        alerta = await get_alerta_config(telegram_id)
        if alerta.get("alertas_ativos"):
            msg += "🔔 Alertas: Ativados\n"
        else:
            msg += "🔕 Alertas: Desativados — /alertas\n"

    # Saúde financeira
    score = _calcular_saude_financeira(
        patrimonio, total_dividas, gastos["total"], renda, bool(plano), bool(posicoes)
    )
    msg += f"\n❤️ **Saúde financeira: {score}/10** {_emoji_saude(score)}\n"

    # Ações rápidas
    msg += (
        "\n━━━━━━━━━━━━━━━━━━━\n"
        "📋 /carteira — Detalhes da carteira\n"
        "💰 /aporte — Plano mensal\n"
        "📈 /simular — Projetar futuro\n"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")


def _barra_progresso(pct: float) -> str:
    """Gera uma barra de progresso visual."""
    pct = min(100, max(0, pct))
    filled = int(pct / 10)
    return "▓" * filled + "░" * (10 - filled) + f" {pct:.0f}%"


def _calcular_saude_financeira(
    patrimonio: float,
    dividas: float,
    gastos_mes: float,
    renda: float,
    tem_plano: bool,
    tem_carteira: bool,
) -> int:
    """Calcula um score de saúde financeira de 0 a 10."""
    score = 5  # base

    # Patrimônio positivo
    if patrimonio > 0:
        score += 1
    if patrimonio > 10000:
        score += 1

    # Dívidas
    if dividas == 0:
        score += 1
    elif renda and dividas > renda * 6:
        score -= 2

    # Taxa de poupança
    if renda and gastos_mes > 0:
        taxa_poupanca = (renda - gastos_mes) / renda
        if taxa_poupanca >= 0.2:
            score += 1
        elif taxa_poupanca < 0:
            score -= 1

    # Disciplina
    if tem_plano:
        score += 1
    if tem_carteira:
        score += 1

    return max(1, min(10, score))


def _emoji_saude(score: int) -> str:
    if score >= 8:
        return "🌟"
    if score >= 6:
        return "😊"
    if score >= 4:
        return "😐"
    return "😟"


# ── /versus — Comparador de ativos ───────────────────────────


async def versus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Compara dois ativos lado a lado com análise de mercado."""
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            "⚔️ **Comparador de Ativos**\n\n"
            "Compare dois ativos lado a lado!\n\n"
            "Use assim:\n"
            "/versus **btc eth** — Bitcoin vs Ethereum\n"
            "/versus **WEGE3 ITSA4** — Ações\n"
            "/versus **btc IVVB11** — Crypto vs ETF\n"
            "/versus **HGLG11 XPML11** — FIIs\n",
            parse_mode="Markdown",
        )
        return

    # Separar os dois ativos (aceitar "vs" no meio)
    ativos_raw = [a for a in args if a.lower() not in ("vs", "x", "ou")]
    if len(ativos_raw) < 2:
        await update.message.reply_text(
            "❌ Informe dois ativos. Ex: /versus btc eth"
        )
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    nome_a, nome_b = ativos_raw[0], ativos_raw[1]

    # Normalizar
    a_id, a_tipo = _normalizar(nome_a)
    b_id, b_tipo = _normalizar(nome_b)

    # Analisar ambos
    analise_a = await _analisar_ativo(a_id, a_tipo)
    analise_b = await _analisar_ativo(b_id, b_tipo)

    if not analise_a and not analise_b:
        await update.message.reply_text(
            "❌ Não consegui analisar nenhum dos dois ativos. "
            "Verifique os nomes/tickers."
        )
        return

    msg = "⚔️ **Comparação lado a lado**\n\n"

    # Ativo A
    msg += _formatar_comparacao(a_id, a_tipo, analise_a)
    msg += "\n**VS**\n\n"
    # Ativo B
    msg += _formatar_comparacao(b_id, b_tipo, analise_b)

    # Veredicto
    msg += "\n━━━━━━━━━━━━━━━━━━━\n"

    if analise_a and analise_b:
        score_a = analise_a.get("sinal", {}).get("score", 0)
        score_b = analise_b.get("sinal", {}).get("score", 0)
        nome_a_display = CRYPTO_NOMES.get(a_id, a_id.upper())
        nome_b_display = CRYPTO_NOMES.get(b_id, b_id.upper())

        if score_a > score_b + 10:
            msg += (
                f"🏆 **Veredito: {nome_a_display}** tem sinais mais favoráveis agora.\n"
                f"Score: {score_a:+d} vs {score_b:+d}\n"
            )
        elif score_b > score_a + 10:
            msg += (
                f"🏆 **Veredito: {nome_b_display}** tem sinais mais favoráveis agora.\n"
                f"Score: {score_b:+d} vs {score_a:+d}\n"
            )
        else:
            msg += (
                f"🤝 **Veredito: Empate técnico.** Ambos com sinais similares.\n"
                f"Score: {score_a:+d} vs {score_b:+d}\n"
            )

        msg += (
            f"\n💡 _Não precisa escolher só um! Diversificar entre os dois "
            f"reduz risco. A proporção depende do seu perfil._"
        )
    elif analise_a:
        msg += f"⚠️ Só consegui analisar {a_id.upper()}. Dados do outro indisponíveis."
    else:
        msg += f"⚠️ Só consegui analisar {b_id.upper()}. Dados do outro indisponíveis."

    await update.message.reply_text(msg, parse_mode="Markdown")


def _normalizar(nome: str) -> tuple[str, str]:
    """Normaliza nome do ativo."""
    nome_lower = nome.lower().strip()
    if nome_lower in CRYPTO_MAP:
        return CRYPTO_MAP[nome_lower], "crypto"
    if nome_lower[-1].isdigit() and len(nome_lower) >= 4:
        return nome.upper().strip(), "acao"
    return nome_lower, "crypto"


async def _analisar_ativo(ativo_id: str, tipo: str) -> dict | None:
    """Analisa um ativo."""
    try:
        if tipo == "crypto":
            return await analise_completa_crypto(ativo_id)
        return await analise_completa_acao(ativo_id)
    except Exception:
        return None


def _formatar_comparacao(ativo_id: str, tipo: str, analise: dict | None) -> str:
    """Formata a análise de um ativo para comparação."""
    nome = CRYPTO_NOMES.get(ativo_id, ativo_id.upper())

    if not analise:
        return f"❌ **{nome}** — dados indisponíveis\n"

    sinal = analise.get("sinal", {})
    sinal_nome = sinal.get("sinal", "NEUTRO")
    emoji = SINAL_EMOJI.get(sinal_nome, "🟡")
    texto = SINAL_TEXTO.get(sinal_nome, "Neutro")
    score = sinal.get("score", 0)

    if tipo == "crypto":
        preco = analise.get("preco", {}).get("preco_brl", 0)
        mom = analise.get("momentum", {})
        var_7d = mom.get("var_7d", 0)
        var_30d = mom.get("var_30d", 0)
        rsi = mom.get("rsi_14", 50)

        resultado = (
            f"{emoji} **{nome}**\n"
            f"💰 R${preco:,.2f}\n"
            f"📊 7d: {var_7d:+.1f}% | 30d: {var_30d:+.1f}%\n"
            f"📉 RSI: {rsi:.0f}"
        )
        if rsi > 70:
            resultado += " (sobrecomprado ⚠️)"
        elif rsi < 30:
            resultado += " (sobrevendido 🟢)"
        resultado += f"\n🎯 Sinal: **{texto}** ({score:+d})\n"

        fg = analise.get("fear_greed")
        if fg:
            resultado += f"😰 Fear&Greed: {fg['valor']} ({fg['classificacao']})\n"
    else:
        stock = analise.get("stock", {})
        preco = stock.get("preco", 0)
        var_dia = stock.get("variacao_dia", 0)
        dist_topo = analise.get("dist_topo_52sem", 0)

        resultado = (
            f"{emoji} **{nome}** ({stock.get('ticker', ativo_id)})\n"
            f"💰 R${preco:.2f}\n"
            f"📊 Hoje: {var_dia:+.1f}% | Topo 52s: -{dist_topo:.0f}%\n"
            f"🎯 Sinal: **{texto}** ({score:+d})\n"
        )

    return resultado


# ── /aposentar — Independência financeira ────────────────────


async def aposentar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Calcula quando o usuário pode alcançar independência financeira."""
    telegram_id = update.effective_user.id
    user = await get_or_create_user(telegram_id)
    renda = user.get("renda_mensal", 0)

    # Tentar pegar dados do plano e carteira
    from services.aporte_service import get_plano_mensal

    plano = await get_plano_mensal(telegram_id)
    posicoes = await get_carteira_ativa(telegram_id)

    gastos = await get_resumo_gastos_mes(telegram_id)
    gasto_mensal = gastos["total"] if gastos["total"] > 0 else (renda * 0.7 if renda else 3000)

    patrimonio_atual = 0
    for pos in posicoes:
        patrimonio_atual += pos["valor_investido"]

    aporte_mensal = plano["valor_mensal"] if plano else 0

    if not aporte_mensal and not renda:
        await update.message.reply_text(
            "🏖️ **Calculadora de Independência Financeira**\n\n"
            "Para calcular quando você pode parar de trabalhar, "
            "preciso saber:\n\n"
            "/aporte — Configure seu aporte mensal\n"
            "Ou me diga: quanto gasta por mês e quanto investe?\n\n"
            "Exemplo: _\"Gasto R$3000/mês e invisto R$500/mês\"_",
            parse_mode="Markdown",
        )
        return

    if not aporte_mensal:
        aporte_mensal = renda * 0.1  # estimar 10% da renda

    # Cálculo de independência financeira
    # Regra dos 4%: precisa de 25x os gastos anuais
    gasto_anual = gasto_mensal * 12
    meta_fire = gasto_anual * 25  # FIRE number

    # Regra mais conservadora para o Brasil: 3.5% (taxa real)
    meta_conservadora = gasto_anual / 0.035

    # Calcular tempo necessário
    retorno_anual = 0.10  # 10% real estimado
    r_mensal = (1 + retorno_anual) ** (1 / 12) - 1

    meses_fire = _meses_para_meta(patrimonio_atual, aporte_mensal, r_mensal, meta_fire)
    meses_conserv = _meses_para_meta(patrimonio_atual, aporte_mensal, r_mensal, meta_conservadora)

    anos_fire = meses_fire / 12
    anos_conserv = meses_conserv / 12

    idade_fire = None
    # Tentar estimar idade (não temos, mas podemos estimar)

    msg = (
        "🏖️ **Calculadora de Independência Financeira**\n\n"
        f"📊 **Seus números:**\n"
        f"💰 Patrimônio atual: R${patrimonio_atual:,.2f}\n"
        f"📈 Aporte mensal: R${aporte_mensal:,.2f}\n"
        f"💸 Gasto mensal estimado: R${gasto_mensal:,.2f}\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎯 **Quanto você precisa:**\n"
        f"Para viver de renda passiva sem trabalhar:\n\n"
        f"📌 Regra dos 4% (padrão): **R${meta_fire:,.0f}**\n"
        f"   _(rende ~R${gasto_mensal:,.0f}/mês sem acabar)_\n\n"
        f"📌 Conservador (3.5%): **R${meta_conservadora:,.0f}**\n"
        f"   _(mais seguro para o Brasil)_\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"⏰ **Quando você chega lá:**\n"
    )

    if meses_fire < 600:  # menos de 50 anos
        msg += f"📅 Pela regra dos 4%: **{anos_fire:.1f} anos** (~{meses_fire:.0f} meses)\n"
        msg += f"📅 Conservador: **{anos_conserv:.1f} anos** (~{meses_conserv:.0f} meses)\n\n"
    else:
        msg += "📅 Com o aporte atual, vai demorar muito.\n\n"

    # Cenários de aceleração
    msg += "🚀 **Como acelerar:**\n"

    for mult, label in [(2, "Dobrar"), (3, "Triplicar")]:
        novo_aporte = aporte_mensal * mult
        meses = _meses_para_meta(patrimonio_atual, novo_aporte, r_mensal, meta_fire)
        if meses < 600:
            msg += (
                f"  • {label} o aporte (R${novo_aporte:,.0f}/mês): "
                f"**{meses/12:.1f} anos**\n"
            )

    # Dica motivacional
    msg += (
        f"\n━━━━━━━━━━━━━━━━━━━\n"
        f"💡 **Dica:** cada R$100/mês a mais que você investe, "
        f"corta **{_anos_cortados(aporte_mensal, 100, r_mensal, meta_fire):.1f} anos** "
        f"do tempo até a independência.\n\n"
        f"📈 /simular — Projetar patrimônio\n"
        f"💰 /aporte — {'Alterar' if plano else 'Configurar'} aporte mensal"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")


def _meses_para_meta(
    pv: float, pmt: float, r: float, fv: float
) -> float:
    """Calcula quantos meses de aporte para atingir uma meta."""
    if pmt <= 0:
        return 999
    if pv >= fv:
        return 0

    # Fórmula iterativa (mais segura que logarítmica para edge cases)
    saldo = pv
    meses = 0
    while saldo < fv and meses < 1200:  # max 100 anos
        saldo = saldo * (1 + r) + pmt
        meses += 1
    return meses


def _anos_cortados(
    aporte_atual: float, extra: float, r: float, meta: float
) -> float:
    """Calcula quantos anos a menos com um aporte extra."""
    meses_sem = _meses_para_meta(0, aporte_atual, r, meta)
    meses_com = _meses_para_meta(0, aporte_atual + extra, r, meta)
    return (meses_sem - meses_com) / 12


# ── /dicadodia — Dica financeira do dia ──────────────────────

DICAS_FINANCEIRAS = [
    "💡 Pague-se primeiro: separe o dinheiro para investir ANTES de gastar, não depois.",
    "💡 A regra 50/30/20: 50% para necessidades, 30% para desejos, 20% para investir.",
    "💡 Reserva de emergência = 6 meses de gastos em CDB liquidez diária ou Tesouro Selic.",
    "💡 Juros compostos são a 8ª maravilha do mundo. R$500/mês a 12% a.a. = R$1,2 milhão em 30 anos.",
    "💡 Não tente acertar o timing do mercado. Compre todo mês (DCA) e deixe o tempo fazer o trabalho.",
    "💡 CDB que rende 100% do CDI é o mínimo aceitável. Procure 110%+ CDI nos bancos digitais.",
    "💡 LCI e LCA são isentas de Imposto de Renda. Um LCA de 90% CDI rende mais que um CDB de 100% CDI.",
    "💡 FIIs pagam dividendos mensais isentos de IR. É como ser dono de imóveis sem a dor de cabeça.",
    "💡 ETFs como BOVA11 e IVVB11 diversificam em centenas de empresas com uma única compra.",
    "💡 A dívida do cartão de crédito cobra ~15% ao MÊS. Quite ANTES de pensar em investir.",
    "💡 Nunca invista dinheiro que você vai precisar nos próximos 6 meses. Esse é seu colchão de segurança.",
    "💡 Bitcoin nunca ficou no prejuízo para quem segurou por mais de 4 anos. Paciência é a chave.",
    "💡 Diversificação: não coloque todos os ovos na mesma cesta. Misture renda fixa, ações, FIIs e cripto.",
    "💡 O maior risco é não investir. A inflação come ~6% do seu dinheiro ao ano debaixo do colchão.",
    "💡 Antes de investir, quite dívidas com juros acima de 1% ao mês. Nenhum investimento ganha disso.",
    "💡 Tesouro IPCA+ protege contra inflação. É o investimento mais seguro para longo prazo no Brasil.",
    "💡 Corretoras como Nubank e Inter não cobram corretagem. Não pague para investir.",
    "💡 Metas claras motivam: 'R$10.000 em 1 ano' funciona melhor que 'quero economizar'.",
    "💡 Investir R$10/dia = R$300/mês = R$170.000 em 20 anos (a 10% a.a.). Todo valor conta!",
    "💡 O melhor momento para começar a investir foi ontem. O segundo melhor é hoje.",
    "💡 Automação é a chave: configure transferência automática no dia do salário → conta de investimentos.",
    "💡 Acompanhe seus investimentos 1x por semana, não 5x por dia. Ansiedade faz você vender na hora errada.",
    "💡 Se um 'investimento' promete retorno fixo acima de 2% ao mês, é golpe. Desconfie SEMPRE.",
    "💡 FGTS rende 3% ao ano + TR. Se puder sacar e investir, rende muito mais em qualquer CDB.",
    "💡 Poupança rende ~6% ao ano. CDB e Tesouro rendem ~12%+. A diferença em 10 anos é enorme.",
    "💡 Imposto de Renda sobre investimentos é regressivo: quanto mais tempo segura, menos paga (de 22,5% a 15%).",
    "💡 Aportar R$100 extra por mês pode significar aposentar 3-5 anos mais cedo. Vale o café a menos.",
    "💡 Subscrição de FIIs: quando abre, compre com desconto. É como promoção de imóvel.",
    "💡 RSI abaixo de 30 = ativo sobrevendido (possível oportunidade). Acima de 70 = sobrecomprado (cuidado).",
    "💡 Não venda no pânico. As maiores altas da bolsa acontecem logo depois das maiores quedas.",
]


async def dica_do_dia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envia uma dica financeira do dia."""
    # Usar o dia do ano como índice para consistência
    indice = date.today().timetuple().tm_yday % len(DICAS_FINANCEIRAS)
    dica = DICAS_FINANCEIRAS[indice]

    await update.message.reply_text(
        f"📚 **Dica do Dia**\n\n{dica}\n\n"
        "🎓 /aprender — Curso completo do zero\n"
        "📊 /oquefazer — O que comprar hoje",
        parse_mode="Markdown",
    )


# ── Handlers ─────────────────────────────────────────────────


def get_ferramentas_handlers() -> list:
    """Retorna os handlers das ferramentas."""
    return [
        CommandHandler("painel", painel),
        CommandHandler("dashboard", painel),
        CommandHandler("versus", versus),
        CommandHandler("vs", versus),
        CommandHandler("aposentar", aposentar),
        CommandHandler("independencia", aposentar),
        CommandHandler("fire", aposentar),
        CommandHandler("dicadodia", dica_do_dia),
        CommandHandler("dica", dica_do_dia),
    ]
