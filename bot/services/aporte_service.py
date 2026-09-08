"""Serviço de gestão do plano de aporte mensal."""

from database.db import get_db


async def salvar_plano_mensal(
    telegram_id: int, valor: float, dia: int, perfil: str
) -> None:
    """Salva ou atualiza o plano de aporte mensal."""
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO plano_mensal "
            "(telegram_id, valor_mensal, dia_pagamento, perfil_risco) "
            "VALUES (?, ?, ?, ?) ON CONFLICT(telegram_id) "
            "DO UPDATE SET valor_mensal = ?, dia_pagamento = ?, "
            "perfil_risco = ?, ativo = 1",
            (telegram_id, valor, dia, perfil, valor, dia, perfil),
        )
        await db.commit()
    finally:
        await db.close()


async def get_plano_mensal(telegram_id: int) -> dict | None:
    """Retorna o plano mensal do usuário."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM plano_mensal WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def toggle_plano(telegram_id: int, ativo: bool) -> None:
    """Ativa ou desativa o plano mensal."""
    db = await get_db()
    try:
        await db.execute(
            "UPDATE plano_mensal SET ativo = ? WHERE telegram_id = ?",
            (int(ativo), telegram_id),
        )
        await db.commit()
    finally:
        await db.close()


async def get_usuarios_para_aporte(dia: int) -> list[dict]:
    """Retorna usuários que devem receber lembrete de aporte hoje."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM plano_mensal WHERE dia_pagamento = ? AND ativo = 1",
            (dia,),
        )
        return [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()


async def get_usuarios_com_carteira() -> list[dict]:
    """Retorna usuários com posições ativas na carteira (para relatório semanal)."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """
            SELECT DISTINCT c.telegram_id
            FROM carteira c
            WHERE c.vendido = 0
            """
        )
        return [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()
