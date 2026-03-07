"""
AURA — 4-Agent AI Pipeline
Agent 1: Data Extractor (voice → structured JSON)
Agent 2: Inventory & Margin Checker (JSON → DB lookup → report)
Agent 3: Deal Strategist (report → ACCEPT/COUNTER/UPSELL)
Agent 4: Luxury Copywriter (deal → haute couture confirmation email)
"""

import json
import os
from groq import Groq
from database import find_item_by_name, check_stock, calculate_margin

# Lazy client init — allows app to start without API key (for demo mode)
_client = None
MODEL = "llama-3.3-70b-versatile"


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not set — cannot run live agent pipeline")
        _client = Groq(api_key=api_key)
    return _client


def _call_llm(system_prompt: str, user_message: str, json_mode: bool = False) -> str:
    """Shared LLM call wrapper."""
    client = _get_client()
    kwargs = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.3,
        "max_tokens": 1024,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    
    completion = client.chat.completions.create(**kwargs)
    return completion.choices[0].message.content


# ─── Agent 1: Data Extractor ───

def agent_extract(transcript: str) -> dict:
    """Parse chaotic voice input into structured deal data."""
    system = """You are a data extraction agent for a luxury fashion B2B sales system.
Extract the following fields from the sales rep's voice input:
- buyer: the person's name (the buyer/contact)
- store: the store or company name
- item: the fashion item name
- quantity: number of units (integer)
- price: the proposed price per unit (number)
- currency: the currency (default EUR if not specified)

Return ONLY valid JSON with these exact keys. If a field is unclear, use your best guess from context.
Always output JSON, nothing else."""

    raw = _call_llm(system, transcript, json_mode=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "Failed to parse extraction", "raw": raw}


# ─── Agent 2: Inventory & Margin Checker ───

def agent_inventory_check(extracted: dict) -> dict:
    """Query DB for stock and margin, return structured report."""
    item_name = extracted.get("item", "")
    quantity = extracted.get("quantity", 0)
    price = extracted.get("price", 0)

    item = find_item_by_name(item_name)
    if not item:
        return {
            "item_found": False,
            "item_name": item_name,
            "summary": f"Item '{item_name}' not found in inventory.",
        }

    stock_ok, current_stock = check_stock(item["id"], quantity)
    actual_margin, min_margin, cost = calculate_margin(item["id"], price)

    result = {
        "item_found": True,
        "item_id": item["id"],
        "item_name": item["item_name"],
        "collection": item["collection"],
        "color": item["color"],
        "requested_qty": quantity,
        "available_qty": current_stock,
        "stock_sufficient": stock_ok,
        "wholesale_cost_eur": cost,
        "proposed_price_eur": price,
        "actual_margin_pct": round(actual_margin, 1) if actual_margin else 0,
        "min_margin_pct": min_margin,
        "margin_healthy": actual_margin >= min_margin if actual_margin and min_margin else False,
    }

    # Build summary
    parts = []
    if not stock_ok:
        parts.append(f"Stock insufficient: {current_stock} available vs {quantity} requested.")
    else:
        parts.append(f"Stock OK: {current_stock} available for {quantity} requested.")
    
    if actual_margin is not None:
        health = "healthy" if actual_margin >= min_margin else "BELOW MINIMUM"
        parts.append(f"Margin {health} at {actual_margin:.1f}% (min {min_margin}%).")
    
    if not stock_ok:
        parts.append(f"Suggest adjusting quantity to {current_stock} units.")

    result["summary"] = " ".join(parts)
    return result


# ─── Agent 3: Deal Strategist ───

def agent_strategist(extracted: dict, inventory_report: dict) -> dict:
    """Decide: ACCEPT / COUNTER-OFFER / UPSELL based on inventory report."""
    system = """You are a luxury fashion deal strategist for Paris Fashion Week B2B negotiations.
Based on the inventory report, decide one of three actions:
- ACCEPT: stock sufficient and margin healthy. Approve the deal as-is.
- COUNTER: stock insufficient OR margin too low. Suggest adjusted quantity and/or price.
- UPSELL: stock is very high (>2x requested) and margin healthy. Suggest the buyer takes more.

Return ONLY valid JSON with these keys:
- action: "ACCEPT" or "COUNTER" or "UPSELL"
- reasoning: 2-3 sentence explanation
- suggested_quantity: the recommended quantity (same as original if ACCEPT)
- suggested_price: the recommended price per unit (same as original if ACCEPT)
- original_quantity: the originally requested quantity
- original_price: the originally requested price
- voice_summary: a concise 1-2 sentence summary to be spoken aloud to the sales rep through their earpiece. Natural, conversational tone. No jargon."""

    context = f"""DEAL REQUEST:
Buyer: {extracted.get('buyer', 'Unknown')} from {extracted.get('store', 'Unknown')}
Item: {extracted.get('item', 'Unknown')}
Quantity: {extracted.get('quantity', 0)} units
Price: €{extracted.get('price', 0)} per unit

INVENTORY REPORT:
{json.dumps(inventory_report, indent=2)}"""

    raw = _call_llm(system, context, json_mode=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"action": "COUNTER", "reasoning": "Parse error, defaulting to counter.", "raw": raw}


