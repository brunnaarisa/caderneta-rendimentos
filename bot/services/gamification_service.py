"""
Serviço de gamificação — XP, níveis, conquistas e streaks.

Cada ação do usuário ganha XP. Ao acumular XP, sobe de nível.
Conquistas são desbloqueadas por comportamentos específicos.
Streaks incentivam uso diário.
"""

import json
from datetime import date, timedelta

from database.db import get_db


# ── Níveis ─────────────────────────────────────────────────────

NIVEIS = [
    {"nivel": 1, "nome": "Curioso", "emoji": "🌱", "xp_min": 0},
    {"nivel": 2, "nome": "Iniciante", "emoji": "🌿", "xp_min": 100},
    {"nivel": 3, "nome": "Aprendiz", "emoji": "🌳", "xp_min": 300},
    {"nivel": 4, "nome": "Investidor", "emoji": "💹", "xp_min": 600},
    {"nivel": 5, "nome": "Estrategista", "emoji": "🧠", "xp_min": 1200},
    {"nivel": 6, "nome": "Expert", "emoji": "⭐", "xp_min": 2500},
    {"nivel": 7, "nome": "Mestre", "emoji": "🏅", "xp_min": 5000},
    {"nivel": 8, "nome": "Lenda", "emoji": "👑", "xp_min": 10000},
]


# ── Recompensas de XP ─────────────────────────────────────────

XP_REWARDS = {
    "consulta_ia": 10,
    "registrar_gasto": 5,
    "registrar_compra": 20,
    "completar_perfil": 50,
    "configurar_aporte": 30,
    "criar_meta": 15,
    "ver_dashboard": 5,
    "completar_aula": 25,
    "indicar_amigo": 100,
    "desafio": 15,
    "streak_diario": 10,  # multiplicado pelo streak
}


# ── Conquistas ─────────────────────────────────────────────────

CONQUISTAS = {
    "primeiro_gasto": {
        "nome": "Primeiro Passo",
        "emoji": "👣",
        "descricao": "Registrou o primeiro gasto",
    },
    "primeiro_investimento": {
        "nome": "Investidor",
        "emoji": "📈",
        "descricao": "Registrou a primeira compra de ativo",
    },
    "streak_7": {
        "nome": "Disciplinado",
        "emoji": "🔥",
        "descricao": "7 dias seguidos usando o bot",
    },
    "streak_30": {
        "nome": "Consistente",
        "emoji": "💎",
        "descricao": "30 dias seguidos usando o bot",
    },
    "plano_ativo": {
        "nome": "Planejador",
        "emoji": "📋",
        "descricao": "Configurou aporte mensal automático",
    },
    "carteira_3": {
        "nome": "Diversificado",
        "emoji": "🌈",
        "descricao": "3+ ativos diferentes na carteira",
    },
    "primeiro_lucro": {
        "nome": "Lucro!",
        "emoji": "💰",
        "descricao": "Primeiro ativo com lucro",
    },
    "meta_batida": {
        "nome": "Meta Batida",
        "emoji": "🎯",
        "descricao": "Completou uma meta financeira",
    },
    "sem_dividas": {
        "nome": "Livre",
        "emoji": "🕊️",
        "descricao": "Zerou todas as dívidas",
    },
    "indicou_3": {
        "nome": "Embaixador",
        "emoji": "🤝",
        "descricao": "Indicou 3 amigos",
    },
    "indicou_10": {
        "nome": "Influencer",
        "emoji": "⭐",
        "descricao": "Indicou 10 amigos",
    },
    "nivel_5": {
        "nome": "Estrategista",
        "emoji": "🧠",
        "descricao": "Alcançou o nível 5",
    },
    "nivel_8": {
        "nome": "Lendário",
        "emoji": "👑",
        "descricao": "Alcançou o nível máximo",
    },
    "patrimonio_10k": {
        "nome": "10K Club",
        "emoji": "🏆",
        "descricao": "Patrimônio acima de R$10.000",
    },
}


# ── Funções principais ─────────────────────────────────────────


