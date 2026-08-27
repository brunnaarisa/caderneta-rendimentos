"""
Handler do /oquefazer — sugestões concretas de investimento com valores reais,
agora com análise de mercado em tempo real.

A feature mais valiosa do bot: diz EXATAMENTE o que fazer com o dinheiro,
com valores, ativos e proporções — e verifica se é um bom momento de compra.
"""

import asyncio
import json
import logging
import re
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from services.ai_advisor import consultar_ia
from services.cdi_service import cdi_anual, get_cdi_atual
from services.market_analysis import (
    analise_completa_acao,
    analise_completa_crypto,
    SINAL_EMOJI,
    SINAL_TEXTO,
)
from services.user_service import get_financial_context, get_or_create_user

logger = logging.getLogger(__name__)

# Estados
VALOR_DISPONIVEL, ESCOLHER_PERFIL = range(2)

# Mapeamento de palavras-chave para IDs de cripto (para análise de mercado)
_CRYPTO_KEYWORDS = {
    "bitcoin": "bitcoin",
    "btc": "bitcoin",
    "ethereum": "ethereum",
    "eth": "ethereum",
    "solana": "solana",
    "sol": "solana",
    "bnb": "binancecoin",
    "cardano": "cardano",
    "ada": "cardano",
    "dogecoin": "dogecoin",
    "doge": "dogecoin",
}

