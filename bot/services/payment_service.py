"""
Serviço de pagamento via Mercado Pago (Pix).

Gera cobranças Pix, verifica status e ativa premium automaticamente.

Configuração necessária no .env:
    MERCADOPAGO_ACCESS_TOKEN=APP_USR-xxxx

Como obter:
1. Crie conta em mercadopago.com.br
2. Vá em Desenvolvedores > Suas integrações > Criar aplicação
3. Copie o Access Token de PRODUÇÃO
4. Adicione no .env
"""

import logging
from datetime import datetime, timedelta

import aiohttp

from config import MERCADOPAGO_ACCESS_TOKEN, PREMIUM_PRICE
from database.db import get_db

logger = logging.getLogger(__name__)

MP_API = "https://api.mercadopago.com"


# ── Criar cobrança Pix ─────────────────────────────────────


async def criar_cobranca_pix(
    telegram_id: int,
    email: str = "",
    meses: int = 1,
) -> dict | None:
    """
    Cria uma cobrança Pix no Mercado Pago.

    Retorna dict com:
    - payment_id: ID do pagamento no MP
    - qr_code: código "copia e cola" do Pix
    - qr_code_base64: imagem do QR code em base64
    - valor: valor cobrado
    - expiracao: data de expiração

    Retorna None se falhar.
    """
    if not MERCADOPAGO_ACCESS_TOKEN:
        logger.warning("MERCADOPAGO_ACCESS_TOKEN não configurado")
        return None

    valor = PREMIUM_PRICE * meses

    payload = {
        "transaction_amount": valor,
        "description": f"FinançasIA Premium — {meses} mês(es)",
        "payment_method_id": "pix",
        "payer": {
            "email": email or f"user_{telegram_id}@financasia.bot",
        },
        "external_reference": f"premium_{telegram_id}_{meses}m",
    }

    headers = {
        "Authorization": f"Bearer {MERCADOPAGO_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": f"premium-{telegram_id}-{datetime.now().strftime('%Y%m%d%H')}",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{MP_API}/v1/payments",
                json=payload,
                headers=headers,
            ) as resp:
                if resp.status != 201:
                    body = await resp.text()
                    logger.error(
                        "Erro ao criar Pix: %d — %s", resp.status, body
                    )
                    return None

                data = await resp.json()

        payment_id = data["id"]
        txn_data = data.get("point_of_interaction", {}).get(
            "transaction_data", {}
        )
        qr_code = txn_data.get("qr_code", "")
        qr_code_base64 = txn_data.get("qr_code_base64", "")
        expiracao = data.get(
            "date_of_expiration",
            (datetime.now() + timedelta(hours=24)).isoformat(),
        )

        # Salvar no banco
        db = await get_db()
        try:
            await db.execute(
                "INSERT INTO pagamentos "
                "(telegram_id, external_id, valor, status, tipo, expiracao) "
                "VALUES (?, ?, ?, 'pending', 'pix', ?)",
                (telegram_id, str(payment_id), valor, expiracao),
            )
            await db.commit()
        finally:
            await db.close()

        logger.info(
            "Pix criado: payment_id=%s, valor=%.2f, user=%s",
            payment_id, valor, telegram_id,
        )

        return {
            "payment_id": payment_id,
            "qr_code": qr_code,
            "qr_code_base64": qr_code_base64,
            "valor": valor,
            "expiracao": expiracao,
        }

    except Exception as e:
        logger.error("Erro ao criar cobrança Pix: %s", e)
        return None


# ── Verificar status do pagamento ──────────────────────────


async def verificar_pagamento(payment_id: str) -> str | None:
    """
    Verifica o status de um pagamento no Mercado Pago.
    Retorna: 'approved', 'pending', 'rejected', 'cancelled', ou None.
    """
    if not MERCADOPAGO_ACCESS_TOKEN:
        return None

    headers = {
        "Authorization": f"Bearer {MERCADOPAGO_ACCESS_TOKEN}",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{MP_API}/v1/payments/{payment_id}",
                headers=headers,
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return data.get("status")
    except Exception as e:
        logger.error("Erro ao verificar pagamento %s: %s", payment_id, e)
        return None


# ── Ativar premium ─────────────────────────────────────────


async def ativar_premium(telegram_id: int, meses: int = 1) -> None:
    """Ativa o premium para o usuário por N meses."""
    db = await get_db()
    try:
        premium_ate = (
            datetime.now() + timedelta(days=30 * meses)
        ).strftime("%Y-%m-%d")

        await db.execute(
            "UPDATE usuarios SET is_premium = 1, premium_ate = ? "
            "WHERE telegram_id = ?",
            (premium_ate, telegram_id),
        )
        await db.commit()
        logger.info("Premium ativado para %s até %s", telegram_id, premium_ate)
    finally:
        await db.close()


async def desativar_premium_expirado() -> list[int]:
    """Desativa premium de usuários expirados. Retorna IDs desativados."""
    db = await get_db()
    try:
        hoje = datetime.now().strftime("%Y-%m-%d")
        cursor = await db.execute(
            "SELECT telegram_id FROM usuarios "
            "WHERE is_premium = 1 AND premium_ate IS NOT NULL "
            "AND premium_ate < ?",
            (hoje,),
        )
        expirados = [dict(r)["telegram_id"] for r in await cursor.fetchall()]

        if expirados:
            await db.execute(
                "UPDATE usuarios SET is_premium = 0 "
                "WHERE is_premium = 1 AND premium_ate IS NOT NULL "
                "AND premium_ate < ?",
                (hoje,),
            )
            await db.commit()

        return expirados
    finally:
        await db.close()


# ── Pagamentos pendentes ──────────────────────────────────


async def get_pagamentos_pendentes() -> list[dict]:
    """Retorna pagamentos Pix pendentes para verificação."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM pagamentos "
            "WHERE status = 'pending' "
            "AND criado_em >= datetime('now', '-24 hours')"
        )
        return [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()


async def atualizar_status_pagamento(
    payment_id: str, status: str
) -> None:
    """Atualiza o status de um pagamento no banco."""
    db = await get_db()
    try:
        extra = ""
        params = [status, payment_id]
        if status == "approved":
            extra = ", pago_em = datetime('now')"

        await db.execute(
            f"UPDATE pagamentos SET status = ?{extra} "
            "WHERE external_id = ?",
            params,
        )
        await db.commit()
    finally:
        await db.close()


async def get_pagamento_por_external_id(payment_id: str) -> dict | None:
    """Busca pagamento pelo external_id (ID do Mercado Pago)."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM pagamentos WHERE external_id = ?",
            (payment_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()
