"""
AURA — Multi-Agent AI Pipeline
Agent 1: Data Extractor (voice -> structured JSON)
Agent 2: Inventory & Margin Checker (JSON -> DB lookup -> report)
Agent 3: Deal Strategist (report -> ACCEPT/COUNTER/UPSELL)
Agent 4: Luxury Copywriter (deal -> haute couture confirmation email)
Intent Classifier: Routes voice input to correct handler
"""

import json
import os
import re
from groq import Groq
from database import find_item_by_name, check_stock, calculate_margin, get_catalog_names, find_item_by_model, get_model_assignments, get_demand_data, get_all_inventory

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
    Includes catalog awareness, number tolerance, model references, and speech transcription error handling."""

    # Get current catalog items to feed the LLM
    try:
        catalog = get_catalog_names()
        catalog_str = ", ".join(catalog)
    except Exception:
        catalog_str = "Obsidian Trench, Ivory Blazer, Noir Midi Dress, Crimson Silk Blouse, Glacial Cashmere Coat, Onyx Leather Jacket, Pearl Evening Gown, Slate Wool Trousers, Rose Gold Mini Bag, Midnight Velvet Suit"

    # Get model assignments for context
    try:
        assignments = get_model_assignments()
        model_context = "\n".join(
            f"  - {a['model_name']} wore: {a['item_name']} ({a['event']})"
            for a in assignments
        ) if assignments else "  No model assignments yet."
    except Exception:
        model_context = "  No model assignments yet."

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

MODEL REFERENCES (buyers may reference items by who wore them):
{model_context}
If the buyer says something like "I want 2 of what Jade Li wore" or "the dress that Jade Li had",
resolve the model reference to the actual item name from the catalog.

CRITICAL RULES FOR VOICE TRANSCRIPTION TOLERANCE:
1. ITEM MATCHING: The speaker may mispronounce or Deepgram may mistranscribe item names.
   Match to the CLOSEST catalog item. Examples:
   - "obsidian french" -> "Obsidian Trench"
   - "ivory blazing" -> "Ivory Blazer"
   - "glacial cashmere" -> "Glacial Cashmere Coat"
   - "midnight velvet" -> "Midnight Velvet Suit"
   - "rose gold bag" -> "Rose Gold Mini Bag"
   - "pearl gown" -> "Pearl Evening Gown"
   - "slate trousers" -> "Slate Wool Trousers"
   - "crimson silk" or "crumsib silk" or "crimsin blouse" -> "Crimson Silk Blouse"
   - "noir midi" or "black midi dress" or "noire midi" -> "Noir Midi Dress"
   Any partial match or phonetic similarity should resolve to the correct catalog item.

2. NUMBER TOLERANCE: Speech-to-text often garbles numbers. Apply common sense:
   - "a hundred and fifty" or "150" or "one fifty" -> 150
   - "twelve hundred" or "1200" -> 1200
   - If a quantity seems unreasonably large (>500 for fashion), it might be a price mistakenly placed
   - If a price seems unreasonably low (<50 for luxury fashion), it might be missing a zero
   - Reasonable quantity range: 1-500 units
   - Reasonable price range: EUR200-EUR5000 per unit for luxury fashion

3. BUYER/STORE: Names may be mistranscribed. Use your best interpretation.
   Common stores: Harrods, Selfridges, Galeries Lafayette, Le Bon Marche, Bergdorf Goodman,
   Neiman Marcus, Saks Fifth Avenue, Barneys, Harvey Nichols, Printemps.

4. EMAIL: If the buyer mentions an email address, extract it exactly.
   Email addresses in speech may sound like "sophie at harrods dot com" -> "sophie@harrods.com"

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
    """Decide: ACCEPT / COUNTER-OFFER / UPSELL / ALTERNATIVE / SUSPEND based on inventory report + demand."""

    # Get demand data for this item
    demand_context = ""
    item_id = inventory_report.get("item_id")
    if item_id:
        try:
            demand = get_demand_data(item_id)
            demand_context = f"""
