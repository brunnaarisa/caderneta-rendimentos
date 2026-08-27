"""Serviço de gestão de dados dos usuários."""

import json
from datetime import date, datetime

from database.db import get_db


async def get_or_create_user(telegram_id: int, nome: str = "") -> dict:
    """Busca ou cria um usuário no banco."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM usuarios WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cursor.fetchone()

        if row:
            return dict(row)

        await db.execute(
            "INSERT INTO usuarios (telegram_id, nome) VALUES (?, ?)",
            (telegram_id, nome),
        )
        await db.commit()

        cursor = await db.execute(
            "SELECT * FROM usuarios WHERE telegram_id = ?", (telegram_id,)
        )
        return dict(await cursor.fetchone())
    finally:
        await db.close()


async def update_profile(telegram_id: int, **kwargs) -> None:
    """Atualiza campos do perfil do usuário."""
    db = await get_db()
    try:
        allowed = {"nome", "renda_mensal", "is_premium", "premium_ate", "perfil_json"}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return

        sets = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [telegram_id]

        await db.execute(
            f"UPDATE usuarios SET {sets}, atualizado_em = datetime('now') "
            f"WHERE telegram_id = ?",
            values,
        )
        await db.commit()
    finally:
        await db.close()


async def check_and_use_consulta(telegram_id: int, daily_limit: int) -> bool:
    """
    Verifica se o usuário pode fazer uma consulta IA.
    Retorna True se pode (e incrementa o contador), False se atingiu o limite.
    Usuários premium sempre retornam True.
    """
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT is_premium, consultas_hoje, data_ultima_consulta "
            "FROM usuarios WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return False

        user = dict(row)

        # Premium: sempre pode
        if user["is_premium"]:
            return True

        hoje = date.today().isoformat()

        # Resetar contador se é um novo dia
        if user["data_ultima_consulta"] != hoje:
            await db.execute(
                "UPDATE usuarios SET consultas_hoje = 1, "
                "data_ultima_consulta = ? WHERE telegram_id = ?",
                (hoje, telegram_id),
            )
            await db.commit()
            return True

        # Verificar limite
        if user["consultas_hoje"] >= daily_limit:
            return False

        # Incrementar
        await db.execute(
            "UPDATE usuarios SET consultas_hoje = consultas_hoje + 1 "
            "WHERE telegram_id = ?",
            (telegram_id,),
        )
        await db.commit()
        return True
    finally:
        await db.close()


async def get_remaining_consultas(telegram_id: int, daily_limit: int) -> int | None:
    """Retorna quantas consultas restam hoje. None = ilimitado (premium)."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT is_premium, consultas_hoje, data_ultima_consulta "
            "FROM usuarios WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return 0

        user = dict(row)
        if user["is_premium"]:
            return None  # ilimitado

        hoje = date.today().isoformat()
        if user["data_ultima_consulta"] != hoje:
            return daily_limit

        return max(0, daily_limit - user["consultas_hoje"])
    finally:
        await db.close()


# ── Gastos ──────────────────────────────────────────────────────


