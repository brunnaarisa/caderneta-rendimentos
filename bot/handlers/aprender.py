"""Handler do /aprender — jornada educacional do zero absoluto."""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)

# Aulas organizadas em módulos progressivos
AULAS = {
    "mod1": {
        "titulo": "📖 Módulo 1 — O Básico (do zero mesmo)",
        "aulas": [
            {
                "id": "m1a1",
                "titulo": "O que é investir?",
                "conteudo": (
                    "📖 **Aula 1 — O que é investir?**\n\n"
                    "Investir é colocar seu dinheiro para **trabalhar para você**.\n\n"
                    "Quando você deixa R$100 na poupança, o banco pega esse "
                    "dinheiro, empresta pra outra pessoa, e te paga uma parte "
                    "dos juros. Você não fez nada — seu dinheiro fez.\n\n"
                    "**Exemplo real:**\n"
                    "• R$100 na poupança → R$107 depois de 1 ano\n"
                    "• R$100 no Nubank (CDB 100% CDI) → R$113 depois de 1 ano\n"
                    "• R$100 debaixo do colchão → R$100 (mas compra menos, "
                    "porque os preços subiram)\n\n"
                    "💡 **Sacou?** Quem não investe **perde dinheiro** todo dia, "
                    "porque a inflação come o valor do que você tem parado.\n\n"
                    "Próxima aula: o que é CDI, Selic e por que todo mundo fala disso."
                ),
            },
            {
                "id": "m1a2",
                "titulo": "CDI e Selic — explicados como se você tivesse 10 anos",
                "conteudo": (
                    "📖 **Aula 2 — CDI e Selic**\n\n"
                    "**Selic** é a taxa de juros que o governo define. "
                    "Pense nela como o \"preço do dinheiro\" no Brasil.\n\n"
                    "**CDI** anda colado na Selic (quase igual). É a taxa que "
                    "os bancos usam entre si.\n\n"
                    "Quando alguém fala:\n"
                    "• _\"Rende 100% do CDI\"_ → você ganha exatamente a "
                    "taxa CDI\n"
                    "• _\"Rende 110% do CDI\"_ → você ganha 10% A MAIS que "
                    "o CDI (melhor!)\n"
                    "• _\"Rende 80% do CDI\"_ → você ganha 80% da taxa "
                    "(pior, tipo poupança)\n\n"
                    "**Hoje a Selic está alta (~13.75%).** Isso significa que "
                    "investimentos seguros estão rendendo bem. Aproveite!\n\n"
                    "💡 **Regra de ouro:** nunca aceite menos que 100% do CDI "
                    "num investimento seguro. Se o banco oferece menos, troque.\n\n"
                    "Próxima aula: o que é IR e por que ele come parte do seu rendimento."
                ),
            },
            {
                "id": "m1a3",
                "titulo": "Imposto de Renda nos investimentos",
                "conteudo": (
                    "📖 **Aula 3 — Imposto de Renda**\n\n"
                    "O governo cobra imposto sobre o que você GANHA (não sobre "
                    "o que investiu). E a boa notícia: quanto mais tempo "
                    "deixar, menos paga!\n\n"
                    "**Tabela regressiva:**\n"
                    "• Até 6 meses: 22,5%\n"
                    "• 6 a 12 meses: 20%\n"
                    "• 12 a 24 meses: 17,5%\n"
                    "• Acima de 24 meses: 15% ✨\n\n"
                    "**Exemplo com R$1.000:**\n"
                    "Rendeu R$130 no ano (CDI).\n"
                    "Se tirar em 6 meses: paga R$14,63 de IR.\n"
                    "Se tirar em 2 anos: paga R$9,75 de IR.\n\n"
                    "**Investimentos SEM IR** (isentos):\n"
                    "• LCI / LCA\n"
                    "• Dividendos de ações\n"
                    "• Dividendos de FIIs\n"
                    "• Poupança\n\n"
                    "💡 O IR é descontado automaticamente — você não precisa "
                    "fazer nada. O valor que cai na sua conta já é o líquido."
                ),
            },
            {
                "id": "m1a4",
                "titulo": "Reserva de emergência — faça isso ANTES de tudo",
                "conteudo": (
                    "📖 **Aula 4 — Reserva de Emergência**\n\n"
                    "🚨 **Isso é mais importante que qualquer investimento.**\n\n"
                    "Reserva de emergência = 3 a 6 meses dos seus gastos "
                    "guardados num lugar SEGURO e com LIQUIDEZ (que você "
                    "consegue tirar na hora).\n\n"
                    "**Por quê?** Porque sem isso, qualquer imprevisto "
                    "(perder emprego, emergência médica, carro quebrar) te "
                    "obriga a vender investimento na hora errada, pegar "
                    "empréstimo caro, ou usar cartão de crédito.\n\n"
                    "**Quanto guardar:**\n"
                    "• Gasta R$2.000/mês → Reserve R$6.000-12.000\n"
                    "• Gasta R$3.000/mês → Reserve R$9.000-18.000\n\n"
                    "**Onde deixar a reserva:**\n"
                    "• CDB com liquidez diária (Nubank, Inter, PagBank)\n"
                    "• Tesouro Selic\n"
                    "• ❌ NUNCA em ações, cripto, ou investimento travado\n\n"
                    "💡 **Só invista em coisas mais arriscadas DEPOIS de ter "
                    "a reserva pronta.** Isso não é opcional."
                ),
            },
        ],
    },
    "mod2": {
        "titulo": "📈 Módulo 2 — Renda Variável (o jogo dos maiores)",
        "aulas": [
            {
                "id": "m2a1",
                "titulo": "Ações — como funciona na prática",
                "conteudo": (
                    "📖 **Aula 5 — O que são ações**\n\n"
                    "Quando você compra uma ação, você vira **sócio** de uma "
                    "empresa. Se ela lucra, você lucra. Se ela vai mal, você "
                    "perde.\n\n"
                    "**Como comprar:**\n"
                    "1. Abra conta numa corretora (Nubank, Inter, XP, Clear...)\n"
                    "2. Procure o código da ação (ex: PETR4 = Petrobras)\n"
                    "3. Clique em comprar, digite a quantidade, confirme\n"
                    "4. Pronto — você é sócio da empresa!\n\n"
                    "**Quanto custa?** Hoje muitas ações custam menos de "
                    "R$30. Dá pra começar com pouco.\n\n"
                    "**Como você ganha dinheiro:**\n"
                    "• 📈 Valorização: comprou a R$20, vendeu a R$30 → lucro\n"
                    "• 💰 Dividendos: a empresa te paga parte do lucro "
                    "(cai na sua conta!)\n\n"
                    "**Como você perde dinheiro:**\n"
                    "• 📉 Desvalorização: comprou a R$30, caiu pra R$20\n"
                    "• ⚠️ Mas você só perde DE VERDADE se vender na baixa!\n\n"
                    "💡 **Dica:** não coloque em ações dinheiro que vai "
                    "precisar em menos de 2-3 anos."
                ),
            },
            {
                "id": "m2a2",
                "titulo": "FIIs — receber aluguel sem ter imóvel",
                "conteudo": (
                    "📖 **Aula 6 — Fundos Imobiliários (FIIs)**\n\n"
                    "Imagina ser dono de um pedaço de shopping, galpão "
                    "logístico ou prédio de escritórios — e receber aluguel "
                    "todo mês. É isso que FIIs fazem.\n\n"
                    "**Como funciona:**\n"
                    "• Você compra cotas na bolsa (B3)\n"
                    "• O fundo aluga os imóveis\n"
                    "• Todo mês cai dividendo na sua conta (isento de IR!)\n\n"
                    "**Exemplo real:**\n"
                    "100 cotas de MXRF11 a ~R$10 cada = R$1.000 investidos\n"
                    "Dividendo: ~R$0,10/cota/mês = R$10/mês na sua conta\n"
                    "→ ~1% ao mês, isento de IR! 🔥\n\n"
                    "**Riscos:**\n"
                    "• O preço da cota oscila (pode cair 10-20%)\n"
                    "• Vacância (imóvel desocupado = menos dividendo)\n"
                    "• Não tem FGC (não tem garantia do governo)\n\n"
                    "**FIIs famosos para iniciantes:**\n"
                    "MXRF11, HGLG11, KNRI11, XPML11, VISC11\n\n"
                    "💡 FIIs são ótimos para quem quer renda mensal sem "
                    "precisar vender nada."
                ),
            },
            {
                "id": "m2a3",
                "titulo": "Cripto — Bitcoin, Ethereum e o resto",
                "conteudo": (
                    "📖 **Aula 7 — Criptomoedas**\n\n"
                    "⚠️ **Começando pelo aviso:** cripto é o investimento "
                    "mais volátil que existe. Pode subir 100% e cair 70%.\n\n"
                    "**O que é Bitcoin (BTC)?**\n"
                    "Dinheiro digital descentralizado — nenhum governo "
                    "controla. Existe um limite de 21 milhões de unidades "
                    "(é escasso, tipo ouro digital).\n\n"
                    "**O que é Ethereum (ETH)?**\n"
                    "Uma plataforma que permite criar contratos e apps "
                    "descentralizados. O ETH é a \"moeda\" dessa plataforma.\n\n"
                    "**Histórico real do Bitcoin:**\n"
                    "• 2020: R$30.000 → 2021: R$350.000 (+1.000%!) 🚀\n"
                    "• 2021: R$350.000 → 2022: R$85.000 (-75%!) 📉\n"
                    "• 2022: R$85.000 → 2024: R$350.000 (+300%) 🚀\n\n"
                    "**Regras de ouro para cripto:**\n"
                    "1. Nunca invista mais do que pode PERDER TUDO\n"
                    "2. Máximo 5-10% do que você investe no total\n"
                    "3. Compre aos poucos (um pouco por mês), não tudo de uma vez\n"
                    "4. Só BTC e ETH para iniciantes — fuja de moedas desconhecidas\n"
                    "5. Horizonte mínimo: 4 anos (um ciclo completo)\n\n"
                    "**Onde comprar:** Mercado Bitcoin, Binance, Coinbase, "
                    "ou HASH11 na B3 (ETF de cripto)."
                ),
            },
            {
                "id": "m2a4",
                "titulo": "ETFs — o jeito mais fácil de diversificar",
                "conteudo": (
                    "📖 **Aula 8 — ETFs (Fundos de Índice)**\n\n"
                    "ETF é como comprar um \"combo\". Em vez de escolher "
                    "ação por ação, você compra todas de uma vez.\n\n"
                    "**ETFs essenciais no Brasil:**\n\n"
                    "🇧🇷 **BOVA11** — Replica o Ibovespa\n"
                    "Você compra 1 cota (~R$120) e tem um pedaço das ~80 "
                    "maiores empresas do Brasil.\n\n"
                    "🇺🇸 **IVVB11** — Replica o S&P 500\n"
                    "Você compra 1 cota (~R$250) e tem um pedaço das 500 "
                    "maiores empresas dos EUA (Apple, Google, Amazon...).\n\n"
                    "₿ **HASH11** — Cripto\n"
                    "Investe em Bitcoin, Ethereum e outras cripto pela bolsa "
                    "brasileira. Sem precisar de exchange.\n\n"
                    "**Por que ETFs são ideais para iniciantes:**\n"
                    "• Diversificação automática (não aposta tudo em 1 empresa)\n"
                    "• Barato (a partir de ~R$10)\n"
                    "• Simples (compra e esquece)\n"
                    "• Sem precisar analisar empresa\n\n"
                    "💡 Warren Buffett (bilionário) recomenda que a maioria "
                    "das pessoas invista em ETF de índice ao invés de tentar "
                    "escolher ações."
                ),
            },
        ],
    },
}


