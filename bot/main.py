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
from handlers.consulta import get_consulta_handlers
from handlers.dividas import get_dividas_handlers
from handlers.gastos import get_gastos_handlers
from handlers.investimentos import get_investimentos_handlers
from handlers.metas import get_metas_handlers
from handlers.premium import get_premium_handlers
from handlers.start import get_start_handler

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
    # 1. Onboarding (ConversationHandler do /start)
    app.add_handler(get_start_handler())

    # 2. Investimentos (ConversationHandler)
    for handler in get_investimentos_handlers():
        app.add_handler(handler)

    # 3. Gastos (ConversationHandler)
    for handler in get_gastos_handlers():
        app.add_handler(handler)

    # 4. Dívidas (ConversationHandler)
    for handler in get_dividas_handlers():
        app.add_handler(handler)

    # 5. Metas (ConversationHandler)
    for handler in get_metas_handlers():
        app.add_handler(handler)

    # 6. Premium
    for handler in get_premium_handlers():
        app.add_handler(handler)

    # 7. Consultas IA + Ajuda (por último, pois pega qualquer texto)
    for handler in get_consulta_handlers():
        app.add_handler(handler)

    # Iniciar bot
    logger.info("Bot iniciado! Pressione Ctrl+C para parar.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
