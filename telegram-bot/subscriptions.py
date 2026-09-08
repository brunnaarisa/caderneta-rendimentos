"""
Gerenciamento de assinaturas e limites de uso (modelo freemium).

Usa SQLite local — sem custo de infra. Quando escalar, migre pra PostgreSQL.
"""
import sqlite3
import os
import time
from datetime import datetime, timedelta

DB_PATH = os.getenv('BOT_DB_PATH', 'bot_data.db')

# Limites do plano gratuito
FREE_DAILY_QUERIES = 5
FREE_COMPARISONS = 3       # por dia
FREE_SIMULATIONS = 2        # por dia

# Limites do plano premium
PREMIUM_DAILY_QUERIES = 999  # ilimitado na prática
PREMIUM_COMPARISONS = 999
PREMIUM_SIMULATIONS = 999


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            plan TEXT DEFAULT 'free',
            plan_expires_at TEXT,
            referral_code TEXT UNIQUE,
            referred_by INTEGER,
            total_queries INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            last_active_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS daily_usage (
            user_id INTEGER,
            date TEXT,
            queries INTEGER DEFAULT 0,
            comparisons INTEGER DEFAULT 0,
            simulations INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, date)
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            alert_type TEXT,  -- 'cdi_change', 'daily_summary'
            enabled INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount_cents INTEGER,
            currency TEXT DEFAULT 'BRL',
            method TEXT,  -- 'pix', 'stripe'
            status TEXT DEFAULT 'pending',
            reference TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            confirmed_at TEXT
        );
    ''')
    conn.commit()
    conn.close()


def ensure_user(user_id, username=None, first_name=None):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
    if not user:
        import hashlib
        ref_code = hashlib.md5(str(user_id).encode()).hexdigest()[:8].upper()
        conn.execute(
            'INSERT INTO users (user_id, username, first_name, referral_code) VALUES (?, ?, ?, ?)',
            (user_id, username, first_name, ref_code)
        )
        conn.commit()
        user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
    else:
        conn.execute(
            'UPDATE users SET last_active_at = datetime("now"), username = ?, first_name = ? WHERE user_id = ?',
            (username, first_name, user_id)
        )
        conn.commit()
    conn.close()
    return dict(user)


def get_user(user_id):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None


def is_premium(user_id):
    user = get_user(user_id)
    if not user or user['plan'] != 'premium':
        return False
    if user['plan_expires_at']:
        expires = datetime.fromisoformat(user['plan_expires_at'])
        if expires < datetime.now():
            # Expirou: rebaixa pra free
            conn = get_db()
            conn.execute("UPDATE users SET plan = 'free' WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()
            return False
    return True


def get_daily_usage(user_id):
    today = datetime.now().strftime('%Y-%m-%d')
    conn = get_db()
    usage = conn.execute(
        'SELECT * FROM daily_usage WHERE user_id = ? AND date = ?',
        (user_id, today)
    ).fetchone()
    conn.close()
    if usage:
        return dict(usage)
    return {'user_id': user_id, 'date': today, 'queries': 0, 'comparisons': 0, 'simulations': 0}


def increment_usage(user_id, field='queries'):
    today = datetime.now().strftime('%Y-%m-%d')
    conn = get_db()
    conn.execute('''
        INSERT INTO daily_usage (user_id, date, {field})
        VALUES (?, ?, 1)
        ON CONFLICT(user_id, date)
        DO UPDATE SET {field} = {field} + 1
    '''.format(field=field), (user_id, today))
    conn.execute('UPDATE users SET total_queries = total_queries + 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()


def check_limit(user_id, field='queries'):
    premium = is_premium(user_id)
    usage = get_daily_usage(user_id)

    if premium:
        limits = {'queries': PREMIUM_DAILY_QUERIES, 'comparisons': PREMIUM_COMPARISONS,
                  'simulations': PREMIUM_SIMULATIONS}
    else:
        limits = {'queries': FREE_DAILY_QUERIES, 'comparisons': FREE_COMPARISONS,
                  'simulations': FREE_SIMULATIONS}

    current = usage.get(field, 0)
    limit = limits.get(field, FREE_DAILY_QUERIES)
    return current < limit, limit - current


def activate_premium(user_id, months=1):
    conn = get_db()
    expires = datetime.now() + timedelta(days=30 * months)
    conn.execute(
        "UPDATE users SET plan = 'premium', plan_expires_at = ? WHERE user_id = ?",
        (expires.isoformat(), user_id)
    )
    conn.commit()
    conn.close()


def apply_referral(user_id, referral_code):
    conn = get_db()
    referrer = conn.execute(
        'SELECT user_id FROM users WHERE referral_code = ? AND user_id != ?',
        (referral_code, user_id)
    ).fetchone()
    if referrer:
        conn.execute(
            'UPDATE users SET referred_by = ? WHERE user_id = ? AND referred_by IS NULL',
            (referrer['user_id'], user_id)
        )
        conn.commit()
        conn.close()
        return referrer['user_id']
    conn.close()
    return None


def get_referral_count(user_id):
    conn = get_db()
    count = conn.execute(
        'SELECT COUNT(*) as c FROM users WHERE referred_by = ?',
        (user_id,)
    ).fetchone()['c']
    conn.close()
    return count


def get_stats():
    conn = get_db()
    total_users = conn.execute('SELECT COUNT(*) as c FROM users').fetchone()['c']
    premium_users = conn.execute("SELECT COUNT(*) as c FROM users WHERE plan = 'premium'").fetchone()['c']
    today = datetime.now().strftime('%Y-%m-%d')
    active_today = conn.execute(
        'SELECT COUNT(DISTINCT user_id) as c FROM daily_usage WHERE date = ?',
        (today,)
    ).fetchone()['c']
    total_queries = conn.execute('SELECT SUM(total_queries) as c FROM users').fetchone()['c'] or 0
    conn.close()
    return {
        'total_users': total_users,
        'premium_users': premium_users,
        'active_today': active_today,
        'total_queries': total_queries,
    }
