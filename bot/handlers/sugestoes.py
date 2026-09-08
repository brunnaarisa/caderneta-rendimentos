"""Handler do /sugestoes — sugestões de investimento por perfil de risco."""

import json
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from services.ai_advisor import consultar_ia
from services.cdi_service import cdi_anual, get_cdi_atual
from services.user_service import get_financial_context, get_or_create_user

logger = logging.getLogger(__name__)

# Catálogo de classes de investimento por nível de risco
INVESTIMENTOS = {
    "conservador": [
        {
            "nome": "CDB 100-110% CDI",
            "tipo": "Renda Fixa",
            "risco": "🟢 Muito baixo",
            "retorno_esperado": "~13-15% ao ano",
            "prazo_minimo": "1 dia a 2 anos",
            "descricao": (
                "Título de banco com rendimento atrelado ao CDI. "
                "Protegido pelo FGC até R$250 mil. "
                "Ideal para reserva de emergência e curto prazo."
            ),
            "onde": "Nubank, Inter, Sofisa, PagBank, BTG",
            "valor_minimo": "A partir de R$1",
        },
        {
            "nome": "Tesouro Selic",
            "tipo": "Renda Fixa",
            "risco": "🟢 Muito baixo",
            "retorno_esperado": "~13% ao ano (Selic)",
            "prazo_minimo": "Liquidez D+1",
            "descricao": (
                "Título do governo federal. O investimento mais seguro do Brasil. "
                "Ideal para reserva de emergência."
            ),
            "onde": "Tesouro Direto (qualquer corretora)",
            "valor_minimo": "A partir de R$30",
        },
        {
            "nome": "LCI / LCA",
            "tipo": "Renda Fixa",
            "risco": "🟢 Baixo",
            "retorno_esperado": "~90-95% CDI (mas isento de IR!)",
            "prazo_minimo": "9 meses a 2 anos",
            "descricao": (
                "Como um CDB, mas ISENTO de Imposto de Renda. "
                "O rendimento líquido costuma ser maior que CDB. "
                "Protegido pelo FGC."
            ),
            "onde": "Inter, BTG, Daycoval, XP",
            "valor_minimo": "A partir de R$50-1.000",
        },
    ],
    "moderado": [
        {
            "nome": "CDB 120-140% CDI",
            "tipo": "Renda Fixa",
            "risco": "🟢 Baixo",
            "retorno_esperado": "~16-19% ao ano",
            "prazo_minimo": "1 a 3 anos (sem liquidez)",
            "descricao": (
                "CDBs de bancos médios que pagam mais que os grandes. "
                "Protegido pelo FGC. Risco: dinheiro preso até o vencimento."
            ),
            "onde": "Daycoval, Paraná Banco, Master (via XP, BTG, Inter)",
            "valor_minimo": "A partir de R$1.000",
        },
        {
            "nome": "Tesouro IPCA+",
            "tipo": "Renda Fixa",
            "risco": "🟡 Baixo a médio",
            "retorno_esperado": "IPCA + 6-7% ao ano",
            "prazo_minimo": "5+ anos (ideal até vencimento)",
            "descricao": (
                "Protege contra inflação + ganho real. Pode oscilar no "
                "curto prazo (marcação a mercado), mas no vencimento entrega "
                "o combinado. Ótimo para aposentadoria e metas longas."
            ),
            "onde": "Tesouro Direto",
            "valor_minimo": "A partir de R$30",
        },
        {
            "nome": "Fundos Imobiliários (FIIs)",
            "tipo": "Renda Variável",
            "risco": "🟡 Médio",
            "retorno_esperado": "~8-12% ao ano (dividendos + valorização)",
            "prazo_minimo": "2+ anos",
            "descricao": (
                "Cotas de fundos que investem em imóveis (shoppings, galpões, "
                "escritórios). Pagam dividendos MENSAIS isentos de IR. "
                "Preço da cota oscila na bolsa."
            ),
            "onde": "B3 via qualquer corretora (KNRI11, HGLG11, MXRF11...)",
            "valor_minimo": "A partir de ~R$10 por cota",
        },
        {
            "nome": "Debêntures Incentivadas",
            "tipo": "Renda Fixa",
            "risco": "🟡 Médio",
            "retorno_esperado": "IPCA + 7-9% ao ano",
            "prazo_minimo": "2 a 5 anos",
            "descricao": (
                "Títulos de empresas de infraestrutura. Isentos de IR. "
                "Rendem mais que Tesouro, mas sem garantia do FGC. "
                "Risco de crédito da empresa emissora."
            ),
            "onde": "XP, BTG, Inter, Rico",
            "valor_minimo": "A partir de R$1.000",
        },
    ],
    "arrojado": [
        {
            "nome": "Ações (Blue Chips)",
            "tipo": "Renda Variável",
            "risco": "🟠 Médio a alto",
            "retorno_esperado": "~15-25% ao ano (histórico longo prazo)",
            "prazo_minimo": "3+ anos",
            "descricao": (
                "Ações de empresas grandes e consolidadas (Petrobras, Vale, "
                "Itaú, WEG). Pagam dividendos e tendem a valorizar no longo "
                "prazo. Podem cair 20-40% no curto prazo."
            ),
            "onde": "B3 via qualquer corretora",
            "valor_minimo": "A partir de ~R$5 por ação",
        },
        {
            "nome": "ETFs (Fundos de Índice)",
            "tipo": "Renda Variável",
            "risco": "🟠 Médio a alto",
            "retorno_esperado": "~12-20% ao ano (segue o índice)",
            "prazo_minimo": "3+ anos",
            "descricao": (
                "Compra um \"pacote\" de ações de uma vez. BOVA11 replica o "
                "Ibovespa, IVVB11 replica o S&P 500 (EUA). Diversificação "
                "automática com uma única compra."
            ),
            "onde": "B3 (BOVA11, IVVB11, HASH11...)",
            "valor_minimo": "A partir de ~R$10 por cota",
        },
        {
            "nome": "Ações de Dividendos",
            "tipo": "Renda Variável",
            "risco": "🟠 Médio",
            "retorno_esperado": "~6-10% ao ano em dividendos + valorização",
            "prazo_minimo": "2+ anos",
            "descricao": (
                "Ações de empresas que distribuem lucros regularmente "
                "(Taesa, BB Seguridade, Itaúsa). Renda passiva recorrente. "
                "Dividendos isentos de IR para pessoa física."
            ),
            "onde": "B3 via qualquer corretora",
            "valor_minimo": "A partir de ~R$5 por ação",
        },
        {
            "nome": "BDRs (Ações internacionais)",
            "tipo": "Renda Variável",
            "risco": "🟠 Médio a alto",
            "retorno_esperado": "Variável (exposição ao dólar + empresa)",
            "prazo_minimo": "3+ anos",
            "descricao": (
                "Investir em Apple, Google, Amazon, Tesla direto da B3 em "
                "reais. Protege contra desvalorização do real. "
                "Oscila com câmbio + mercado americano."
            ),
            "onde": "B3 (AAPL34, GOGL34, AMZO34...)",
            "valor_minimo": "A partir de ~R$20 por BDR",
        },
    ],
    "agressivo": [
        {
            "nome": "Small Caps",
            "tipo": "Renda Variável",
            "risco": "🔴 Alto",
            "retorno_esperado": "~20-50% ao ano (com alta volatilidade)",
            "prazo_minimo": "5+ anos",
            "descricao": (
                "Ações de empresas menores com alto potencial de crescimento. "
                "Podem multiplicar de valor, mas também podem cair muito. "
                "Exige estudo e estômago forte."
            ),
            "onde": "B3 via qualquer corretora",
            "valor_minimo": "A partir de ~R$1 por ação",
        },
        {
            "nome": "Criptomoedas (BTC, ETH)",
            "tipo": "Cripto",
            "risco": "🔴 Muito alto",
            "retorno_esperado": "Imprevisível (histórico: +100% a -70% ao ano)",
            "prazo_minimo": "4+ anos (ciclos de mercado)",
            "descricao": (
                "Bitcoin e Ethereum são os mais consolidados. Alta "
                "volatilidade: podem dobrar ou cair pela metade em meses. "
                "Não invista mais do que pode perder."
            ),
            "onde": "Mercado Bitcoin, Binance, Coinbase, HASH11 (ETF na B3)",
            "valor_minimo": "A partir de R$1",
        },
        {
            "nome": "COE (Certificado de Operações Estruturadas)",
            "tipo": "Estruturado",
            "risco": "🔴 Alto",
            "retorno_esperado": "Depende da estrutura (pode ser 0% a 30%+)",
            "prazo_minimo": "1 a 3 anos",
            "descricao": (
                "Produto que combina renda fixa + variável. Alguns têm "
                "capital protegido (você não perde o investido). "
                "Retorno atrelado a ações, dólar, ou índices."
            ),
            "onde": "XP, BTG, Itaú, Bradesco",
            "valor_minimo": "A partir de R$1.000-5.000",
        },
        {
            "nome": "Venture Capital / Startups",
            "tipo": "Alternativo",
            "risco": "🔴 Muito alto",
            "retorno_esperado": "Imprevisível (pode 10x ou ir a zero)",
            "prazo_minimo": "5-10 anos",
            "descricao": (
                "Investir em startups em estágio inicial via plataformas de "
                "equity crowdfunding. Altíssimo risco, mas potencial de "
                "retornos exponenciais se a empresa decolar."
            ),
            "onde": "Kria, StartMeUp, SMU Investimentos, Bossanova",
            "valor_minimo": "A partir de R$1.000",
        },
    ],
}