async def aprender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o menu de módulos educacionais."""
    botoes = []
    for mod_id, mod in AULAS.items():
        botoes.append(
            [InlineKeyboardButton(mod["titulo"], callback_data=f"mod_{mod_id}")]
        )

    await update.message.reply_text(
        "🎓 **Jornada do Zero — Aprenda a Investir**\n\n"
        "Não sabe nada sobre investimentos? Perfeito!\n"
        "Eu te ensino do zero, passo a passo.\n\n"
        "Escolha um módulo para começar:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(botoes),
    )


async def mostrar_modulo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra as aulas de um módulo."""
    query = update.callback_query
    await query.answer()

    mod_id = query.data.replace("mod_", "")
    mod = AULAS.get(mod_id)
    if not mod:
        await query.edit_message_text("Módulo não encontrado.")
        return

    botoes = [
        [InlineKeyboardButton(f"📝 {a['titulo']}", callback_data=f"aula_{a['id']}")]
        for a in mod["aulas"]
    ]
    botoes.append(
        [InlineKeyboardButton("⬅️ Voltar", callback_data="voltar_modulos")]
    )

    await query.edit_message_text(
        f"{mod['titulo']}\n\nEscolha uma aula:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(botoes),
    )


async def mostrar_aula(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o conteúdo de uma aula."""
    query = update.callback_query
    await query.answer()

    aula_id = query.data.replace("aula_", "")

    # Encontrar a aula em todos os módulos
    aula = None
    for mod in AULAS.values():
        for a in mod["aulas"]:
            if a["id"] == aula_id:
                aula = a
                break

    if not aula:
        await query.edit_message_text("Aula não encontrada.")
        return

    await query.edit_message_text(
        aula["conteudo"]
        + "\n\n━━━━━━━━━━━━━━━━━━━\n"
        "Use /aprender para ver outras aulas\n"
        "Ou me pergunte qualquer dúvida! 💬",
        parse_mode="Markdown",
    )


async def voltar_modulos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Volta ao menu de módulos."""
    query = update.callback_query
    await query.answer()

    botoes = [
        [InlineKeyboardButton(mod["titulo"], callback_data=f"mod_{mod_id}")]
        for mod_id, mod in AULAS.items()
    ]

    await query.edit_message_text(
        "🎓 **Jornada do Zero**\n\nEscolha um módulo:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(botoes),
    )


def get_aprender_handlers() -> list:
    """Retorna os handlers educacionais."""
    return [
        CommandHandler("aprender", aprender),
        CallbackQueryHandler(mostrar_modulo, pattern=r"^mod_mod\d+$"),
        CallbackQueryHandler(mostrar_aula, pattern=r"^aula_m\d+a\d+$"),
        CallbackQueryHandler(voltar_modulos, pattern="^voltar_modulos$"),
    ]