# Estratégias concretas por perfil e faixa de valor
# Cada uma diz exatamente: "com R$X, eu faria isso"
ESTRATEGIAS = {
    "conservador": {
        "nome": "Conservador",
        "emoji": "🛡️",
        "faixas": {
            "pequeno": {  # até R$500
                "acoes": [
                    {
                        "ativo": "CDB Liquidez Diária (Nubank/Inter/PagBank)",
                        "percentual": 70,
                        "porque": "Seguro, rende CDI, pode tirar quando quiser",
                    },
                    {
                        "ativo": "Tesouro Selic",
                        "percentual": 30,
                        "porque": "Mais seguro do Brasil, governo garante",
                    },
                ],
            },
            "medio": {  # R$500 a R$5.000
                "acoes": [
                    {
                        "ativo": "CDB 110% CDI (Sofisa/Daycoval)",
                        "percentual": 50,
                        "porque": "Rende 10% acima do CDI, com FGC",
                    },
                    {
                        "ativo": "Tesouro Selic",
                        "percentual": 30,
                        "porque": "Reserva de emergência ideal",
                    },
                    {
                        "ativo": "LCI ou LCA (~93% CDI)",
                        "percentual": 20,
                        "porque": "Isento de IR — rendimento líquido maior",
                    },
                ],
            },
            "grande": {  # acima de R$5.000
                "acoes": [
                    {
                        "ativo": "CDB 110-120% CDI (prazo 1-2 anos)",
                        "percentual": 40,
                        "porque": "Rendimento turbinado com FGC",
                    },
                    {
                        "ativo": "Tesouro IPCA+ 2029",
                        "percentual": 30,
                        "porque": "Protege contra inflação + ganho real de ~6%/ano",
                    },
                    {
                        "ativo": "LCI/LCA",
                        "percentual": 20,
                        "porque": "Isento de IR, ótimo para 9+ meses",
                    },
                    {
                        "ativo": "FII MXRF11 ou HGLG11",
                        "percentual": 10,
                        "porque": "Dividendos mensais isentos de IR, entrada no mundo da renda variável",
                    },
                ],
            },
        },
    },
    "moderado": {
        "nome": "Moderado",
        "emoji": "⚖️",
        "faixas": {
            "pequeno": {
                "acoes": [
                    {
                        "ativo": "CDB 100% CDI (liquidez diária)",
                        "percentual": 50,
                        "porque": "Base segura, disponível a qualquer momento",
                    },
                    {
                        "ativo": "BOVA11 (ETF do Ibovespa)",
                        "percentual": 30,
                        "porque": "Um pedaço das 80 maiores empresas do Brasil com 1 compra",
                    },
                    {
                        "ativo": "MXRF11 (FII)",
                        "percentual": 20,
                        "porque": "Dividendo mensal isento de IR (~1%/mês)",
                    },
                ],
            },
            "medio": {
                "acoes": [
                    {
                        "ativo": "CDB 110% CDI ou Tesouro IPCA+",
                        "percentual": 35,
                        "porque": "Base sólida com rendimento acima da média",
                    },
                    {
                        "ativo": "FIIs (HGLG11, KNRI11 ou XPML11)",
                        "percentual": 25,
                        "porque": "Renda mensal isenta, exposição a imóveis de qualidade",
                    },
                    {
                        "ativo": "ETF IVVB11 (S&P 500)",
                        "percentual": 20,
                        "porque": "Exposição às 500 maiores empresas dos EUA + proteção em dólar",
                    },
                    {
                        "ativo": "Ações de dividendos (ITSA4, BBAS3 ou TAEE11)",
                        "percentual": 20,
                        "porque": "Empresas consolidadas que pagam dividendos regularmente",
                    },
                ],
            },
            "grande": {
                "acoes": [
                    {
                        "ativo": "Tesouro IPCA+ 2035",
                        "percentual": 25,
                        "porque": "Proteção contra inflação de longo prazo + ganho real",
                    },
                    {
                        "ativo": "FIIs diversificados (3-4 fundos)",
                        "percentual": 25,
                        "porque": "HGLG11 (logística), XPML11 (shoppings), KNRI11 (escritórios)",
                    },
                    {
                        "ativo": "ETFs (BOVA11 + IVVB11)",
                        "percentual": 25,
                        "porque": "Diversificação Brasil + EUA em 2 compras",
                    },
                    {
                        "ativo": "Ações (WEGE3, ITSA4, BBAS3)",
                        "percentual": 15,
                        "porque": "Empresas de qualidade para longo prazo",
                    },
                    {
                        "ativo": "HASH11 (cripto via B3)",
                        "percentual": 10,
                        "porque": "Exposição a Bitcoin/Ethereum sem precisar de exchange",
                    },
                ],
            },
        },
    },
    "arrojado": {
        "nome": "Arrojado",
        "emoji": "📈",
        "faixas": {
            "pequeno": {
                "acoes": [
                    {
                        "ativo": "IVVB11 (S&P 500 EUA)",
                        "percentual": 35,
                        "porque": "Exposição ao mercado americano + dólar com 1 compra",
                    },
                    {
                        "ativo": "BOVA11 (Ibovespa)",
                        "percentual": 25,
                        "porque": "80 maiores empresas do Brasil de uma vez",
                    },
                    {
                        "ativo": "HASH11 (cripto na B3)",
                        "percentual": 15,
                        "porque": "Bitcoin + Ethereum via bolsa, sem complicação",
                    },
                    {
                        "ativo": "FII MXRF11",
                        "percentual": 15,
                        "porque": "Dividendo mensal caindo na conta",
                    },
                    {
                        "ativo": "CDB liquidez diária",
                        "percentual": 10,
                        "porque": "Reserva mínima para emergência",
                    },
                ],
            },
            "medio": {
                "acoes": [
                    {
                        "ativo": "Ações growth (WEGE3, PRIO3, RENT3)",
                        "percentual": 25,
                        "porque": "Empresas brasileiras de alto crescimento",
                    },
                    {
                        "ativo": "ETF IVVB11 (S&P 500)",
                        "percentual": 20,
                        "porque": "Apple, Google, Amazon, Tesla — tudo em 1 cota",
                    },
                    {
                        "ativo": "FIIs (HGLG11, XPML11, VISC11)",
                        "percentual": 20,
                        "porque": "Renda passiva mensal isenta de IR",
                    },
                    {
                        "ativo": "Bitcoin (BTC) direto",
                        "percentual": 10,
                        "porque": "Comprar na Binance/Mercado Bitcoin, guardar para o próximo ciclo",
                    },
                    {
                        "ativo": "Ethereum (ETH) direto",
                        "percentual": 5,
                        "porque": "Segunda maior cripto, tecnologia de contratos inteligentes",
                    },
                    {
                        "ativo": "Tesouro IPCA+ ou CDB",
                        "percentual": 20,
                        "porque": "Base segura — nunca vá 100% em risco",
                    },
                ],
            },
            "grande": {
                "acoes": [
                    {
                        "ativo": "Ações BR (WEGE3, PRIO3, ITSA4, VALE3, RENT3)",
                        "percentual": 25,
                        "porque": "Mix de crescimento + dividendos das melhores do Brasil",
                    },
                    {
                        "ativo": "BDRs/IVVB11 (EUA)",
                        "percentual": 20,
                        "porque": "Diversificação internacional + proteção cambial",
                    },
                    {
                        "ativo": "FIIs diversificados (4-5 fundos)",
                        "percentual": 15,
                        "porque": "HGLG11, XPML11, KNRI11, VISC11 — renda mensal",
                    },
                    {
                        "ativo": "Bitcoin (BTC)",
                        "percentual": 10,
                        "porque": "Reserva de valor digital, comprar e segurar 4+ anos",
                    },
                    {
                        "ativo": "Ethereum (ETH)",
                        "percentual": 5,
                        "porque": "Aposta em infraestrutura Web3",
                    },
                    {
                        "ativo": "Small Caps BR (SMLL via ETF ou ações individuais)",
                        "percentual": 5,
                        "porque": "Alto potencial de crescimento, alta volatilidade",
                    },
                    {
                        "ativo": "Renda Fixa (Tesouro IPCA+)",
                        "percentual": 20,
                        "porque": "Âncora de segurança — proteção contra inflação",
                    },
                ],
            },
        },
    },
    "agressivo": {
        "nome": "Agressivo",
        "emoji": "🚀",
        "faixas": {
            "pequeno": {
                "acoes": [
                    {
                        "ativo": "Bitcoin (BTC)",
                        "percentual": 25,
                        "porque": "Maior cripto, mais consolidada, potencial de alta expressiva",
                    },
                    {
                        "ativo": "Ethereum (ETH)",
                        "percentual": 15,
                        "porque": "Plataforma líder em contratos inteligentes",
                    },
                    {
                        "ativo": "IVVB11 (S&P 500)",
                        "percentual": 25,
                        "porque": "Big techs americanas sem precisar abrir conta fora",
                    },
                    {
                        "ativo": "Ações growth (PRIO3, WEGE3)",
                        "percentual": 25,
                        "porque": "Empresas brasileiras de alto crescimento",
                    },
                    {
                        "ativo": "CDB liquidez diária",
                        "percentual": 10,
                        "porque": "Mínimo de segurança — nunca vá 100% em risco",
                    },
                ],
            },
            "medio": {
                "acoes": [
                    {
                        "ativo": "Bitcoin (BTC)",
                        "percentual": 20,
                        "porque": "Compra parcelada mensal (DCA) para suavizar volatilidade",
                    },
                    {
                        "ativo": "Ethereum (ETH)",
                        "percentual": 10,
                        "porque": "Segunda maior cripto, forte adoção institucional",
                    },
                    {
                        "ativo": "Ações growth BR (PRIO3, WEGE3, HAPV3, RENT3)",
                        "percentual": 20,
                        "porque": "Empresas com potencial de dobrar em 3-5 anos",
                    },
                    {
                        "ativo": "Small Caps ou ETF SMLL",
                        "percentual": 10,
                        "porque": "Empresas menores com potencial de valorização explosiva",
                    },
                    {
                        "ativo": "BDRs (AAPL34, GOGL34, AMZO34)",
                        "percentual": 15,
                        "porque": "Gigantes americanas direto da B3 em reais",
                    },
                    {
                        "ativo": "FIIs de tijolo (HGLG11, XPML11)",
                        "percentual": 10,
                        "porque": "Renda mensal para equilibrar a carteira",
                    },
                    {
                        "ativo": "Renda fixa (Tesouro ou CDB)",
                        "percentual": 15,
                        "porque": "Âncora de segurança — essencial mesmo pra agressivo",
                    },
                ],
            },
            "grande": {
                "acoes": [
                    {
                        "ativo": "Bitcoin (BTC)",
                        "percentual": 15,
                        "porque": "Reserva de valor digital — compra mensal (DCA)",
                    },
                    {
                        "ativo": "Ethereum (ETH) + Solana (SOL)",
                        "percentual": 10,
                        "porque": "Infraestrutura Web3, alto risco/alto retorno",
                    },
                    {
                        "ativo": "Ações BR diversificadas (8-10 papéis)",
                        "percentual": 20,
                        "porque": "PRIO3, WEGE3, VALE3, ITSA4, RENT3, BBAS3 e mais",
                    },
                    {
                        "ativo": "Small Caps BR",
                        "percentual": 10,
                        "porque": "3-4 empresas menores com tese de crescimento",
                    },
                    {
                        "ativo": "BDRs / Conta internacional",
                        "percentual": 15,
                        "porque": "Apple, NVIDIA, Amazon, Google — exposição a dólar",
                    },
                    {
                        "ativo": "FIIs (3-4 fundos)",
                        "percentual": 10,
                        "porque": "Renda passiva mensal como colchão",
                    },
                    {
                        "ativo": "Equity Crowdfunding (Kria, SMU)",
                        "percentual": 5,
                        "porque": "Investir em startups — pode ir a zero ou multiplicar 10x",
                    },
                    {
                        "ativo": "Renda fixa (Tesouro IPCA+)",
                        "percentual": 15,
                        "porque": "Base sólida — até investidor agressivo precisa disso",
                    },
                ],
            },
        },
    },
}