async def add_gasto(
    telegram_id: int, valor: float, categoria: str, descricao: str = ""
) -> int:
    """Registra um gasto e retorna o ID."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO gastos (telegram_id, valor, categoria, descricao) "
            "VALUES (?, ?, ?, ?)",
            (telegram_id, valor, categoria, descricao),
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def get_gastos_mes(telegram_id: int, ano: int = 0, mes: int = 0) -> list[dict]:
    """Retorna gastos do mês (padrão: mês atual)."""
    if not ano:
        ano = date.today().year
    if not mes:
        mes = date.today().month

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM gastos WHERE telegram_id = ? "
            "AND strftime('%Y', data) = ? AND strftime('%m', data) = ? "
            "ORDER BY data DESC",
            (telegram_id, str(ano), f"{mes:02d}"),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_resumo_gastos_mes(telegram_id: int) -> dict:
    """Retorna resumo dos gastos do mês por categoria."""
    gastos = await get_gastos_mes(telegram_id)
    resumo: dict[str, float] = {}
    total = 0.0

    for g in gastos:
        cat = g["categoria"]
        resumo[cat] = resumo.get(cat, 0) + g["valor"]
        total += g["valor"]

    return {"categorias": resumo, "total": total, "quantidade": len(gastos)}


# ── Dívidas ─────────────────────────────────────────────────────


async def add_divida(
    telegram_id: int,
    nome: str,
    valor_total: float,
    taxa_juros_mensal: float = 0,
    valor_parcela: float = 0,
    parcelas_restantes: int = 0,
) -> int:
    """Registra uma dívida."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO dividas "
            "(telegram_id, nome, valor_total, taxa_juros_mensal, "
            "valor_parcela, parcelas_restantes) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                telegram_id,
                nome,
                valor_total,
                taxa_juros_mensal,
                valor_parcela,
                parcelas_restantes,
            ),
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def get_dividas(telegram_id: int) -> list[dict]:
    """Lista as dívidas de um usuário."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM dividas WHERE telegram_id = ? ORDER BY taxa_juros_mensal DESC",
            (telegram_id,),
        )
        return [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()


# ── Metas ───────────────────────────────────────────────────────


async def add_meta(
    telegram_id: int, nome: str, valor_alvo: float, prazo_meses: int = 0
) -> int:
    """Cria uma meta financeira."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO metas (telegram_id, nome, valor_alvo, prazo_meses) "
            "VALUES (?, ?, ?, ?)",
            (telegram_id, nome, valor_alvo, prazo_meses),
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def update_meta_valor(meta_id: int, valor_adicional: float) -> None:
    """Adiciona valor a uma meta."""
    db = await get_db()
    try:
        await db.execute(
            "UPDATE metas SET valor_atual = valor_atual + ? WHERE id = ?",
            (valor_adicional, meta_id),
        )
        await db.commit()
    finally:
        await db.close()


async def get_metas(telegram_id: int) -> list[dict]:
    """Lista as metas de um usuário."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM metas WHERE telegram_id = ? ORDER BY criado_em DESC",
            (telegram_id,),
        )
        return [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()


# ── Contexto completo para IA ──────────────────────────────────


async def get_financial_context(telegram_id: int) -> str:
    """
    Monta um resumo textual completo da situação financeira do usuário
    para enviar como contexto à IA.
    """
    user = await get_or_create_user(telegram_id)
    gastos = await get_resumo_gastos_mes(telegram_id)
    dividas = await get_dividas(telegram_id)
    metas = await get_metas(telegram_id)

    perfil = json.loads(user.get("perfil_json", "{}") or "{}")

    partes = []

    # Perfil
    renda = user.get("renda_mensal", 0)
    if renda:
        partes.append(f"Renda mensal: R${renda:,.2f}")
    if perfil.get("objetivo"):
        partes.append(f"Objetivo principal: {perfil['objetivo']}")
    if perfil.get("conhecimento"):
        partes.append(f"Nível de conhecimento financeiro: {perfil['conhecimento']}")

    # Gastos do mês
    if gastos["total"] > 0:
        partes.append(f"\nGastos este mês: R${gastos['total']:,.2f}")
        for cat, val in sorted(
            gastos["categorias"].items(), key=lambda x: x[1], reverse=True
        ):
            partes.append(f"  - {cat}: R${val:,.2f}")
        if renda:
            sobra = renda - gastos["total"]
            partes.append(
                f"  → Sobra estimada: R${sobra:,.2f} "
                f"({sobra / renda * 100:.0f}% da renda)"
            )

    # Dívidas
    if dividas:
        total_div = sum(d["valor_total"] for d in dividas)
        partes.append(f"\nDívidas totais: R${total_div:,.2f}")
        for d in dividas:
            juros = (
                f" (juros: {d['taxa_juros_mensal']:.1f}%/mês)"
                if d["taxa_juros_mensal"]
                else ""
            )
            partes.append(f"  - {d['nome']}: R${d['valor_total']:,.2f}{juros}")

    # Metas
    if metas:
        partes.append("\nMetas financeiras:")
        for m in metas:
            pct = (
                (m["valor_atual"] / m["valor_alvo"] * 100) if m["valor_alvo"] else 0
            )
            partes.append(
                f"  - {m['nome']}: R${m['valor_atual']:,.2f} / "
                f"R${m['valor_alvo']:,.2f} ({pct:.0f}%)"
            )

    if not partes:
        return "Usuário novo, sem dados financeiros cadastrados ainda."

    return "\n".join(partes)