# Carteira sugerida por perfil (% de alocação)
CARTEIRAS = {
    "Conservador": {
        "alocacao": [
            ("Renda Fixa pós-fixada (CDB/Tesouro Selic)", 70),
            ("Renda Fixa inflação (IPCA+)", 20),
            ("Fundos Imobiliários", 10),
        ],
        "resumo": "Foco em segurança e liquidez, com uma pitada de renda variável.",
    },
    "Moderado": {
        "alocacao": [
            ("Renda Fixa pós-fixada", 40),
            ("Renda Fixa inflação (IPCA+)", 25),
            ("Fundos Imobiliários", 20),
            ("Ações / ETFs", 15),
        ],
        "resumo": "Equilíbrio entre segurança e crescimento do patrimônio.",
    },
    "Arrojado": {
        "alocacao": [
            ("Renda Fixa (reserva + IPCA+)", 30),
            ("Ações / ETFs", 30),
            ("Fundos Imobiliários", 20),
            ("BDRs / Internacional", 15),
            ("Cripto", 5),
        ],
        "resumo": "Busca crescimento acelerado aceitando oscilações maiores.",
    },
    "Agressivo": {
        "alocacao": [
            ("Renda Fixa (apenas reserva)", 15),
            ("Ações (blue chips + small caps)", 35),
            ("Fundos Imobiliários", 15),
            ("Internacional (BDRs/ETFs)", 20),
            ("Cripto", 10),
            ("Alternativos", 5),
        ],
        "resumo": "Máxima exposição a risco em busca de retornos altos.",
    },
}