DEMAND DATA:
- Demand level: {demand['demand_level']}
- Orders for this item: {demand['order_count']} (total {demand['total_qty_ordered']} units ordered)
- Current stock: {demand['current_stock']} units"""
        except Exception:
            demand_context = "\nDEMAND DATA: Not available."

    # Get full catalog for ALTERNATIVE suggestions
    catalog_context = ""
    try:
        all_items = get_all_inventory()
        catalog_lines = []
        for it in all_items:
            catalog_lines.append(f"  - {it['item_name']} ({it['collection']}, {it['color']}) — stock: {it['stock_qty']}, wholesale: EUR{it['wholesale_price_eur']}")
        catalog_context = "\nFULL CATALOG (for alternatives):\n" + "\n".join(catalog_lines)
    except Exception:
        catalog_context = ""

    system = f"""You are a luxury fashion deal strategist for Paris Fashion Week B2B negotiations.
Based on the inventory report and demand data, decide one of five actions:
- ACCEPT: stock sufficient and margin healthy. Approve the deal as-is.
- COUNTER: stock insufficient OR margin too low. Suggest adjusted quantity and/or price.
- UPSELL: stock is very high (>2x requested) and margin healthy. Suggest the buyer takes more.
- ALTERNATIVE: stock is INSUFFICIENT for the requested item. Suggest a SIMILAR item from the catalog that has enough stock. Include a small discount (5-15%) as a goodwill gesture. Pick the most similar item by style/category/price range.
- SUSPEND: use when the situation is uncertain — for example:
  * Price is below target but not unacceptable
  * Stock is limited and you're unsure
  * The deal is borderline

DEMAND-BASED PRICING RULES:
- If demand is HIGH: be LESS generous with discounts, hold firm on price, counter-offer with higher prices. The item is in demand — buyers will pay more.
- If demand is MEDIUM: standard negotiation — normal flexibility.
- If demand is LOW: be MORE generous, offer better prices, upsell more aggressively to move stock.

WHEN TO USE ALTERNATIVE:
- ONLY when stock_sufficient is false AND the requested quantity cannot be reasonably reduced
- Pick the most similar item: same collection > same color > similar price range > similar style
- Offer a 5-15% discount on the alternative item as compensation
- If the buyer only needs slightly fewer units and stock can cover it, prefer COUNTER over ALTERNATIVE

Return ONLY valid JSON with these keys:
- action: "ACCEPT" or "COUNTER" or "UPSELL" or "ALTERNATIVE" or "SUSPEND"
- reasoning: 2-3 sentence explanation
- suggested_quantity: the recommended quantity (same as original if ACCEPT)
- suggested_price: the recommended price per unit (same as original if ACCEPT)
- original_quantity: the originally requested quantity
- original_price: the originally requested price
- alternative_item: (ONLY for ALTERNATIVE action) the name of the suggested alternative item from the catalog
- alternative_price: (ONLY for ALTERNATIVE action) the discounted price for the alternative
- discount_pct: (ONLY for ALTERNATIVE action) the discount percentage offered
- voice_summary: a concise 1-2 sentence summary to be spoken aloud to the sales rep. Natural, conversational tone. If ALTERNATIVE, mention the alternative item name and discount."""

    context = f"""DEAL REQUEST:
Buyer: {extracted.get('buyer', 'Unknown')} from {extracted.get('store', 'Unknown')}
Item: {extracted.get('item', 'Unknown')}
Quantity: {extracted.get('quantity', 0)} units
Price: EUR{extracted.get('price', 0)} per unit