def _classificar_faixa(valor: float) -> str:
    """Classifica o valor em faixa."""
    if valor < 500:
        return "pequeno"
    elif valor <= 5000:
        return "medio"
    return "grande"


def _extrair_ativos_para_analise(nome_ativo: str) -> list[dict]:
    """
    Extrai ativos analisáveis de uma string de estratégia.
    Ex: "Bitcoin (BTC)" → [{"id": "bitcoin", "tipo": "crypto"}]
    Ex: "WEGE3, PRIO3" → [{"id": "WEGE3", "tipo": "acao"}, ...]
    """
    ativos = []
    seen = set()
    nome_lower = nome_ativo.lower()

    # Detectar criptomoedas
    for keyword, coin_id in _CRYPTO_KEYWORDS.items():
        if re.search(rf"\b{re.escape(keyword)}\b", nome_lower):
            if coin_id not in seen:
                ativos.append({"id": coin_id, "tipo": "crypto"})
                seen.add(coin_id)

    # Detectar tickers B3 (4 letras + 1-2 dígitos)
    tickers = re.findall(r"\b([A-Z]{4}\d{1,2})\b", nome_ativo)
    for ticker in tickers[:2]:  # max 2 por linha para limitar chamadas
        if ticker not in seen:
            ativos.append({"id": ticker, "tipo": "acao"})
            seen.add(ticker)

    return ativos


