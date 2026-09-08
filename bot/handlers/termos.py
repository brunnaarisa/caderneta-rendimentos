"""
Handler do /termos — Termos de Uso e Política de Privacidade.

Exibição dos termos de uso do bot e política de privacidade
em conformidade com a LGPD (Lei Geral de Proteção de Dados).
"""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)


TERMOS_DE_USO = """📜 **Termos de Uso — FinançasIA**

**1. Natureza do Serviço**
O FinançasIA é uma ferramenta de **educação financeira**. O bot NÃO é:
• Consultor de investimentos (CVM)
• Analista de valores mobiliários (CNPI)
• Instituição financeira
• Assessor de investimentos

**2. Conteúdo Educacional**
Todo conteúdo fornecido (análises, estudos de alocação, indicadores \
técnicos, simulações) tem caráter **exclusivamente educacional** e \
informativo. Não constitui recomendação de compra, venda ou \
manutenção de qualquer ativo financeiro.

**3. Responsabilidade**
• A **decisão de investir é exclusivamente sua**.
• Rentabilidade passada não garante resultados futuros.
• Indicadores técnicos são ferramentas de estudo, não previsões.
• Para orientação personalizada, consulte um profissional \
certificado pela CVM.

**4. Isenção de Responsabilidade**
O FinançasIA não se responsabiliza por:
• Perdas financeiras decorrentes de decisões de investimento
• Indisponibilidade temporária do serviço
• Precisão dos dados de mercado (obtidos de fontes públicas)
• Interrupções nas APIs de terceiros (CoinGecko, BRAPI)

**5. Plano Premium**
• Assinatura mensal no valor informado no bot
• Pagamento via Pix processado pelo Mercado Pago
• Cancelamento a qualquer momento via /premium
• Sem reembolso do período já pago

**6. Idade Mínima**
O uso do bot é permitido apenas para maiores de 18 anos.

_Última atualização: Agosto 2026_
"""

POLITICA_PRIVACIDADE = """🔒 **Política de Privacidade — FinançasIA**

Em conformidade com a **Lei Geral de Proteção de Dados (LGPD — \
Lei nº 13.709/2018)**.

**1. Dados Coletados**
Coletamos apenas os dados necessários para o funcionamento:
• **Telegram ID** — identificação do usuário (fornecido pelo Telegram)
• **Primeiro nome** — personalização das mensagens
• **Perfil financeiro** — objetivo, renda aproximada e nível de \
conhecimento (informados voluntariamente no onboarding)
• **Registros de carteira** — compras registradas pelo usuário
• **Gastos e metas** — informados voluntariamente pelo usuário

**2. Finalidade do Tratamento**
Os dados são usados exclusivamente para:
• Personalizar o conteúdo educacional
• Acompanhar posições de carteira registradas
• Enviar alertas configurados pelo usuário
• Processar pagamentos (plano Premium)

**3. Armazenamento**
• Dados armazenados em banco SQLite no servidor do bot
• Não compartilhamos dados com terceiros (exceto Mercado Pago \
para processamento de pagamentos)
• Dados de pagamento são processados pelo Mercado Pago sob a \
política de privacidade deles

**4. Base Legal (Art. 7º LGPD)**
• **Consentimento** — ao usar o bot, você consente com o \
tratamento dos dados informados
• **Execução de contrato** — processamento de pagamentos Premium

**5. Direitos do Titular (Art. 18 LGPD)**
Você tem direito a:
• ✅ **Acesso** — ver seus dados (/painel)
• ✅ **Correção** — atualizar seu perfil (/start)
• ✅ **Eliminação** — solicitar exclusão dos seus dados
• ✅ **Portabilidade** — exportar seus dados
• ✅ **Revogação** — cancelar alertas e notificações a qualquer momento

Para exercer seus direitos, envie uma mensagem ao bot ou entre \
em contato com o administrador.

**6. Retenção de Dados**
• Dados são mantidos enquanto a conta estiver ativa
• Após 12 meses de inatividade, dados podem ser excluídos
• Dados de pagamento seguem as regras do Mercado Pago

**7. Segurança**
• Comunicação criptografada via Telegram (MTProto)
• Banco de dados com acesso restrito ao servidor
• Não armazenamos senhas ou dados bancários

**8. Encarregado de Dados (DPO)**
Para dúvidas sobre privacidade, entre em contato com o \
administrador do bot.

_Última atualização: Agosto 2026_
"""


async def termos_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra menu de termos de uso e privacidade."""
    await update.message.reply_text(
        "📜 **Termos e Privacidade**\n\n"
        "Escolha o que deseja consultar:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "📜 Termos de Uso",
                        callback_data="termos_uso",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔒 Política de Privacidade",
                        callback_data="termos_privacidade",
                    )
                ],
            ]
        ),
    )


async def mostrar_termos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe os termos de uso."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(TERMOS_DE_USO, parse_mode="Markdown")


async def mostrar_privacidade(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Exibe a política de privacidade."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        POLITICA_PRIVACIDADE, parse_mode="Markdown"
    )


def get_termos_handlers() -> list:
    """Retorna os handlers dos termos."""
    return [
        CommandHandler("termos", termos_cmd),
        CommandHandler("privacidade", termos_cmd),
        CommandHandler("lgpd", termos_cmd),
        CallbackQueryHandler(mostrar_termos, pattern=r"^termos_uso$"),
        CallbackQueryHandler(
            mostrar_privacidade, pattern=r"^termos_privacidade$"
        ),
    ]
