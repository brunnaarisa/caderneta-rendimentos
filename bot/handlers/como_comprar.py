"""
Handler do /comocomprar — guia passo a passo para comprar cada tipo de ativo.

Para quem nunca comprou nada: mostra exatamente onde baixar o app,
que botão apertar, passo por passo. Zero conhecimento prévio necessário.
"""

import logging
import re

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from services.portfolio_service import CRYPTO_MAP

logger = logging.getLogger(__name__)


# ── Guias por tipo de ativo ──────────────────────────────────

GUIA_CRYPTO = (
    "📖 **Como comprar criptomoedas (BTC, ETH, etc.)**\n\n"
    "🟡 **Opção 1: Binance** (taxa mais baixa)\n"
    "1. Baixe o app **Binance** (Google Play / App Store)\n"
    "2. Crie conta com e-mail + CPF\n"
    "3. Faça a verificação (selfie + documento) — leva 10 min\n"
    "4. Toque em **Carteira** → **Depositar** → **BRL** → **Pix**\n"
    "5. Copie a chave Pix e faça a transferência do seu banco\n"
    "6. Quando o dinheiro cair: toque em **Negociar**\n"
    "7. Procure o ativo (BTC, ETH, SOL, etc.)\n"
    "8. Toque em **Comprar** → digite o valor em R$\n"
    "9. Confirme. **Pronto!** ✅\n"
    "💡 _Taxa ~0,1%. Melhor para comprar frequentemente._\n\n"
    "🔵 **Opção 2: Mercado Bitcoin** (mais simples)\n"
    "1. Baixe o app **Mercado Bitcoin (MB)**\n"
    "2. Crie conta com CPF\n"
    "3. Deposite via Pix (cai na hora)\n"
    "4. Procure o ativo na busca\n"
    "5. Toque em **Comprar** → valor → confirmar\n"
    "6. **Pronto!** ✅\n"
    "💡 _App brasileiro, bom para iniciantes._\n\n"
    "⚠️ **Dica de segurança:** ative a autenticação em 2 fatores (2FA) "
    "assim que criar a conta. Nunca compartilhe sua senha.\n"
)

GUIA_ACOES = (
    "📖 **Como comprar ações, FIIs e ETFs na Bolsa (B3)**\n\n"
    "💜 **Opção 1: Nubank** (mais fácil, sem taxa)\n"
    "1. Abra o app do **Nubank** (já tem conta? Pule para 3)\n"
    "2. Se não tem: crie conta em nubank.com.br (grátis)\n"
    "3. Na tela inicial, toque em **Investir**\n"
    "4. Toque em **Ações** ou **Fundos Imobiliários** ou **ETFs**\n"
    "5. Procure o código (ex: WEGE3, HGLG11, IVVB11)\n"
    "6. Toque em **Comprar**\n"
    "7. Escolha quantidade de cotas ou valor em R$\n"
    "8. Confirme. **Pronto!** ✅\n"
    "💡 _Zero corretagem. Mais fácil pra quem já é cliente._\n\n"
    "🟠 **Opção 2: Inter Invest** (também sem taxa)\n"
    "1. Abra o app do **Inter**\n"
    "2. Toque em **Investir** → **Renda Variável**\n"
    "3. Procure o ticker (ex: PETR4, VALE3)\n"
    "4. Toque em **Comprar** → defina quantidade\n"
    "5. Confirme. **Pronto!** ✅\n"
    "💡 _Sem corretagem. Cashback em algumas compras._\n\n"
    "📌 **O que é um ticker?** É o código da empresa na bolsa.\n"
    "Ex: WEGE3 = WEG, VALE3 = Vale, HGLG11 = FII de galpões\n"
)

GUIA_RENDA_FIXA = (
    "📖 **Como comprar Renda Fixa (CDB, Tesouro, LCI/LCA)**\n\n"
    "💜 **CDB e LCI/LCA no Nubank:**\n"
    "1. Abra o app → **Investir** → **Renda Fixa**\n"
    "2. Veja as opções: CDB, LCI, LCA\n"
    "3. Confira: rendimento (ex: 110% CDI), prazo, valor mínimo\n"
    "4. Digite o valor → **Investir**\n"
    "5. **Pronto!** Rende todo dia automaticamente ✅\n"
    "💡 _CDB com liquidez diária = reserva de emergência perfeita._\n\n"
    "🏛️ **Tesouro Direto:**\n"
    "1. Acesse pelo app do seu banco ou tesourodireto.com.br\n"
    "2. Tipos de título:\n"
    "   • **Tesouro Selic** — rende CDI, pode tirar quando quiser\n"
    "   • **Tesouro IPCA+** — protege da inflação (longo prazo)\n"
    "   • **Tesouro Prefixado** — taxa fixa definida na compra\n"
    "3. Escolha o título → digite o valor (mínimo ~R$30)\n"
    "4. Confirme. **Pronto!** ✅\n"
    "💡 _O investimento mais seguro do Brasil. Garantido pelo governo._\n\n"
    "📌 **Qual escolher?**\n"
    "• Reserva de emergência → CDB liquidez diária ou Tesouro Selic\n"
    "• Médio prazo (1-3 anos) → LCI/LCA (isento de IR!) ou CDB 110%+ CDI\n"
    "• Longo prazo (5+ anos) → Tesouro IPCA+\n"
)