async def _analisar_ativos_em_lote(acoes_estrategia: list[dict]) -> dict:
    """
    Analisa todos os ativos de uma estratégia em paralelo.
    Retorna {id_ativo: resultado_analise}.
    """
    todos = []
    seen = set()
    for acao in acoes_estrategia:
        for ativo in _extrair_ativos_para_analise(acao["ativo"]):
            if ativo["id"] not in seen:
                todos.append(ativo)
                seen.add(ativo["id"])

    todos = todos[:6]  # limitar chamadas

    if not todos:
        return {}

    async def _analisar(ativo):
        try:
            if ativo["tipo"] == "crypto":
                return ativo["id"], await analise_completa_crypto(ativo["id"])
            return ativo["id"], await analise_completa_acao(ativo["id"])
        except Exception as e:
            logger.warning("Erro ao analisar %s: %s", ativo["id"], e)
            return ativo["id"], None

    results = await asyncio.gather(*[_analisar(a) for a in todos])
    return {aid: res for aid, res in results if res is not None}


def _formatar_sinal_curto(ativo_id: str, tipo: str, analise: dict) -> str:
    """Formata uma linha curta com o sinal de mercado."""
    sinal_info = analise.get("sinal", {})
    sinal_nome = sinal_info.get("sinal", "NEUTRO")
    emoji = SINAL_EMOJI.get(sinal_nome, "🟡")
    texto = SINAL_TEXTO.get(sinal_nome, "Sem sinal")

    if tipo == "crypto":
        preco = analise.get("preco", {}).get("preco_brl", 0)
        mom = analise.get("momentum", {})
        rsi = mom.get("rsi_14")
        var_7d = mom.get("var_7d", 0)
        detalhes = []
        if rsi is not None:
            detalhes.append(f"RSI {rsi:.0f}")
        if var_7d:
            s = "+" if var_7d > 0 else ""
            detalhes.append(f"{s}{var_7d:.1f}% 7d")
        fg = analise.get("fear_greed")
        if fg:
            detalhes.append(f"F&G {fg['valor']}")
        det = f" ({', '.join(detalhes)})" if detalhes else ""
        return f"   {emoji} R${preco:,.2f} — {texto}{det}"
    else:
        preco = analise.get("stock", {}).get("preco", 0)
        dist = analise.get("dist_topo_52sem", 0)
        return f"   {emoji} R${preco:.2f} — {texto} ({dist:.0f}% do topo 52s)"


