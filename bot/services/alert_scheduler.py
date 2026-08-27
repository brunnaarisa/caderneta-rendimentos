"""
Scheduler de alertas — roda em background e envia notificações
proativas para os usuários sobre suas posições.

Verifica a cada 1 hora se algum usuário precisa receber alerta.
"""

import logging

from telegram.ext import ContextTypes

from services.market_analysis import verificar_carteira
from services.portfolio_service import (
    get_carteira_ativa,
    get_usuarios_para_alertar,
    update_ultimo_alerta,
    CRYPTO_NOMES,
)

logger = logging.getLogger(__name__)


async def job_verificar_alertas(context: ContextTypes.DEFAULT_TYPE):
    """
    Job que roda periodicamente para verificar e enviar alertas.
    Registrado no main.py via job_queue.
    """
    logger.info("Verificando alertas de carteira...")

    try:
        usuarios = await get_usuarios_para_alertar()
        logger.info("Usuários para alertar: %d", len(usuarios))

        for user in usuarios:
            telegram_id = user["telegram_id"]

            try:
                posicoes = await get_carteira_ativa(telegram_id)
                if not posicoes:
                    continue

                # Montar lista de compras para análise
                compras = [
                    {
                        "ativo": p["ativo"],
                        "tipo": p["tipo"],
                        "preco_compra": p["preco_compra"],
                        "valor_investido": p["valor_investido"],
                        "data_compra": p["data_compra"],
                    }
                    for p in posicoes
                ]

                # Verificar cada ativo
                alertas = await verificar_carteira(compras)

                # Filtrar só os que precisam de ação
                alertas_importantes = [
                    a for a in alertas if a.get("mensagem") is not None
                ]

                if alertas_importantes:
                    # Montar mensagem
                    msg = "🔔 **Alerta da sua Carteira**\n\n"

                    for alerta in alertas_importantes:
                        nome = CRYPTO_NOMES.get(
                            alerta["ativo"].lower(), alerta["ativo"]
                        )
                        sinal = "+" if alerta["variacao_pct"] >= 0 else ""

                        msg += (
                            f"{alerta['mensagem']}\n"
                            f"  💰 Investiu: R${alerta['valor_investido']:,.2f}\n"
                            f"  📊 Valor atual: R${alerta['valor_atual_estimado']:,.2f}\n"
                            f"  📈 Resultado: {sinal}{alerta['variacao_pct']:.1f}%\n\n"
                        )

                    msg += (
                        "━━━━━━━━━━━━━━━━━━━\n"
                        "📋 /carteira — Ver posições completas\n"
                        "📊 /analisar [ativo] — Análise detalhada\n"
                        "🔕 /alertas — Desativar alertas"
                    )

                    await context.bot.send_message(
                        chat_id=telegram_id,
                        text=msg,
                        parse_mode="Markdown",
                    )
                    logger.info("Alerta enviado para %s", telegram_id)

                # Atualizar timestamp do último alerta
                await update_ultimo_alerta(telegram_id)

            except Exception as e:
                logger.error(
                    "Erro ao processar alertas do usuário %s: %s", telegram_id, e
                )

    except Exception as e:
        logger.error("Erro no job de alertas: %s", e)


def registrar_jobs(app):
    """
    Registra os jobs periódicos no bot.
    Chamado pelo main.py após criar a Application.
    """
    job_queue = app.job_queue

    # Verificar alertas a cada 1 hora
    job_queue.run_repeating(
        job_verificar_alertas,
        interval=3600,  # 1 hora
        first=60,  # começa 1 minuto após o bot iniciar
        name="verificar_alertas",
    )

    logger.info("Jobs de alerta registrados (intervalo: 1h)")