async def get_or_create_gamificacao(telegram_id: int) -> dict:
    """Busca ou cria registro de gamificação do usuário."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM gamificacao WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)

        await db.execute(
            "INSERT INTO gamificacao (telegram_id) VALUES (?)",
            (telegram_id,),
        )
        await db.commit()

        cursor = await db.execute(
            "SELECT * FROM gamificacao WHERE telegram_id = ?",
            (telegram_id,),
        )
        return dict(await cursor.fetchone())
    finally:
        await db.close()


async def add_xp(telegram_id: int, acao: str, multiplicador: int = 1) -> dict:
    """
    Adiciona XP por uma ação. Retorna info sobre XP ganho e level up.
    {xp_ganho, xp_total, nivel_anterior, nivel_novo, subiu_nivel,
     conquistas_novas}
    """
    xp_base = XP_REWARDS.get(acao, 0)
    if not xp_base:
        return {"xp_ganho": 0}

    xp_ganho = xp_base * multiplicador
    gami = await get_or_create_gamificacao(telegram_id)
    xp_total = gami["xp"] + xp_ganho
    nivel_anterior = gami["nivel"]

    # Calcular novo nível
    nivel_novo = 1
    for n in NIVEIS:
        if xp_total >= n["xp_min"]:
            nivel_novo = n["nivel"]

    db = await get_db()
    try:
        await db.execute(
            "UPDATE gamificacao SET xp = ?, nivel = ? WHERE telegram_id = ?",
            (xp_total, nivel_novo, telegram_id),
        )
        await db.commit()
    finally:
        await db.close()

    # Verificar conquistas de nível
    conquistas_novas = []
    if nivel_novo >= 5 and nivel_anterior < 5:
        c = await desbloquear_conquista(telegram_id, "nivel_5")
        if c:
            conquistas_novas.append(c)
    if nivel_novo >= 8 and nivel_anterior < 8:
        c = await desbloquear_conquista(telegram_id, "nivel_8")
        if c:
            conquistas_novas.append(c)

    return {
        "xp_ganho": xp_ganho,
        "xp_total": xp_total,
        "nivel_anterior": nivel_anterior,
        "nivel_novo": nivel_novo,
        "subiu_nivel": nivel_novo > nivel_anterior,
        "conquistas_novas": conquistas_novas,
    }


async def registrar_acesso_diario(telegram_id: int) -> dict:
    """
    Registra acesso diário e atualiza streak.
    Retorna {streak_atual, streak_novo, xp_streak, conquistas}.
    """
    gami = await get_or_create_gamificacao(telegram_id)
    hoje = date.today().isoformat()
    ontem = (date.today() - timedelta(days=1)).isoformat()

    ultimo = gami.get("ultimo_acesso", "")
    streak = gami["streak_dias"]
    maior = gami["maior_streak"]

    # Já acessou hoje
    if ultimo == hoje:
        return {"streak_atual": streak, "streak_novo": False, "xp_streak": 0}

    # Continua streak (acessou ontem)
    if ultimo == ontem:
        streak += 1
    else:
        streak = 1

    if streak > maior:
        maior = streak

    # XP de streak (capped em 5x)
    xp_mult = min(streak, 5)

    db = await get_db()
    try:
        await db.execute(
            "UPDATE gamificacao SET streak_dias = ?, maior_streak = ?, "
            "ultimo_acesso = ? WHERE telegram_id = ?",
            (streak, maior, hoje, telegram_id),
        )
        await db.commit()
    finally:
        await db.close()

    # XP de streak
    resultado_xp = await add_xp(telegram_id, "streak_diario", xp_mult)

    # Conquistas de streak
    conquistas = list(resultado_xp.get("conquistas_novas", []))
    if streak >= 7:
        c = await desbloquear_conquista(telegram_id, "streak_7")
        if c:
            conquistas.append(c)
    if streak >= 30:
        c = await desbloquear_conquista(telegram_id, "streak_30")
        if c:
            conquistas.append(c)

    return {
        "streak_atual": streak,
        "streak_novo": True,
        "xp_streak": resultado_xp["xp_ganho"],
        "conquistas": conquistas,
    }


async def desbloquear_conquista(
    telegram_id: int, conquista_id: str
) -> dict | None:
    """
    Tenta desbloquear uma conquista. Retorna a conquista se for nova,
    None se já estava desbloqueada.
    """
    if conquista_id not in CONQUISTAS:
        return None

    gami = await get_or_create_gamificacao(telegram_id)
    conquistas = json.loads(gami.get("conquistas", "[]") or "[]")

    if conquista_id in conquistas:
        return None

    conquistas.append(conquista_id)

    db = await get_db()
    try:
        await db.execute(
            "UPDATE gamificacao SET conquistas = ? WHERE telegram_id = ?",
            (json.dumps(conquistas), telegram_id),
        )
        await db.commit()
    finally:
        await db.close()

    return CONQUISTAS[conquista_id]


async def get_info_nivel(nivel: int) -> dict:
    """Retorna info do nível atual."""
    for n in NIVEIS:
        if n["nivel"] == nivel:
            return n
    return NIVEIS[0]


async def get_proximo_nivel(nivel: int, xp: int) -> dict | None:
    """Retorna info do próximo nível e quanto falta."""
    for n in NIVEIS:
        if n["nivel"] == nivel + 1:
            return {
                **n,
                "xp_faltando": n["xp_min"] - xp,
            }
    return None  # Já é nível máximo


async def get_ranking(limit: int = 10) -> list[dict]:
    """Retorna o ranking global de XP."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT g.telegram_id, g.xp, g.nivel, g.streak_dias, "
            "u.nome FROM gamificacao g "
            "JOIN usuarios u ON g.telegram_id = u.telegram_id "
            "ORDER BY g.xp DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()