def _montar_plano(perfil_key: str, valor: float) -> str:
    """Monta o texto do plano (versão sem análise — fallback)."""
    estrategia = ESTRATEGIAS[perfil_key]
    faixa = _classificar_faixa(valor)
    acoes = estrategia["faixas"][faixa]["acoes"]

    linhas = []
    for acao in acoes:
        valor_acao = valor * acao["percentual"] / 100
        linhas.append(
            f"**{acao['percentual']}% → R${valor_acao:,.2f} em {acao['ativo']}**\n"
            f"   _{acao['porque']}_"
        )

    texto = (
        f"{estrategia['emoji']} **Se eu tivesse R${valor:,.2f} hoje "
        f"(perfil {estrategia['nome']}):**\n\n"
        + "\n\n".join(linhas)
        + "\n\n━━━━━━━━━━━━━━━━━━━\n\n"
        "📌 **Próximos passos concretos:**\n"
        "1. Abra conta em uma corretora (Nubank, Inter, ou XP)\n"
        "2. Transfira o valor\n"
        "3. Compre cada ativo na proporção acima\n"
        "4. Repita todo mês com o que conseguir aportar\n\n"
        "🔑 **Regra de ouro:** compre um pouco todo mês (DCA), "
        "não tente acertar o momento perfeito.\n\n"
        "⚠️ _Isso é o que eu faria — não é uma recomendação "
        "oficial de investimento. Cada pessoa tem uma situação "
        "diferente. Consulte um profissional certificado para "
        "decisões de grande valor._"
    )
    return texto


async def _montar_plano_com_analise(perfil_key: str, valor: float) -> str:
    """Monta o plano com análise de mercado em tempo real."""
    estrategia = ESTRATEGIAS[perfil_key]
    faixa = _classificar_faixa(valor)
    acoes = estrategia["faixas"][faixa]["acoes"]

    # Analisar todos os ativos em paralelo
    resultados = await _analisar_ativos_em_lote(acoes)

    linhas = []
    for acao in acoes:
        valor_acao = valor * acao["percentual"] / 100
        linha = (
            f"**{acao['percentual']}% → R${valor_acao:,.2f} em {acao['ativo']}**\n"
            f"   _{acao['porque']}_"
        )

        # Adicionar análise de mercado para cada ativo detectado
        ativos_desta = _extrair_ativos_para_analise(acao["ativo"])
        for ativo in ativos_desta:
            if ativo["id"] in resultados:
                linha += "\n" + _formatar_sinal_curto(
                    ativo["id"], ativo["tipo"], resultados[ativo["id"]]
                )

        linhas.append(linha)

    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    texto = (
        f"{estrategia['emoji']} **Se eu tivesse R${valor:,.2f} hoje "
        f"(perfil {estrategia['nome']}):**\n\n"
        + "\n\n".join(linhas)
        + "\n\n━━━━━━━━━━━━━━━━━━━\n"
    )

    if resultados:
        texto += f"📡 _Análise atualizada em {agora}_\n\n"

        # Resumo de alertas
        bom = [
            aid.upper()
            for aid, a in resultados.items()
            if a.get("sinal", {}).get("sinal") in ("COMPRA_FORTE", "COMPRA")
        ]
        cuidado = [
            aid.upper()
            for aid, a in resultados.items()
            if a.get("sinal", {}).get("sinal") in ("VENDA", "VENDA_FORTE")
        ]
        if cuidado:
            v = "está" if len(cuidado) == 1 else "estão"
            texto += (
                f"⚠️ {', '.join(cuidado)} {v} com sinal de cautela — "
                f"considere esperar ou reduzir nesses ativos.\n"
            )
        if bom:
            v = "está" if len(bom) == 1 else "estão"
            texto += f"✅ {', '.join(bom)} {v} com sinal positivo!\n"
        texto += "\n"

    texto += (
        "📌 **Próximos passos concretos:**\n"
        "1. Abra conta em uma corretora (Nubank, Inter, ou XP)\n"
        "2. Transfira o valor\n"
        "3. Compre cada ativo na proporção acima\n"
        "4. Repita todo mês com o que conseguir aportar\n\n"
        "🔑 **Regra de ouro:** compre um pouco todo mês (DCA), "
        "não tente acertar o momento perfeito.\n\n"
        "📋 /analisar [ativo] — Análise detalhada de qualquer ativo\n"
        "📝 /comprei — Registrar compra na carteira\n\n"
        "⚠️ _Isso é o que eu faria — não é recomendação oficial. "
        "Análise baseada em indicadores técnicos que não garantem "
        "resultados futuros._"
    )
    return texto