INVENTORY REPORT:
{json.dumps(inventory_report, indent=2)}
{demand_context}
{catalog_context}"""

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


# ─── Intent Classification (Voice Router) ───

# Keywords that trigger actions via voice instead of button clicks
VOICE_COMMANDS = {
    "confirm": ["confirm", "confirmed", "approve", "approved", "accept", "accepted", "go ahead",
                 "let's do it", "deal", "done deal", "validate", "yes confirm", "i confirm",
                 "that's good", "we'll take it", "let's go", "alright confirm"],
    "suspend": ["suspend", "suspended", "hold", "hold on", "put on hold", "wait", "pause",
                "not sure", "hold that", "keep it", "let me think", "give me a moment",
                "i'll get back to you", "hold off"],
}

# Patterns for stock addition (voice)
STOCK_ADD_PATTERNS = [
    r"(?:we |i )?\breceived?\b.*?\b(\d+)\b.*\bnew\b",
    r"(?:we |i )?\bgot\b.*?\b(\d+)\b.*\bnew\b",
    r"\badd\b.*?\b(\d+)\b.*\bstock\b",
    r"\brestock\b.*?\b(\d+)\b",
    r"\b(\d+)\b.*\bnew\b.*\b(?:units?|pieces?|items?)\b",
    r"(?:we |i )?\breceived?\b.*?\b(\d+)\b",
]

# Patterns for email provision
EMAIL_PATTERN = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')

# Patterns for model references
MODEL_REFERENCE_PATTERNS = [
    r"(?:what|the\s+(?:dress|item|piece|coat|suit|gown|jacket|blazer|blouse|trousers|bag))\s+(?:that\s+)?(\w+(?:\s+\w+)?)\s+(?:wore|had|was wearing|modeled|walked in|carried)",
    r"(\w+(?:\s+\w+)?)\s+(?:wore|modeled|was wearing|walked in|had on)",
    r"(?:same|like)\s+(\w+(?:\s+\w+)?)\s*(?:'s|wore|had)",
    r"(?:can i|i want|i'd like|give me).*?(?:what|that|the one)\s+(\w+(?:\s+\w+)?)\s+(?:wore|had|modeled)",
]


def classify_intent(transcript: str, has_active_deal: bool = False) -> dict:
    """Classify a voice transcript into one of several intents.
    Returns dict with 'intent' key and relevant extracted data.

    Intents:
    - 'confirm': User wants to confirm the active deal
    - 'suspend': User wants to suspend/hold the active deal
    - 'email': User is providing an email address
    - 'stock_add': User is reporting stock received
    - 'model_query': User is asking about what a model wore
    - 'model_assign': User is telling us a model wore something
    - 'catalog_query': User wants to browse a designer/model's catalog
    - 'deal': Regular deal transcript (default)
    """
    text = transcript.strip().lower()
    words = text.split()

    # 1. Email detection — very specific, check first
    email_match = EMAIL_PATTERN.search(transcript)
    if email_match and len(words) < 25:
        return {"intent": "email", "email": email_match.group(0), "transcript": transcript}

    # 2. Short utterances → check voice commands (confirm/suspend)
    if len(words) <= 15:
        for action, keywords in VOICE_COMMANDS.items():
            for kw in keywords:
                if kw in text:
                    if has_active_deal:
                        return {"intent": action, "transcript": transcript}
                    else:
                        # No active deal — might still be a voice command for future use
                        # but don't trigger it without context
                        break

    # 3. Catalog query detection — "show me X's catalog", "display X collection", "what does X have"
    catalog_patterns = [
        r"(?:show me|display|list|what does|what do|browse|see)\s+(?:the\s+)?(?:catalog|collection|catalogue|items?|pieces?)\s+(?:of|from|by|for)\s+(\w+(?:\s+\w+)?)",
        r"(?:show me|display|list|browse|see)\s+(\w+(?:\s+\w+)?)\s*(?:'s|s)?\s+(?:catalog|collection|catalogue|items?|pieces?)",
        r"(?:what does|what do)\s+(\w+(?:\s+\w+)?)\s+have",
        r"(?:show me|display|catalog|collection)\s+(?:for|of|by)\s+(\w+(?:\s+\w+)?)",
        r"(\w+(?:\s+\w+)?)\s*(?:'s|s)?\s+(?:catalog|collection|catalogue)",
    ]
    for pattern in catalog_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            designer_name = match.group(1).strip()
            return {"intent": "catalog_query", "designer_name": designer_name, "transcript": transcript}

    # 4. Stock addition detection
    for pattern in STOCK_ADD_PATTERNS:
        match = re.search(pattern, text)
        if match:
            qty = int(match.group(1))
            # Extract item name from the rest of the sentence
            return {"intent": "stock_add", "quantity": qty, "transcript": transcript}

    # 5. Model reference detection (query: "I want what Jade Li wore")
    for pattern in MODEL_REFERENCE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            model_name = match.group(1).strip()
            # Check if it's a query ("I want what X wore") or assignment ("X wore the Y")
            if any(kw in text for kw in ["i want", "can i", "i'd like", "give me", "same as", "like the"]):
                return {"intent": "model_query", "model_name": model_name, "transcript": transcript}
            elif any(kw in text for kw in ["wore", "was wearing", "modeled", "walked in", "had on"]):
                return {"intent": "model_assign", "model_name": model_name, "transcript": transcript}

    # 6. Default — it's a deal transcript
    return {"intent": "deal", "transcript": transcript}


def detect_voice_command(transcript: str) -> str | None:
    """Legacy wrapper — check if transcript is a voice command.
    Returns 'confirm', 'suspend', or None."""
    result = classify_intent(transcript, has_active_deal=True)
    if result["intent"] in ("confirm", "suspend"):
        return result["intent"]
    return None


# ─── Agent: Stock Addition Extractor ───

def agent_extract_stock_add(transcript: str) -> dict:
    """Extract item name and quantity from a stock addition voice command."""
    try:
        catalog = get_catalog_names()
        catalog_str = ", ".join(catalog)
    except Exception:
        catalog_str = "Obsidian Trench, Ivory Blazer, Noir Midi Dress, Crimson Silk Blouse, Glacial Cashmere Coat, Onyx Leather Jacket, Pearl Evening Gown, Slate Wool Trousers, Rose Gold Mini Bag, Midnight Velvet Suit"

    system = f"""You are a data extraction agent for a luxury fashion inventory system.