async def sugestoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra sugestões de investimento baseadas no perfil do usuário."""
    user = await get_or_create_user(update.effective_user.id)
    perfil_json = json.loads(user.get("perfil_json", "{}") or "{}")
    perfil_nome = perfil_json.get("perfil_risco")

    if not perfil_nome:
        await update.message.reply_text(
            "🎯 Primeiro preciso conhecer seu **perfil de investidor**!\n\n"
            "Use /perfil para fazer o teste rápido (5 perguntas).\n"
            "Depois volte aqui para ver as sugestões personalizadas.",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(
        f"📋 Seu perfil: **{perfil_nome}**\n\n"
        "Escolha o que quer ver:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "📊 Carteira sugerida", callback_data="sug_carteira"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🟢 Conservador", callback_data="sug_conservador"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⚖️ Moderado", callback_data="sug_moderado"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "📈 Arrojado", callback_data="sug_arrojado"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🚀 Agressivo", callback_data="sug_agressivo"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🤖 Análise IA personalizada", callback_data="sug_ia"
                    )
                ],
            ]
        ),
    )


async def mostrar_carteira(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra a carteira sugerida para o perfil."""
    query = update.callback_query
    await query.answer()

    user = await get_or_create_user(query.from_user.id)
    perfil_json = json.loads(user.get("perfil_json", "{}") or "{}")
    perfil_nome = perfil_json.get("perfil_risco", "Moderado")
    renda = user.get("renda_mensal", 0)

    carteira = CARTEIRAS.get(perfil_nome, CARTEIRAS["Moderado"])

    # Buscar CDI para referência
    cdi = await get_cdi_atual()
    taxa = cdi_anual(cdi["taxa"])

    linhas = []
    for classe, pct in carteira["alocacao"]:
        barra = "█" * (pct // 5) + "░" * (20 - pct // 5)
        valor_str = f" (R${renda * pct / 100:,.0f}/mês)" if renda else ""
        linhas.append(f"**{pct}%** {classe}{valor_str}\n{barra}")

    msg = (
        f"📊 **Carteira Sugerida — Perfil {perfil_nome}**\n\n"
        f"{carteira['resumo']}\n\n"
        + "\n\n".join(linhas)
        + f"\n\n📈 CDI atual: {taxa:.1f}% ao ano"
    )

    if renda:
        # Sugerir quanto investir (regra 50-30-20)
        investir = renda * 0.2
        msg += (
            f"\n\n💡 **Sugestão:** invista pelo menos "
            f"**R${investir:,.0f}/mês** (20% da sua renda)"
        )

    msg += (
        "\n\n⚠️ _Sugestão educacional. Não é recomendação de investimento. "
        "Consulte um profissional certificado._"
    )

    await query.edit_message_text(msg, parse_mode="Markdown")


async def mostrar_classe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra investimentos de uma classe específica."""
    query = update.callback_query
    await query.answer()

    classe = query.data.replace("sug_", "")
    investimentos = INVESTIMENTOS.get(classe, [])

    if not investimentos:
        await query.edit_message_text("Classe não encontrada.")
        return

    emojis = {
        "conservador": "🟢",
        "moderado": "⚖️",
        "arrojado": "📈",
        "agressivo": "🚀",
    }

    nomes = {
        "conservador": "Conservador",
        "moderado": "Moderado",
        "arrojado": "Arrojado",
        "agressivo": "Agressivo",
    }

    linhas = []
    for inv in investimentos:
        linhas.append(
            f"**{inv['nome']}**\n"
            f"  📁 {inv['tipo']} | {inv['risco']}\n"
            f"  💰 Retorno: {inv['retorno_esperado']}\n"
            f"  ⏰ Prazo: {inv['prazo_minimo']}\n"
            f"  💵 Mínimo: {inv['valor_minimo']}\n"
            f"  📍 Onde: {inv['onde']}\n"
            f"  _{inv['descricao']}_"
        )

    msg = (
        f"{emojis[classe]} **Investimentos {nomes[classe]}s**\n\n"
        + "\n\n━━━━━━━━━━━━━━━━━━━\n\n".join(linhas)
        + "\n\n🤖 Me mande uma mensagem para tirar dúvidas sobre qualquer um!"
        + "\n\n⚠️ _Informações educacionais. Não é recomendação de investimento._"
    )

    await query.edit_message_text(msg, parse_mode="Markdown")


async def analise_ia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pede uma análise personalizada da IA."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text("🤖 Analisando seu perfil... ⏳")

    user = await get_or_create_user(query.from_user.id)
    perfil_json = json.loads(user.get("perfil_json", "{}") or "{}")
    perfil_nome = perfil_json.get("perfil_risco", "não definido")

    contexto = await get_financial_context(query.from_user.id)

    cdi = await get_cdi_atual()
    taxa = cdi_anual(cdi["taxa"])

    pergunta = (
        f"O perfil de risco deste investidor é: {perfil_nome}.\n"
        f"CDI atual: {taxa:.2f}% ao ano.\n\n"
        "Com base no perfil de risco e na situação financeira, dê uma "
        "recomendação PERSONALIZADA de como essa pessoa deveria investir "
        "o dinheiro agora. Inclua:\n"
        "1. Se a pessoa DEVE ou NÃO investir em renda variável agora "
        "(considere se tem reserva de emergência, dívidas, etc)\n"
        "2. Sugestão concreta de alocação com valores\n"
        "3. Primeiro passo prático para esta semana\n"
        "4. Um alerta personalizado baseado na situação dela"
    )

    resposta = await consultar_ia(pergunta, contexto)

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=f"🤖 **Análise Personalizada**\n\n{resposta}",
        parse_mode="Markdown",
    )


def get_sugestoes_handlers() -> list:
    """Retorna os handlers de sugestões."""
    return [
        CommandHandler("sugestoes", sugestoes),
        CallbackQueryHandler(mostrar_carteira, pattern="^sug_carteira$"),
        CallbackQueryHandler(analise_ia, pattern="^sug_ia$"),
        CallbackQueryHandler(
            mostrar_classe, pattern="^sug_(conservador|moderado|arrojado|agressivo)$"
        ),
    ]