async def oquefazer_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pergunta quanto a pessoa quer investir."""
    await update.message.reply_text(
        "💰 **O que eu faria com seu dinheiro hoje**\n\n"
        "Vou te dar um plano concreto — com nomes de ativos, "
        "valores exatos e onde comprar.\n\n"
        "**Quanto você quer investir agora?**\n"
        "_(Digite o valor, ex: 100, 500, 1000, 5000)_",
        parse_mode="Markdown",
    )
    return VALOR_DISPONIVEL


async def receber_valor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe o valor e pergunta o nível de risco."""
    try:
        valor = float(
            update.message.text.replace("R$", "")
            .replace(".", "")
            .replace(",", ".")
            .strip()
        )
        if valor <= 0:
            raise ValueError
    except (ValueError, AttributeError):
        await update.message.reply_text(
            "❌ Valor inválido. Digite um número, ex: **500**",
            parse_mode="Markdown",
        )
        return VALOR_DISPONIVEL

    context.user_data["oqf_valor"] = valor

    # Verificar se já tem perfil salvo
    user = await get_or_create_user(update.effective_user.id)
    perfil_json = json.loads(user.get("perfil_json", "{}") or "{}")
    perfil_salvo = perfil_json.get("perfil_risco")

    if perfil_salvo:
        # Já tem perfil — perguntar se quer usar ou escolher outro
        await update.message.reply_text(
            f"✅ Valor: **R${valor:,.2f}**\n\n"
            f"Seu perfil salvo é **{perfil_salvo}**.\n"
            "Quer sugestões para qual nível de risco?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            f"✅ {perfil_salvo} (meu perfil)",
                            callback_data=f"oqf_{perfil_salvo.lower()}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🛡️ Conservador", callback_data="oqf_conservador"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "⚖️ Moderado", callback_data="oqf_moderado"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "📈 Arrojado", callback_data="oqf_arrojado"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🚀 Agressivo", callback_data="oqf_agressivo"
                        )
                    ],
                ]
            ),
        )
    else:
        await update.message.reply_text(
            f"✅ Valor: **R${valor:,.2f}**\n\n"
            "Qual nível de risco você aceita?\n\n"
            "🛡️ **Conservador** — segurança máxima, rendimento menor\n"
            "⚖️ **Moderado** — equilíbrio entre segurança e retorno\n"
            "📈 **Arrojado** — aceita oscilações por retornos maiores\n"
            "🚀 **Agressivo** — aceita perdas grandes por chance de ganhos altos",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🛡️ Conservador", callback_data="oqf_conservador"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "⚖️ Moderado", callback_data="oqf_moderado"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "📈 Arrojado", callback_data="oqf_arrojado"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🚀 Agressivo", callback_data="oqf_agressivo"
                        )
                    ],
                ]
            ),
        )
    return ESCOLHER_PERFIL


async def receber_perfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe o perfil e mostra o plano com análise de mercado em tempo real."""
    query = update.callback_query
    await query.answer()

    perfil_key = query.data.replace("oqf_", "")
    valor = context.user_data.get("oqf_valor", 100)

    # Avisar que está analisando (chamadas de API demoram alguns segundos)
    await query.edit_message_text(
        "🔍 **Analisando o mercado em tempo real...**\n\n"
        "_Verificando indicadores técnicos, médias móveis, RSI "
        "e Fear & Greed para montar seu plano..._",
        parse_mode="Markdown",
    )

    # Montar plano com análise de mercado
    try:
        plano = await _montar_plano_com_analise(perfil_key, valor)
    except Exception as e:
        logger.error("Erro na análise de mercado: %s", e)
        plano = _montar_plano(perfil_key, valor)

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=plano,
        parse_mode="Markdown",
    )

    # Oferecer análise IA personalizada
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=(
            "💡 Quer que eu analise **para a sua situação específica**?\n\n"
            "Me mande uma mensagem tipo:\n"
            f'_"Tenho R${valor:,.0f}, ganho R$X por mês, '
            'tenho/não tenho reserva de emergência, '
            'quero investir para Y. O que eu faço?"_\n\n'
            "Quanto mais detalhes, melhor o conselho! 🧠"
        ),
        parse_mode="Markdown",
    )

    return ConversationHandler.END


async def cancel_oqf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelado. Use /oquefazer para recomeçar.")
    return ConversationHandler.END


def get_oquefazer_handlers() -> list:
    """Retorna os handlers do /oquefazer."""
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("oquefazer", oquefazer_start),
            CommandHandler("oqf", oquefazer_start),
        ],
        states={
            VALOR_DISPONIVEL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receber_valor)
            ],
            ESCOLHER_PERFIL: [
                CallbackQueryHandler(receber_perfil, pattern=r"^oqf_")
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_oqf)],
    )
    return [conv]