async def get_posicao_ranking(telegram_id: int) -> int:
    """Retorna a posição do usuário no ranking."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT COUNT(*) + 1 as posicao FROM gamificacao "
            "WHERE xp > (SELECT COALESCE(xp, 0) FROM gamificacao "
            "WHERE telegram_id = ?)",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        return dict(row)["posicao"] if row else 0
    finally:
        await db.close()


# ── Indicações ─────────────────────────────────────────────────


async def registrar_indicacao(referrer_id: int, referred_id: int) -> bool:
    """Registra uma indicação. Retorna True se é nova."""
    db = await get_db()
    try:
        # Verificar se já existe
        cursor = await db.execute(
            "SELECT id FROM indicacoes WHERE referred_id = ?",
            (referred_id,),
        )
        if await cursor.fetchone():
            return False

        # Não pode indicar a si mesmo
        if referrer_id == referred_id:
            return False

        await db.execute(
            "INSERT INTO indicacoes (referrer_id, referred_id) "
            "VALUES (?, ?)",
            (referrer_id, referred_id),
        )
        await db.commit()
        return True
    finally:
        await db.close()


async def get_total_indicacoes(telegram_id: int) -> int:
    """Retorna total de indicações de um usuário."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT COUNT(*) as total FROM indicacoes WHERE referrer_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        return dict(row)["total"] if row else 0
    finally:
        await db.close()


async def aplicar_bonus_indicacao(referrer_id: int) -> dict:
    """Aplica bônus de indicação (consultas grátis extras + XP)."""
    # Dar XP
    resultado_xp = await add_xp(referrer_id, "indicar_amigo")

    # Verificar conquistas
    total = await get_total_indicacoes(referrer_id)
    conquistas = list(resultado_xp.get("conquistas_novas", []))

    if total >= 3:
        c = await desbloquear_conquista(referrer_id, "indicou_3")
        if c:
            conquistas.append(c)
    if total >= 10:
        c = await desbloquear_conquista(referrer_id, "indicou_10")
        if c:
            conquistas.append(c)

    return {
        "xp_ganho": resultado_xp["xp_ganho"],
        "total_indicacoes": total,
        "conquistas": conquistas,
    }


# ── Orçamento ──────────────────────────────────────────────────


async def get_or_create_orcamento(telegram_id: int) -> dict:
    """Busca ou cria orçamento do usuário."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM orcamento WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)

        await db.execute(
            "INSERT INTO orcamento (telegram_id) VALUES (?)",
            (telegram_id,),
        )
        await db.commit()

        cursor = await db.execute(
            "SELECT * FROM orcamento WHERE telegram_id = ?",
            (telegram_id,),
        )
        return dict(await cursor.fetchone())
    finally:
        await db.close()


async def salvar_orcamento(
    telegram_id: int,
    necessidades: float = 50,
    desejos: float = 30,
    investimentos: float = 20,
) -> None:
    """Salva configuração de orçamento."""
    await get_or_create_orcamento(telegram_id)
    db = await get_db()
    try:
        await db.execute(
            "UPDATE orcamento SET necessidades_pct = ?, desejos_pct = ?, "
            "investimentos_pct = ? WHERE telegram_id = ?",
            (necessidades, desejos, investimentos, telegram_id),
        )
        await db.commit()
    finally:
        await db.close()