GUIA_ABRIR_CONTA = (
    "📖 **Ainda não tem conta em corretora? Comece aqui:**\n\n"
    "As 3 opções mais fáceis (todas gratuitas):\n\n"
    "1️⃣ **Nubank** — nubank.com.br\n"
    "   Ações, FIIs, ETFs, CDB, Tesouro. Tudo sem taxa.\n"
    "   _Melhor pra quem quer simplicidade._\n\n"
    "2️⃣ **Inter** — inter.co\n"
    "   Mesmas opções + cashback. Também sem taxa.\n"
    "   _Boa alternativa com mais funcionalidades._\n\n"
    "3️⃣ **Binance** — binance.com\n"
    "   Só para criptomoedas. Taxa de 0,1%.\n"
    "   _Obrigatória se quiser comprar crypto direto._\n\n"
    "📌 **Minha sugestão:** abra conta no **Nubank** (pra ações, "
    "FIIs e renda fixa) + **Binance** (pra crypto). "
    "Com esses dois você investe em tudo!\n\n"
    "⏱️ _Abrir conta leva 5-10 minutos. Precisa de CPF e selfie._"
)


def _identificar_tipo(ativo: str) -> str:
    """Identifica o tipo do ativo para mostrar o guia certo."""
    ativo_lower = ativo.lower().strip()

    # Cripto
    if ativo_lower in CRYPTO_MAP or ativo_lower in (
        "cripto",
        "crypto",
        "criptomoeda",
        "criptomoedas",
    ):
        return "crypto"

    # Renda fixa
    rf_keywords = [
        "cdb",
        "tesouro",
        "lci",
        "lca",
        "renda fixa",
        "poupança",
        "poupanca",
        "selic",
        "ipca",
    ]
    if ativo_lower in rf_keywords or any(
        kw in ativo_lower for kw in rf_keywords
    ):
        return "renda_fixa"

    # Ação/FII/ETF (ticker: 4+ letras + dígito)
    if re.match(r"^[A-Za-z]{4}\d{1,2}$", ativo_lower):
        return "acao"

    # Keywords genéricos
    if ativo_lower in (
        "ação",
        "acao",
        "ações",
        "acoes",
        "fii",
        "fiis",
        "etf",
        "etfs",
        "bolsa",
    ):
        return "acao"

    if ativo_lower in ("conta", "corretora", "começar", "comecar", "inicio"):
        return "conta"

    return "todos"


async def como_comprar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra guia passo a passo de como comprar."""
    args = context.args
    ativo = " ".join(args).strip() if args else ""

    if not ativo:
        await update.message.reply_text(
            "📖 **Como Comprar — Guia Passo a Passo**\n\n"
            "Escolha o que quer aprender:\n\n"
            "/comocomprar **btc** — Criptomoedas\n"
            "/comocomprar **WEGE3** — Ações\n"
            "/comocomprar **HGLG11** — Fundos Imobiliários\n"
            "/comocomprar **IVVB11** — ETFs\n"
            "/comocomprar **tesouro** — Tesouro Direto\n"
            "/comocomprar **cdb** — CDB e Renda Fixa\n"
            "/comocomprar **conta** — Abrir conta em corretora\n\n"
            "Ou digite o nome de qualquer ativo! 😊",
            parse_mode="Markdown",
        )
        return

    tipo = _identificar_tipo(ativo)

    if tipo == "crypto":
        texto = GUIA_CRYPTO
        nome = ativo.lower().strip()
        texto += (
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📊 /analisar {nome} — Ver se é bom momento\n"
            f"📝 /comprei — Registrar após comprar"
        )
    elif tipo == "acao":
        texto = GUIA_ACOES
        texto += (
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📊 /analisar {ativo.upper()} — Ver análise do ativo\n"
            f"📝 /comprei — Registrar após comprar"
        )
    elif tipo == "renda_fixa":
        texto = GUIA_RENDA_FIXA
    elif tipo == "conta":
        texto = GUIA_ABRIR_CONTA
    else:
        # Mostrar tudo resumido
        texto = (
            GUIA_ABRIR_CONTA
            + "\n━━━━━━━━━━━━━━━━━━━\n\n"
            + GUIA_CRYPTO
            + "\n━━━━━━━━━━━━━━━━━━━\n\n"
            + GUIA_ACOES
            + "\n━━━━━━━━━━━━━━━━━━━\n\n"
            + GUIA_RENDA_FIXA
        )

    # Dividir se muito longo (limite Telegram: 4096 chars)
    if len(texto) > 4000:
        partes = texto.split("\n━━━━━━━━━━━━━━━━━━━\n")
        for parte in partes:
            parte = parte.strip()
            if parte:
                await update.message.reply_text(
                    parte, parse_mode="Markdown"
                )
    else:
        await update.message.reply_text(texto, parse_mode="Markdown")


def get_como_comprar_handlers() -> list:
    """Retorna os handlers de como comprar."""
    return [CommandHandler("comocomprar", como_comprar)]
