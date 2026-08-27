"""
FinançasIA — Consultor Financeiro Pessoal no Telegram.

Ponto de entrada do bot. Inicializa o banco de dados,
registra todos os handlers e inicia o polling.
"""

import asyncio
import logging

from telegram.ext import ApplicationBuilder

from config import LOG_LEVEL, TELEGRAM_BOT_TOKEN
from database.db import init_db
from handlers.aprender import get_aprender_handlers
from handlers.carteira import get_carteira_handlers
from handlers.consulta import get_consulta_handlers
from handlers.dividas import get_dividas_handlers
from handlers.gastos import get_gastos_handlers
from handlers.investimentos import get_investimentos_handlers
from handlers.metas import get_metas_handlers
from handlers.oquefazer import get_oquefazer_handlers
from handlers.perfil_risco import get_perfil_risco_handler
from handlers.premium import get_premium_handlers
from handlers.start import get_start_handler
from handlers.sugestoes import get_sugestoes_handlers
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
    asyncio.get_event_loop().run_until_complete(init_db())
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

    # 5. Investimentos (calculadora)
    for handler in get_investimentos_handlers():
        app.add_handler(handler)

    # 6. Gastos
    for handler in get_gastos_handlers():
        app.add_handler(handler)

    # 7. Dívidas
    for handler in get_dividas_handlers():
        app.add_handler(handler)

    # 8. Metas
    for handler in get_metas_handlers():
        app.add_handler(handler)

    # 9. Sugestões
    for handler in get_sugestoes_handlers():
        app.add_handler(handler)

    # 10. Aprender
    for handler in get_aprender_handlers():
        app.add_handler(handler)

    # 11. Premium
    for handler in get_premium_handlers():
        app.add_handler(handler)

    # 12. Consultas IA + Ajuda (por último — pega qualquer texto)
    for handler in get_consulta_handlers():
        app.add_handler(handler)

    # Registrar jobs de background (alertas automáticos)
    registrar_jobs(app)

    # Iniciar bot
    logger.info("Bot iniciado! Pressione Ctrl+C para parar.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
