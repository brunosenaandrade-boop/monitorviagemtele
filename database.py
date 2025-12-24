import aiosqlite
import json
from datetime import datetime
from typing import Optional

DATABASE_FILE = "flight_monitor.db"


async def init_db():
    """Inicializa o banco de dados com as tabelas necessárias."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS monitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                origin TEXT NOT NULL,
                destination TEXT NOT NULL,
                departure_date TEXT NOT NULL,
                return_date TEXT,
                adults INTEGER DEFAULT 1,
                max_price REAL,
                last_price REAL,
                last_check TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                monitor_id INTEGER NOT NULL,
                price REAL NOT NULL,
                currency TEXT DEFAULT 'BRL',
                flight_details TEXT,
                checked_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (monitor_id) REFERENCES monitors(id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_states (
                user_id INTEGER PRIMARY KEY,
                state TEXT,
                data TEXT
            )
        """)

        await db.commit()


async def save_monitor(user_id: int, chat_id: int, origin: str, destination: str,
                       departure_date: str, return_date: Optional[str] = None,
                       adults: int = 1, max_price: Optional[float] = None) -> int:
    """Salva um novo monitoramento."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        cursor = await db.execute("""
            INSERT INTO monitors (user_id, chat_id, origin, destination,
                                  departure_date, return_date, adults, max_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, chat_id, origin.upper(), destination.upper(),
              departure_date, return_date, adults, max_price))
        await db.commit()
        return cursor.lastrowid


async def get_user_monitors(user_id: int):
    """Retorna todos os monitoramentos ativos de um usuário."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM monitors
            WHERE user_id = ? AND is_active = 1
            ORDER BY created_at DESC
        """, (user_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_all_active_monitors():
    """Retorna todos os monitoramentos ativos."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM monitors WHERE is_active = 1
        """)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def update_monitor_price(monitor_id: int, price: float, flight_details: str):
    """Atualiza o preço de um monitoramento."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute("""
            UPDATE monitors
            SET last_price = ?, last_check = ?
            WHERE id = ?
        """, (price, datetime.now().isoformat(), monitor_id))

        await db.execute("""
            INSERT INTO price_history (monitor_id, price, flight_details)
            VALUES (?, ?, ?)
        """, (monitor_id, price, flight_details))

        await db.commit()


async def deactivate_monitor(monitor_id: int, user_id: int) -> bool:
    """Desativa um monitoramento."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        cursor = await db.execute("""
            UPDATE monitors SET is_active = 0
            WHERE id = ? AND user_id = ?
        """, (monitor_id, user_id))
        await db.commit()
        return cursor.rowcount > 0


async def get_price_history(monitor_id: int, limit: int = 10):
    """Retorna histórico de preços de um monitoramento."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM price_history
            WHERE monitor_id = ?
            ORDER BY checked_at DESC
            LIMIT ?
        """, (monitor_id, limit))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def save_user_state(user_id: int, state: str, data: dict):
    """Salva o estado do usuário durante o fluxo de conversa."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute("""
            INSERT OR REPLACE INTO user_states (user_id, state, data)
            VALUES (?, ?, ?)
        """, (user_id, state, json.dumps(data)))
        await db.commit()


async def get_user_state(user_id: int):
    """Recupera o estado do usuário."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM user_states WHERE user_id = ?
        """, (user_id,))
        row = await cursor.fetchone()
        if row:
            return {"state": row["state"], "data": json.loads(row["data"])}
        return None


async def clear_user_state(user_id: int):
    """Limpa o estado do usuário."""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
        await db.commit()
