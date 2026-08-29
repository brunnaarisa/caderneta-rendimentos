"""Serviço de gestão da carteira de investimentos do usuário."""

from database.db import get_db


# Mapeamento de nomes amigáveis para IDs de API
CRYPTO_MAP = {
    "btc": "bitcoin",
    "bitcoin": "bitcoin",
    "eth": "ethereum",
    "ethereum": "ethereum",
    "sol": "solana",
    "solana": "solana",
    "bnb": "binancecoin",
    "ada": "cardano",
    "xrp": "ripple",
    "dot": "polkadot",
    "doge": "dogecoin",
}

CRYPTO_NOMES = {
    "bitcoin": "Bitcoin (BTC)",
    "ethereum": "Ethereum (ETH)",
    "solana": "Solana (SOL)",
    "binancecoin": "BNB",
    "cardano": "Cardano (ADA)",
    "ripple": "XRP",
    "polkadot": "Polkadot (DOT)",
    "dogecoin": "Dogecoin (DOGE)",
}


def normalizar_ativo(nome: str) -> tuple[str, str]:
    """
    Normaliza o nome do ativo e retorna (id_normalizado, tipo).
    Ex: "btc" -> ("bitcoin", "crypto"), "PETR4" -> ("PETR4", "acao")
    """
    nome_lower = nome.lower().strip()
    if nome_lower in CRYPTO_MAP:
        return CRYPTO_MAP[nome_lower], "crypto"
    # Se termina com número (3, 4, 11), é ação/FII da B3
    if nome_lower[-1].isdigit() and len(nome_lower) >= 4:
        return nome.upper().strip(), "acao"
    # Tentar como crypto por padrão
    return nome_lower, "crypto"


async def registrar_compra(
    telegram_id: int,
    ativo: str,
    tipo: str,
    preco_compra: float,
    valor_investido: float,
    quantidade: float = 0,
) -> int:
    """Registra uma compra na carteira."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO carteira "
            "(telegram_id, ativo, tipo, preco_compra, quantidade, valor_investido) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (telegram_id, ativo, tipo, preco_compra, quantidade, valor_investido),
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def registrar_venda(compra_id: int, preco_venda: float) -> None:
    """Marca uma compra como vendida."""
    db = await get_db()
    try:
        await db.execute(
            "UPDATE carteira SET vendido = 1, preco_venda = ?, "
            "data_venda = date('now') WHERE id = ?",
            (preco_venda, compra_id),
        )
        await db.commit()
    finally:
        await db.close()


async def get_carteira_ativa(telegram_id: int) -> list[dict]:
    """Retorna as posições ativas (não vendidas) do usuário."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM carteira WHERE telegram_id = ? AND vendido = 0 "
            "ORDER BY criado_em DESC",
            (telegram_id,),
        )
        return [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()


async def get_historico_vendas(telegram_id: int) -> list[dict]:
    """Retorna as posições já vendidas."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM carteira WHERE telegram_id = ? AND vendido = 1 "
            "ORDER BY data_venda DESC LIMIT 20",
            (telegram_id,),
        )
        return [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()


# ── Configuração de alertas ────────────────────────────────────


async def get_alerta_config(telegram_id: int) -> dict:
    """Retorna a configuração de alertas do usuário."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM alertas_config WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        # Criar config padrão
        await db.execute(
            "INSERT INTO alertas_config (telegram_id) VALUES (?)",
            (telegram_id,),
        )
        await db.commit()
        return {
            "telegram_id": telegram_id,
            "alertas_ativos": 1,
            "hora_alerta": "09:00",
            "intervalo_horas": 24,
            "ultimo_alerta": None,
        }
    finally:
        await db.close()


async def toggle_alertas(telegram_id: int, ativo: bool) -> None:
    """Ativa ou desativa alertas para um usuário."""
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO alertas_config (telegram_id, alertas_ativos) "
            "VALUES (?, ?) ON CONFLICT(telegram_id) "
            "DO UPDATE SET alertas_ativos = ?",
            (telegram_id, int(ativo), int(ativo)),
        )
        await db.commit()
    finally:
        await db.close()


async def update_ultimo_alerta(telegram_id: int) -> None:
    """Atualiza o timestamp do último alerta enviado."""
    db = await get_db()
    try:
        await db.execute(
            "UPDATE alertas_config SET ultimo_alerta = datetime('now') "
            "WHERE telegram_id = ?",
            (telegram_id,),
        )
        await db.commit()
    finally:
        await db.close()


async def get_usuarios_para_alertar() -> list[dict]:
    """
    Retorna usuários que devem receber alertas
    (alertas ativos + carteira não vazia + intervalo cumprido).
    """
    db = await get_db()
    try:
        cursor = await db.execute(
            """
            SELECT DISTINCT a.telegram_id, a.ultimo_alerta, a.intervalo_horas
            FROM alertas_config a
            INNER JOIN carteira c ON c.telegram_id = a.telegram_id AND c.vendido = 0
            WHERE a.alertas_ativos = 1
            AND (
                a.ultimo_alerta IS NULL
                OR datetime(a.ultimo_alerta, '+' || a.intervalo_horas || ' hours')
                    <= datetime('now')
            )
            """
        )
        return [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()
