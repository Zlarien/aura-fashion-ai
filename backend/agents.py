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
from database import find_item_by_name, check_stock, calculate_margin, get_catalog_names

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
    """Parse chaotic voice input into structured deal data.
    Includes catalog awareness and number tolerance for speech transcription errors."""

    # Get current catalog items to feed the LLM
    try:
        catalog = get_catalog_names()
        catalog_str = ", ".join(catalog)
    except Exception:
        catalog_str = "Obsidian Trench, Ivory Blazer, Noir Midi Dress, Crimson Silk Blouse, Glacial Cashmere Coat, Onyx Leather Jacket, Pearl Evening Gown, Slate Wool Trousers, Rose Gold Mini Bag, Midnight Velvet Suit"

    system = f"""You are a data extraction agent for a luxury fashion B2B sales system at Paris Fashion Week.
Extract the following fields from the sales rep's voice input:
- buyer: the person's name (the buyer/contact)
- store: the store or company name
- item: the fashion item name — MUST match one from our catalog (see below)
- quantity: number of units (integer)
- price: the proposed price per unit (number)
- currency: the currency (default EUR if not specified)
- email: the buyer's email address if mentioned (null if not provided)

CATALOG ITEMS (match the closest one, even if the pronunciation is slightly off):
{catalog_str}

CRITICAL RULES FOR VOICE TRANSCRIPTION TOLERANCE:
1. ITEM MATCHING: The speaker may mispronounce or Deepgram may mistranscribe item names.
   Match to the CLOSEST catalog item. Examples:
   - "obsidian french" → "Obsidian Trench"
   - "ivory blazing" → "Ivory Blazer"
   - "glacial cashmere" → "Glacial Cashmere Coat"
   - "midnight velvet" → "Midnight Velvet Suit"
   - "rose gold bag" → "Rose Gold Mini Bag"
   - "pearl gown" → "Pearl Evening Gown"
   - "slate trousers" → "Slate Wool Trousers"
   Any partial match or phonetic similarity should resolve to the correct catalog item.

2. NUMBER TOLERANCE: Speech-to-text often garbles numbers. Apply common sense:
   - "a hundred and fifty" or "150" or "one fifty" → 150
   - "twelve hundred" or "1200" → 1200
   - If a quantity seems unreasonably large (>500 for fashion), it might be a price mistakenly placed
   - If a price seems unreasonably low (<50 for luxury fashion), it might be missing a zero
   - Reasonable quantity range: 1-500 units
   - Reasonable price range: €200-€5000 per unit for luxury fashion

3. BUYER/STORE: Names may be mistranscribed. Use your best interpretation.
   Common stores: Harrods, Selfridges, Galeries Lafayette, Le Bon Marché, Bergdorf Goodman,
   Neiman Marcus, Saks Fifth Avenue, Barneys, Harvey Nichols, Printemps.

Return ONLY valid JSON with these exact keys: buyer, store, item, quantity, price, currency, email.
If email was not mentioned, set it to null."""

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
    """Decide: ACCEPT / COUNTER-OFFER / UPSELL / SUSPEND based on inventory report."""
    system = """You are a luxury fashion deal strategist for Paris Fashion Week B2B negotiations.
Based on the inventory report, decide one of four actions:
- ACCEPT: stock sufficient and margin healthy. Approve the deal as-is.
- COUNTER: stock insufficient OR margin too low. Suggest adjusted quantity and/or price.
- UPSELL: stock is very high (>2x requested) and margin healthy. Suggest the buyer takes more.
- SUSPEND: use when the situation is uncertain — for example:
  * Price is below target but not unacceptable (could work if no better offers come)
  * Stock is limited and you're unsure if restocking will happen before Fashion Week ends
  * The deal is borderline — worth holding rather than rejecting or accepting immediately
  SUSPEND means "hold this deal for later decision, don't deduct stock, don't confirm yet."

Return ONLY valid JSON with these keys:
- action: "ACCEPT" or "COUNTER" or "UPSELL" or "SUSPEND"
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


# ─── Voice Command Detection ───

# Keywords that trigger actions via voice instead of button clicks
VOICE_COMMANDS = {
    "confirm": ["confirm", "confirmed", "approve", "approved", "accept", "accepted", "go ahead", "let's do it", "deal", "done deal", "validate"],
    "suspend": ["suspend", "suspended", "hold", "hold on", "put on hold", "wait", "pause", "not sure", "hold that", "keep it"],
}


def detect_voice_command(transcript: str) -> str | None:
    """Check if transcript is a voice command rather than a new deal.
    Returns 'confirm', 'suspend', or None (meaning it's a regular deal transcript).
    Only matches if the transcript is SHORT (< 15 words) — longer utterances are deals."""
    text = transcript.strip().lower()
    words = text.split()

    # Long utterances are always deals, not commands
    if len(words) > 15:
        return None

    for action, keywords in VOICE_COMMANDS.items():
        for kw in keywords:
            if kw in text:
                return action

    return None


# ─── Pipeline Runner ───


def agent_receipt(extracted: dict, strategy: dict, order_id: int) -> str:
    """Generate a formal payment receipt for confirmed orders."""
    system = """You are a luxury fashion finance coordinator for a prestigious Parisian maison.
Generate a formal PAYMENT RECEIPT (not a confirmation email) for a confirmed B2B order.

Rules:
- Format as a structured receipt with clear line items
- Include: Receipt number (use the order ID provided), date, buyer info, item details, unit price, quantity, subtotal, and total
- Add a "Payment Terms: Net 30" line
- Include "Maison AURA — Paris Fashion Week" as the issuing entity
- Keep it professional, clean, and structured — like a Chanel invoice, not a Shopify receipt
- Use plain text formatting with clear sections

Return ONLY the receipt text, no JSON wrapping."""

    from datetime import datetime
    context = f"""ORDER #{order_id}:
Date: {datetime.now().strftime('%d %B %Y')}
Buyer: {extracted.get('buyer', 'Valued Client')}
Store: {extracted.get('store', '')}
Item: {extracted.get('item', 'item')}
Quantity: {strategy.get('suggested_quantity', extracted.get('quantity', 0))} units
Unit Price: EUR {strategy.get('suggested_price', extracted.get('price', 0)):,.2f}
Total: EUR {strategy.get('suggested_quantity', extracted.get('quantity', 0)) * strategy.get('suggested_price', extracted.get('price', 0)):,.2f}"""

    return _call_llm(system, context, json_mode=False)


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
    emoji = {"ACCEPT": "✅", "COUNTER": "⚡", "UPSELL": "📈", "SUSPEND": "⏸️"}.get(action, "⚡")
    sq = strategy.get("suggested_quantity", extracted.get("quantity", "?"))
    sp = strategy.get("suggested_price", extracted.get("price", "?"))
    total = sq * sp if isinstance(sq, (int, float)) and isinstance(sp, (int, float)) else "?"
    await send_log(3, "STRATEGIST",
        f"{emoji} {action} → {sq} units @ €{sp:,} | "
        f"Reason: {strategy.get('reasoning', '?')[:80]}... | Total: €{total:,}" if isinstance(total, (int, float)) else
        f"{emoji} {action} → {sq} units @ €{sp} | Reason: {strategy.get('reasoning', '?')[:80]}...",
        strategy)

    return extracted, inventory_report, strategy
