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

    # Model assignments: which model wore which item (runway / pre-show)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_name TEXT NOT NULL,
            item_id INTEGER NOT NULL,
            event TEXT NOT NULL DEFAULT 'runway show',
            assigned_at TEXT NOT NULL,
            FOREIGN KEY (item_id) REFERENCES inventory(id)
        )
    """)

    # Seed inventory if empty
    count = cursor.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
    if count == 0:
        seed_data = [
            ("Obsidian Trench", "AW25 Noir", "Black", 120, 850.00, 35.0),
            ("Ivory Blazer", "SS25 Lumiere", "Ivory", 80, 620.00, 40.0),
            ("Noir Midi Dress", "AW25 Noir", "Black", 200, 480.00, 45.0),
            ("Crimson Silk Blouse", "SS25 Lumiere", "Red", 150, 320.00, 50.0),
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

    # Seed model assignments if empty
    model_count = cursor.execute("SELECT COUNT(*) FROM model_assignments").fetchone()[0]
    if model_count == 0:
        model_seeds = [
            ("Jade Li", 3, "pre-show fitting"),       # Noir Midi Dress
            ("Amara Osei", 1, "runway show"),           # Obsidian Trench
            ("Sofia Vidal", 7, "gala evening"),         # Pearl Evening Gown
            ("Lena Richter", 6, "runway show"),         # Onyx Leather Jacket
            ("Yuki Tanaka", 10, "runway show"),         # Midnight Velvet Suit
        ]
        for model_name, item_id, event in model_seeds:
            cursor.execute(
                "INSERT INTO model_assignments (model_name, item_id, event, assigned_at) VALUES (?, ?, ?, ?)",
                (model_name, item_id, event, datetime.now().isoformat()),
            )

    conn.commit()
    conn.close()


# ─── Seed Data (for reset) ───

SEED_INVENTORY = [
    ("Obsidian Trench", "AW25 Noir", "Black", 120, 850.00, 35.0),
    ("Ivory Blazer", "SS25 Lumiere", "Ivory", 80, 620.00, 40.0),
    ("Noir Midi Dress", "AW25 Noir", "Black", 200, 480.00, 45.0),
    ("Crimson Silk Blouse", "SS25 Lumiere", "Red", 150, 320.00, 50.0),
    ("Glacial Cashmere Coat", "AW25 Noir", "Ice Blue", 45, 1200.00, 30.0),
    ("Onyx Leather Jacket", "AW25 Noir", "Black", 60, 980.00, 35.0),
    ("Pearl Evening Gown", "Gala Collection", "Champagne", 30, 2100.00, 25.0),
    ("Slate Wool Trousers", "AW25 Noir", "Charcoal", 180, 380.00, 45.0),
    ("Rose Gold Mini Bag", "Accessories", "Rose Gold", 250, 290.00, 55.0),
    ("Midnight Velvet Suit", "AW25 Noir", "Navy", 15, 1450.00, 30.0),
]


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


def get_demand_data(item_id: int) -> dict:
    """Get demand signals for an item: order count, total quantity ordered, and low-stock flag."""
    conn = get_connection()
    # Count confirmed + suspended orders (pending = not yet decided, skip)
    row = conn.execute("""
        SELECT COUNT(*) as order_count, COALESCE(SUM(quantity), 0) as total_qty_ordered
        FROM orders
        WHERE item_id = ? AND status IN ('confirmed', 'suspended')
    """, (item_id,)).fetchone()
    # Check current stock for scarcity signal
    stock_row = conn.execute("SELECT stock_qty FROM inventory WHERE id = ?", (item_id,)).fetchone()
    conn.close()

    order_count = row["order_count"] if row else 0
    total_qty = row["total_qty_ordered"] if row else 0
    current_stock = stock_row["stock_qty"] if stock_row else 0

    # Demand level heuristic: high if 2+ orders OR stock < 30 units
    if order_count >= 2 or current_stock < 30:
        level = "HIGH"
    elif order_count >= 1 or current_stock < 60:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "item_id": item_id,
        "order_count": order_count,
        "total_qty_ordered": total_qty,
        "current_stock": current_stock,
        "demand_level": level,
    }


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


# ─── Stock Management ───


def reset_inventory():
    """Reset all inventory to original seed quantities and clear orders + model assignments."""
    conn = get_connection()
    cursor = conn.cursor()
    # Reset stock quantities to seed values
    for name, collection, color, qty, price, margin in SEED_INVENTORY:
        cursor.execute(
            "UPDATE inventory SET stock_qty = ?, wholesale_price_eur = ?, min_margin_pct = ? WHERE item_name = ?",
            (qty, price, margin, name),
        )
    # Clear all orders
    cursor.execute("DELETE FROM orders")
    conn.commit()
    conn.close()


def add_stock(item_name: str, quantity: int) -> dict | None:
    """Add stock to an item by name (fuzzy matched). Returns updated item or None."""
    item = find_item_by_name(item_name)
    if not item:
        return None
    conn = get_connection()
    conn.execute(
        "UPDATE inventory SET stock_qty = stock_qty + ? WHERE id = ?",
        (quantity, item["id"]),
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM inventory WHERE id = ?", (item["id"],)).fetchone()
    conn.close()
    return dict(updated) if updated else None


def deduct_stock_external(item_name: str, quantity: int, colleague: str = "colleague") -> dict | None:
    """Simulate a colleague deducting stock. Returns updated item or None."""
    item = find_item_by_name(item_name)
    if not item:
        return None
    conn = get_connection()
    conn.execute(
        "UPDATE inventory SET stock_qty = MAX(0, stock_qty - ?) WHERE id = ?",
        (quantity, item["id"]),
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM inventory WHERE id = ?", (item["id"],)).fetchone()
    conn.close()
    return dict(updated) if updated else None


# ─── Model Assignments ───


def assign_model(model_name: str, item_name: str, event: str = "runway show") -> dict | None:
    """Assign a model to an item (e.g., 'Jade Li wore the Noir Midi Dress')."""
    item = find_item_by_name(item_name)
    if not item:
        return None
    conn = get_connection()
    conn.execute(
        "INSERT INTO model_assignments (model_name, item_id, event, assigned_at) VALUES (?, ?, ?, ?)",
        (model_name, item["id"], event, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return {"model_name": model_name, "item_name": item["item_name"], "event": event}


def find_item_by_model(model_name: str) -> list[dict]:
    """Find all items worn/assigned to a model. Returns list of items with model info."""
    conn = get_connection()
    # Fuzzy match model name
    rows = conn.execute("""
        SELECT ma.model_name, ma.event, i.*
        FROM model_assignments ma
        JOIN inventory i ON ma.item_id = i.id
    """).fetchall()
    conn.close()

    query = model_name.strip().lower()
    results = []
    for row in rows:
        row_dict = dict(row)
        name_lower = row_dict["model_name"].lower()
        # Exact or partial match
        if query in name_lower or name_lower in query or _fuzzy_score(query, name_lower) >= 0.6:
            results.append(row_dict)
    return results


def get_model_assignments() -> list[dict]:
    """Return all model assignments with item names."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT ma.model_name, ma.event, i.item_name, i.id as item_id
        FROM model_assignments ma
        JOIN inventory i ON ma.item_id = i.id
        ORDER BY ma.assigned_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Auto-init on import
init_db()
