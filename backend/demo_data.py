"""
AURA — Demo Mode Pre-baked Data
Golden responses for Shift+D demo mode — bypasses all APIs.
"""

DEMO_TRANSCRIPT = "Aura, Sophie Laurent from Harrods is interested in 150 units of the Obsidian Trench coat at 1200 euros"

DEMO_AGENT1_RESULT = {
    "buyer": "Sophie Laurent",
    "store": "Harrods",
    "item": "Obsidian Trench",
    "quantity": 150,
    "price": 1200.00,
    "currency": "EUR",
}

DEMO_AGENT2_RESULT = {
    "item_found": True,
    "item_id": 1,
    "item_name": "Obsidian Trench",
    "collection": "AW25 Noir",
    "color": "Black",
    "requested_qty": 150,
    "available_qty": 120,
    "stock_sufficient": False,
    "wholesale_cost_eur": 850.00,
    "proposed_price_eur": 1200.00,
    "actual_margin_pct": 41.2,
    "min_margin_pct": 35.0,
    "margin_healthy": True,
    "summary": "Stock insufficient: 120 available vs 150 requested. Margin healthy at 41.2% (min 35.0%). Suggest adjusting quantity to 120 units.",
}

DEMO_AGENT3_RESULT = {
    "action": "COUNTER",
    "reasoning": "Stock limited to 120 units — cannot fulfill 150. Margin is healthy at 41.2%, above the 35% floor. Recommend counter-offering at 120 units with a slight price increase to €1,350 to compensate for exclusivity of reduced allocation. This preserves the relationship with Harrods while maximizing revenue on available stock.",
    "suggested_quantity": 120,
    "suggested_price": 1350.00,
    "original_quantity": 150,
    "original_price": 1200.00,
    "voice_summary": "Stock confirmed at 120 units, not 150. Margin is strong. I suggest counter-offering at 120 units at 1350 euros — that's a premium for the exclusivity of the limited allocation.",
}

DEMO_AGENT4_EMAIL = """Subject: Order Confirmation — Obsidian Trench | Harrods × Maison AURA

Dear Ms. Laurent,

It is with great pleasure that we confirm your order for the Obsidian Trench from our AW25 Noir collection.

Order Details:
• Item: Obsidian Trench — AW25 Noir Collection
• Quantity: 120 units
• Agreed Price: €1,350 per unit
• Total Value: €162,000

Your allocation has been secured from our atelier's limited production run. Each piece will be individually inspected before dispatch to ensure it meets the exacting standards that both Harrods and Maison AURA are known for.

Estimated delivery to your Knightsbridge location: 4–6 weeks from confirmation.

We look forward to continuing this exceptional partnership.

With distinguished regards,

Maison AURA
Paris Fashion Week — AW25 Showroom
"""

# Agent log lines for typewriter display
DEMO_AGENT_LOGS = [
    {
        "agent": 1,
        "label": "EXTRACTOR",
        "content": "✓ Buyer: Sophie Laurent | Store: Harrods | Item: Obsidian Trench | Qty: 150 | Price: €1,200",
    },
    {
        "agent": 2,
        "label": "INVENTORY",
        "content": "✓ Stock: 120/150 (INSUFFICIENT) | Margin: 41.2% (healthy, min 35%) | Cost: €850",
    },
    {
        "agent": 3,
        "label": "STRATEGIST",
        "content": "⚡ COUNTER-OFFER → 120 units @ €1,350 | Reason: Limited stock, premium for exclusivity | Total: €162,000",
    },
]

DEMO_TTS_TEXT = DEMO_AGENT3_RESULT["voice_summary"]