The user is reporting that new stock has arrived. Extract:
- item: the fashion item name — MUST match one from our catalog
- quantity: number of units received (integer)

CATALOG ITEMS (match the closest one):
{catalog_str}

Apply the same fuzzy matching rules as for deal extraction — mispronunciations and speech-to-text errors are expected.

Return ONLY valid JSON with keys: item, quantity"""

    raw = _call_llm(system, transcript, json_mode=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "Failed to parse stock addition", "raw": raw}


# ─── Agent: Model Assignment Extractor ───

def agent_extract_model_assign(transcript: str) -> dict:
    """Extract model name and item from a model assignment voice command."""
    try:
        catalog = get_catalog_names()
        catalog_str = ", ".join(catalog)
    except Exception:
        catalog_str = "Obsidian Trench, Ivory Blazer, Noir Midi Dress, Crimson Silk Blouse, Glacial Cashmere Coat, Onyx Leather Jacket, Pearl Evening Gown, Slate Wool Trousers, Rose Gold Mini Bag, Midnight Velvet Suit"

    # Get existing model assignments for context
    try:
        assignments = get_model_assignments()
        models_str = ", ".join(set(a["model_name"] for a in assignments)) if assignments else "No models assigned yet"
    except Exception:
        models_str = "No models assigned yet"

    system = f"""You are a data extraction agent for a luxury fashion showroom.
The user is telling you about a model who wore a specific item (e.g., during a runway show, fitting, or event).
Extract:
- model_name: the model's full name
- item: the fashion item name — MUST match one from our catalog
- event: the event context (e.g., "runway show", "pre-show fitting", "gala evening")

CATALOG ITEMS: {catalog_str}
KNOWN MODELS: {models_str}

Return ONLY valid JSON with keys: model_name, item, event"""

    raw = _call_llm(system, transcript, json_mode=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "Failed to parse model assignment", "raw": raw}


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
    emoji = {"ACCEPT": "✅", "COUNTER": "⚡", "UPSELL": "📈", "SUSPEND": "⏸️", "ALTERNATIVE": "🔄"}.get(action, "⚡")
    sq = strategy.get("suggested_quantity", extracted.get("quantity", "?"))
    sp = strategy.get("suggested_price", extracted.get("price", "?"))
    total = sq * sp if isinstance(sq, (int, float)) and isinstance(sp, (int, float)) else "?"
    await send_log(3, "STRATEGIST",
        f"{emoji} {action} → {sq} units @ €{sp:,} | "
        f"Reason: {strategy.get('reasoning', '?')[:80]}... | Total: €{total:,}" if isinstance(total, (int, float)) else
        f"{emoji} {action} → {sq} units @ €{sp} | Reason: {strategy.get('reasoning', '?')[:80]}...",
        strategy)

    return extracted, inventory_report, strategy