# ─── Agent 4: Luxury Copywriter ───

def agent_copywriter(extracted: dict, strategy: dict) -> str:
    """Generate haute couture order confirmation email."""
    system = """You are a luxury fashion copywriter for a prestigious Parisian maison.
Write a brief, elegant order confirmation email in the tone of Chanel or Dior correspondence.

Rules:
- Use formal, prestigious vocabulary
- Address the buyer by name with proper honorifics
- Include order details (item, quantity, price, total)
- Mention the collection name
- Keep it under 200 words
- Sign off as "Maison AURA" with "Paris Fashion Week" reference
- This must feel like receiving a letter from a fashion house, NOT a Shopify receipt
- Include a subject line starting with "Subject: "

Return ONLY the email text, no JSON wrapping."""

    context = f"""CONFIRMED ORDER:
Buyer: {extracted.get('buyer', 'Valued Client')}
Store: {extracted.get('store', '')}
Item: {strategy.get('suggested_quantity', extracted.get('quantity', 0))} × {extracted.get('item', 'item')}
Price: €{strategy.get('suggested_price', extracted.get('price', 0))} per unit
Collection: (use your fashion knowledge)
Total: €{strategy.get('suggested_quantity', extracted.get('quantity', 0)) * strategy.get('suggested_price', extracted.get('price', 0)):,.0f}"""

    return _call_llm(system, context, json_mode=False)


# ─── Pipeline Runner ───

async def run_pipeline(transcript: str, send_log):
    """Run all agents sequentially, sending logs after each step.
    send_log is an async callable: send_log(agent_num, label, content, data)
    Returns (extracted, inventory_report, strategy)
    """
    # Agent 1 — Extract
    extracted = agent_extract(transcript)
    await send_log(1, "EXTRACTOR",
        f"✓ Buyer: {extracted.get('buyer', '?')} | Store: {extracted.get('store', '?')} | "
        f"Item: {extracted.get('item', '?')} | Qty: {extracted.get('quantity', '?')} | "
        f"Price: €{extracted.get('price', '?'):,}" if isinstance(extracted.get('price'), (int, float)) else
        f"✓ Buyer: {extracted.get('buyer', '?')} | Store: {extracted.get('store', '?')} | "
        f"Item: {extracted.get('item', '?')} | Qty: {extracted.get('quantity', '?')} | "
        f"Price: {extracted.get('price', '?')}",
        extracted)

    # Agent 2 — Inventory check
    inventory_report = agent_inventory_check(extracted)
    stock_status = "OK" if inventory_report.get("stock_sufficient") else "INSUFFICIENT"
    margin_status = "healthy" if inventory_report.get("margin_healthy") else "LOW"
    await send_log(2, "INVENTORY",
        f"✓ Stock: {inventory_report.get('available_qty', '?')}/{inventory_report.get('requested_qty', '?')} "
        f"({stock_status}) | Margin: {inventory_report.get('actual_margin_pct', '?')}% "
        f"({margin_status}, min {inventory_report.get('min_margin_pct', '?')}%) | "
        f"Cost: €{inventory_report.get('wholesale_cost_eur', '?')}",
        inventory_report)

    # Agent 3 — Strategy
    strategy = agent_strategist(extracted, inventory_report)
    action = strategy.get("action", "COUNTER")
    emoji = {"ACCEPT": "✅", "COUNTER": "⚡", "UPSELL": "📈"}.get(action, "⚡")
    sq = strategy.get("suggested_quantity", extracted.get("quantity", "?"))
    sp = strategy.get("suggested_price", extracted.get("price", "?"))
    total = sq * sp if isinstance(sq, (int, float)) and isinstance(sp, (int, float)) else "?"
    await send_log(3, "STRATEGIST",
        f"{emoji} {action} → {sq} units @ €{sp:,} | "
        f"Reason: {strategy.get('reasoning', '?')[:80]}... | Total: €{total:,}" if isinstance(total, (int, float)) else
        f"{emoji} {action} → {sq} units @ €{sp} | Reason: {strategy.get('reasoning', '?')[:80]}...",
        strategy)

    return extracted, inventory_report, strategy
