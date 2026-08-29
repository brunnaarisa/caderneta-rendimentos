"""
FinançasIA — Assistente de Educação Financeira no Telegram.

Ponto de entrada do bot. Inicializa o banco de dados,
registra todos os handlers e inicia o polling.
"""

import asyncio
import logging

from telegram.ext import ApplicationBuilder

from config import LOG_LEVEL, TELEGRAM_BOT_TOKEN
from database.db import init_db
from handlers.aprender import get_aprender_handlers
from handlers.aporte import get_aporte_handlers
from handlers.carteira import get_carteira_handlers
from handlers.como_comprar import get_como_comprar_handlers
from handlers.alerta_mercado import get_alerta_mercado_handlers
from handlers.alerta_preco import get_alerta_preco_handlers
from handlers.compartilhar import get_compartilhar_handlers
from handlers.evolucao import get_evolucao_handlers
from handlers.imposto_renda import get_ir_handlers
from handlers.radar import get_radar_handlers
from handlers.resumo_matinal import get_resumo_matinal_handlers
from handlers.watchlist import get_watchlist_handlers
from handlers.consulta import get_consulta_handlers
from handlers.desafio import get_desafio_handlers
from handlers.dividas import get_dividas_handlers
from handlers.ferramentas import get_ferramentas_handlers
from handlers.gamificacao import get_gamificacao_handlers
from handlers.gastos import get_gastos_handlers
from handlers.investimentos import get_investimentos_handlers
from handlers.metas import get_metas_handlers
from handlers.oquefazer import get_oquefazer_handlers
from handlers.perfil_risco import get_perfil_risco_handler
from handlers.premium import get_premium_handlers
from handlers.start import get_start_handler
from handlers.sugestoes import get_sugestoes_handlers
from handlers.termos import get_termos_handlers
from services.alert_scheduler import registrar_jobs

# Configurar logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, LOG_LEVEL, logging.INFO),
)
logger = logging.getLogger(__name__)


def main():
    """Função principal — configura e roda o bot."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error(
            "TELEGRAM_BOT_TOKEN não configurado! "
            "Copie .env.example para .env e preencha."
        )
        return

    logger.info("Inicializando FinançasIA Bot...")

    # Inicializar banco de dados
    asyncio.run(init_db())
    logger.info("Banco de dados inicializado.")

    # Criar aplicação
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Registrar handlers (ordem importa!)
    # 1. Onboarding
    app.add_handler(get_start_handler())

    # 2. Perfil de risco
    app.add_handler(get_perfil_risco_handler())

    # 3. O que eu faria
    for handler in get_oquefazer_handlers():
        app.add_handler(handler)

    # 4. Carteira e análise de mercado
    for handler in get_carteira_handlers():
        app.add_handler(handler)

    # 5. Plano de aporte mensal
    for handler in get_aporte_handlers():
        app.add_handler(handler)

    # 6. Como comprar (guias passo a passo)
    for handler in get_como_comprar_handlers():
        app.add_handler(handler)

    # 7. Investimentos (calculadora)
    for handler in get_investimentos_handlers():
        app.add_handler(handler)

    # 8. Gastos
    for handler in get_gastos_handlers():
        app.add_handler(handler)

    # 9. Dívidas
    for handler in get_dividas_handlers():
        app.add_handler(handler)

    # 10. Metas
    for handler in get_metas_handlers():
        app.add_handler(handler)

    # 11. Sugestões
    for handler in get_sugestoes_handlers():
        app.add_handler(handler)

    # 12. Aprender
    for handler in get_aprender_handlers():
        app.add_handler(handler)

    # 13. Premium
    for handler in get_premium_handlers():
        app.add_handler(handler)

    # 14. Desafio de rendimento
    for handler in get_desafio_handlers():
        app.add_handler(handler)

    # 15. Gamificação, indicação e orçamento
    for handler in get_gamificacao_handlers():
        app.add_handler(handler)

    # 16. Ferramentas (painel, comparador, FIRE, dica)
    for handler in get_ferramentas_handlers():
        app.add_handler(handler)

    # 17. Alertas urgentes de mercado
    for handler in get_alerta_mercado_handlers():
        app.add_handler(handler)

    # 18. Calculadora de Imposto de Renda
    for handler in get_ir_handlers():
        app.add_handler(handler)

    # 19. Alertas de preço-alvo
    for handler in get_alerta_preco_handlers():
        app.add_handler(handler)

    # 20. Radar de oportunidades
    for handler in get_radar_handlers():
        app.add_handler(handler)

    # 21. Resumo matinal
    for handler in get_resumo_matinal_handlers():
        app.add_handler(handler)

    # 22. Watchlist personalizada
    for handler in get_watchlist_handlers():
        app.add_handler(handler)

    # 23. Evolução/histórico da carteira
    for handler in get_evolucao_handlers():
        app.add_handler(handler)

    # 24. Compartilhamento social
    for handler in get_compartilhar_handlers():
        app.add_handler(handler)

    # 25. Termos de Uso e Privacidade (LGPD)
    for handler in get_termos_handlers():
        app.add_handler(handler)

    # 26. Consultas IA + Ajuda (por último — pega qualquer texto)
    for handler in get_consulta_handlers():
        app.add_handler(handler)

    # Registrar jobs de background (alertas automáticos)
    registrar_jobs(app)

    # Iniciar bot
    logger.info("Bot iniciado! Pressione Ctrl+C para parar.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
