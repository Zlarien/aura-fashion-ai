"""
AURA — SQLite Database Layer
Tables: inventory (pre-seeded luxury items), orders (confirmed deals)
"""

import sqlite3
import os
from datetime import datetime
from difflib import SequenceMatcher

DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables and seed inventory if empty."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            collection TEXT NOT NULL,
            color TEXT NOT NULL,
            stock_qty INTEGER NOT NULL,
            wholesale_price_eur REAL NOT NULL,
            min_margin_pct REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            buyer_name TEXT NOT NULL,
            store_name TEXT NOT NULL,
            item_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            agreed_price_eur REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            confirmation_email TEXT,
            FOREIGN KEY (item_id) REFERENCES inventory(id)
        )
    """)

    # Seed inventory if empty
    count = cursor.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
    if count == 0:
        seed_data = [
            ("Obsidian Trench", "AW25 Noir", "Black", 120, 850.00, 35.0),
            ("Ivory Blazer", "SS25 Lumière", "Ivory", 80, 620.00, 40.0),
            ("Noir Midi Dress", "AW25 Noir", "Black", 200, 480.00, 45.0),
            ("Crimson Silk Blouse", "SS25 Lumière", "Red", 150, 320.00, 50.0),
            ("Glacial Cashmere Coat", "AW25 Noir", "Ice Blue", 45, 1200.00, 30.0),
            ("Onyx Leather Jacket", "AW25 Noir", "Black", 60, 980.00, 35.0),
            ("Pearl Evening Gown", "Gala Collection", "Champagne", 30, 2100.00, 25.0),
            ("Slate Wool Trousers", "AW25 Noir", "Charcoal", 180, 380.00, 45.0),
            ("Rose Gold Mini Bag", "Accessories", "Rose Gold", 250, 290.00, 55.0),
            ("Midnight Velvet Suit", "AW25 Noir", "Navy", 15, 1450.00, 30.0),
        ]
        cursor.executemany(
            "INSERT INTO inventory (item_name, collection, color, stock_qty, wholesale_price_eur, min_margin_pct) VALUES (?, ?, ?, ?, ?, ?)",
            seed_data,
        )

    conn.commit()
    conn.close()


# ─── Query Functions ───


def get_all_inventory():
    """Return all inventory items as list of dicts."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM inventory").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_catalog_names() -> list[str]:
    """Return all item names in the catalog — used to feed Agent 1 for accurate matching."""
    conn = get_connection()
    rows = conn.execute("SELECT item_name FROM inventory").fetchall()
    conn.close()
    return [r["item_name"] for r in rows]


def _fuzzy_score(a: str, b: str) -> float:
    """Similarity ratio between two strings (0.0 to 1.0)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_item_by_name(name: str):
    """Find item by name with multi-layer matching:
    1. Exact substring match (LIKE)
    2. Word-overlap match (any word from query matches any word in item name)
    3. Fuzzy match via SequenceMatcher (threshold 0.5)
    """
    if not name or not name.strip():
        return None

    conn = get_connection()
    query = name.strip().lower()

    # Layer 1: Direct LIKE match (fast path)
    row = conn.execute(
        "SELECT * FROM inventory WHERE LOWER(item_name) LIKE ?",
        (f"%{query}%",),
    ).fetchone()
    if row:
        conn.close()
        return dict(row)

    # Layer 2: Word-overlap — check if any significant word from query matches item names
    all_items = conn.execute("SELECT * FROM inventory").fetchall()
    query_words = [w for w in query.split() if len(w) > 2]  # skip tiny words

    for item in all_items:
        item_lower = item["item_name"].lower()
        for word in query_words:
            if word in item_lower:
                conn.close()
                return dict(item)

    # Layer 3: Fuzzy match — find best SequenceMatcher score
    best_score = 0.0
    best_item = None
    for item in all_items:
        # Compare against full name and individual words
        score = _fuzzy_score(query, item["item_name"])
        # Also check each word pair for partial matches
        for item_word in item["item_name"].lower().split():
            for q_word in query_words:
                word_score = _fuzzy_score(q_word, item_word)
                score = max(score, word_score)
        if score > best_score:
            best_score = score
            best_item = item

    conn.close()

    if best_score >= 0.5 and best_item:
        return dict(best_item)

    return None


def check_stock(item_id: int, quantity: int):
    """Check if enough stock exists. Returns (available, current_stock)."""
    conn = get_connection()
    row = conn.execute("SELECT stock_qty FROM inventory WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    if not row:
        return False, 0
    return row["stock_qty"] >= quantity, row["stock_qty"]


def calculate_margin(item_id: int, proposed_price: float):
    """Calculate margin % for proposed price vs wholesale cost."""
    conn = get_connection()
    row = conn.execute(
        "SELECT wholesale_price_eur, min_margin_pct FROM inventory WHERE id = ?",
        (item_id,),
    ).fetchone()
    conn.close()
    if not row:
        return None, None, None
    cost = row["wholesale_price_eur"]
    min_margin = row["min_margin_pct"]
    actual_margin = ((proposed_price - cost) / cost) * 100
    return actual_margin, min_margin, cost


def create_order(buyer_name: str, store_name: str, item_id: int, quantity: int, agreed_price: float):
    """Create a pending order."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO orders (buyer_name, store_name, item_id, quantity, agreed_price_eur, status, created_at)
           VALUES (?, ?, ?, ?, ?, 'pending', ?)""",
        (buyer_name, store_name, item_id, quantity, agreed_price, datetime.now().isoformat()),
    )
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id


def confirm_order(order_id: int, email_text: str):
    """Confirm order and attach luxury email."""
    conn = get_connection()
    conn.execute(
        "UPDATE orders SET status = 'confirmed', confirmation_email = ? WHERE id = ?",
        (email_text, order_id),
    )
    # Deduct stock (clamped to 0 — never go negative)
    order = conn.execute("SELECT item_id, quantity FROM orders WHERE id = ?", (order_id,)).fetchone()
    if order:
        conn.execute(
            "UPDATE inventory SET stock_qty = MAX(0, stock_qty - ?) WHERE id = ?",
            (order["quantity"], order["item_id"]),
        )
    conn.commit()
    conn.close()


def suspend_order(order_id: int):
    """Suspend/hold an order — no stock deduction, keeps deal on hold for later decision."""
    conn = get_connection()
    conn.execute(
        "UPDATE orders SET status = 'suspended' WHERE id = ?",
        (order_id,),
    )
    conn.commit()
    conn.close()


def resume_order(order_id: int):
    """Move a suspended order back to pending for re-evaluation."""
    conn = get_connection()
    conn.execute(
        "UPDATE orders SET status = 'pending' WHERE id = ?",
        (order_id,),
    )
    conn.commit()
    conn.close()


def get_confirmed_orders():
    """Return all confirmed orders with item names."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT o.*, i.item_name
        FROM orders o
        JOIN inventory i ON o.item_id = i.id
        WHERE o.status = 'confirmed'
        ORDER BY o.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_suspended_orders():
    """Return all suspended/held orders with item names."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT o.*, i.item_name
        FROM orders o
        JOIN inventory i ON o.item_id = i.id
        WHERE o.status = 'suspended'
        ORDER BY o.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Auto-init on import
init_db()
