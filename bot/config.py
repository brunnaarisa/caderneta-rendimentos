"""Configurações centralizadas do FinançasIA Bot."""

import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Anthropic (Claude)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
AI_MODEL = "claude-sonnet-4-20250514"

# Limites
FREE_DAILY_LIMIT = int(os.getenv("FREE_DAILY_LIMIT", "5"))
PREMIUM_PRICE = float(os.getenv("PREMIUM_PRICE", "14.90"))

# Banco de dados
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/financas_ia.db")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Categorias de gastos
CATEGORIAS_GASTOS = [
    "🍔 Alimentação",
    "🏠 Moradia",
    "🚗 Transporte",
    "👕 Vestuário",
    "💊 Saúde",
    "📚 Educação",
    "🎮 Lazer",
    "📱 Assinaturas",
    "🛒 Compras",
    "💡 Contas (luz, água, etc)",
    "📦 Outros",
]

# Mercado Pago (Pix)
MERCADOPAGO_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "")

# API Banco Central — CDI
BCB_CDI_URL = (
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.4389/dados/ultimos/1?formato=json"
)
