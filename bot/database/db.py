"""Banco de dados SQLite assíncrono para persistência de dados dos usuários."""

import os
import aiosqlite
from config import DATABASE_PATH


async def get_db() -> aiosqlite.Connection:
    """Retorna conexão com o banco de dados."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    """Cria as tabelas se não existirem."""
    db = await get_db()
    try:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                telegram_id INTEGER PRIMARY KEY,
                nome TEXT,
                renda_mensal REAL DEFAULT 0,
                is_premium INTEGER DEFAULT 0,
                premium_ate TEXT,
                consultas_hoje INTEGER DEFAULT 0,
                data_ultima_consulta TEXT,
                perfil_json TEXT DEFAULT '{}',
                criado_em TEXT DEFAULT (datetime('now')),
                atualizado_em TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS gastos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                valor REAL NOT NULL,
                categoria TEXT NOT NULL,
                descricao TEXT,
                data TEXT DEFAULT (date('now')),
                criado_em TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (telegram_id) REFERENCES usuarios(telegram_id)
            );

            CREATE TABLE IF NOT EXISTS dividas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                valor_total REAL NOT NULL,
                valor_parcela REAL,
                taxa_juros_mensal REAL DEFAULT 0,
                parcelas_restantes INTEGER,
                criado_em TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (telegram_id) REFERENCES usuarios(telegram_id)
            );

            CREATE TABLE IF NOT EXISTS metas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                valor_alvo REAL NOT NULL,
                valor_atual REAL DEFAULT 0,
                prazo_meses INTEGER,
                criado_em TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (telegram_id) REFERENCES usuarios(telegram_id)
            );

            CREATE TABLE IF NOT EXISTS investimentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                banco TEXT,
                valor REAL NOT NULL,
                percentual_cdi REAL DEFAULT 100,
                data_inicio TEXT DEFAULT (date('now')),
                prazo_meses INTEGER,
                criado_em TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (telegram_id) REFERENCES usuarios(telegram_id)
            );

            CREATE TABLE IF NOT EXISTS carteira (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                ativo TEXT NOT NULL,
                tipo TEXT NOT NULL DEFAULT 'crypto',
                preco_compra REAL NOT NULL,
                quantidade REAL,
                valor_investido REAL NOT NULL,
                data_compra TEXT DEFAULT (date('now')),
                vendido INTEGER DEFAULT 0,
                preco_venda REAL,
                data_venda TEXT,
                criado_em TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (telegram_id) REFERENCES usuarios(telegram_id)
            );

            CREATE TABLE IF NOT EXISTS alertas_config (
                telegram_id INTEGER PRIMARY KEY,
                alertas_ativos INTEGER DEFAULT 1,
                hora_alerta TEXT DEFAULT '09:00',
                intervalo_horas INTEGER DEFAULT 24,
                ultimo_alerta TEXT,
                FOREIGN KEY (telegram_id) REFERENCES usuarios(telegram_id)
            );

            CREATE TABLE IF NOT EXISTS plano_mensal (
                telegram_id INTEGER PRIMARY KEY,
                valor_mensal REAL NOT NULL,
                dia_pagamento INTEGER NOT NULL DEFAULT 5,
                perfil_risco TEXT NOT NULL DEFAULT 'moderado',
                ativo INTEGER DEFAULT 1,
                criado_em TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (telegram_id) REFERENCES usuarios(telegram_id)
            );

            CREATE TABLE IF NOT EXISTS gamificacao (
                telegram_id INTEGER PRIMARY KEY,
                xp INTEGER DEFAULT 0,
                nivel INTEGER DEFAULT 1,
                streak_dias INTEGER DEFAULT 0,
                maior_streak INTEGER DEFAULT 0,
                ultimo_acesso TEXT,
                conquistas TEXT DEFAULT '[]',
                FOREIGN KEY (telegram_id) REFERENCES usuarios(telegram_id)
            );

            CREATE TABLE IF NOT EXISTS indicacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                referred_id INTEGER NOT NULL,
                bonus_aplicado INTEGER DEFAULT 0,
                criado_em TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (referrer_id) REFERENCES usuarios(telegram_id),
                FOREIGN KEY (referred_id) REFERENCES usuarios(telegram_id)
            );

            CREATE TABLE IF NOT EXISTS orcamento (
                telegram_id INTEGER PRIMARY KEY,
                necessidades_pct REAL DEFAULT 50,
                desejos_pct REAL DEFAULT 30,
                investimentos_pct REAL DEFAULT 20,
                alertas_ativo INTEGER DEFAULT 1,
                criado_em TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (telegram_id) REFERENCES usuarios(telegram_id)
            );

            CREATE TABLE IF NOT EXISTS alerta_mercado_config (
                telegram_id INTEGER PRIMARY KEY,
                ativo INTEGER DEFAULT 1,
                ultimo_alerta TEXT,
                criado_em TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (telegram_id) REFERENCES usuarios(telegram_id)
            );

            CREATE TABLE IF NOT EXISTS alertas_preco (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                ativo TEXT NOT NULL,
                tipo TEXT NOT NULL DEFAULT 'crypto',
                direcao TEXT NOT NULL DEFAULT 'acima',
                preco_alvo REAL NOT NULL,
                ativo_flag INTEGER DEFAULT 1,
                notificado INTEGER DEFAULT 0,
                criado_em TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (telegram_id) REFERENCES usuarios(telegram_id)
            );

            CREATE TABLE IF NOT EXISTS resumo_matinal_config (
                telegram_id INTEGER PRIMARY KEY,
                ativo INTEGER DEFAULT 1,
                criado_em TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (telegram_id) REFERENCES usuarios(telegram_id)
            );

            CREATE INDEX IF NOT EXISTS idx_alertas_preco_user
                ON alertas_preco(telegram_id, ativo_flag);
            CREATE INDEX IF NOT EXISTS idx_gastos_user
                ON gastos(telegram_id, data);
            CREATE INDEX IF NOT EXISTS idx_dividas_user
                ON dividas(telegram_id);
            CREATE INDEX IF NOT EXISTS idx_metas_user
                ON metas(telegram_id);
            CREATE INDEX IF NOT EXISTS idx_investimentos_user
                ON investimentos(telegram_id);
            CREATE INDEX IF NOT EXISTS idx_carteira_user
                ON carteira(telegram_id, vendido);
            CREATE INDEX IF NOT EXISTS idx_alertas_user
                ON alertas_config(telegram_id);
            CREATE INDEX IF NOT EXISTS idx_indicacoes_referrer
                ON indicacoes(referrer_id);
            """
        )
        await db.commit()
    finally:
        await db.close()
