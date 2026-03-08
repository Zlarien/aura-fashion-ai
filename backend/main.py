"""
AURA — FastAPI Backend + WebSocket Hub
Handles: mic audio streaming, agent pipeline, demo mode, TTS, CORS
"""

import os
import json
import asyncio
import base64
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Import our modules
from database import (
    init_db, get_all_inventory, get_confirmed_orders, get_suspended_orders,
    create_order, confirm_order, suspend_order, reset_inventory, add_stock,
    deduct_stock_external, assign_model, find_item_by_model, get_model_assignments,
    find_item_by_name, get_demand_data,
)
from agents import (
    agent_extract, agent_inventory_check, agent_strategist, agent_copywriter,
    agent_receipt, run_pipeline, detect_voice_command, classify_intent,
    agent_extract_stock_add, agent_extract_model_assign,
)
from deepgram_client import DeepgramStreamer
from cartesia_client import synthesize_speech
from demo_data import (
    DEMO_TRANSCRIPT, DEMO_AGENT_LOGS, DEMO_AGENT1_RESULT,
    DEMO_AGENT2_RESULT, DEMO_AGENT3_RESULT, DEMO_AGENT4_EMAIL, DEMO_TTS_TEXT,
)

# ─── App Setup ───

app = FastAPI(title="AURA — AI Sales Intelligence")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Multi-Session State ───
connected_clients: dict = {}  # websocket -> {"rep_name": str, "session": dict}


async def broadcast_to_all(data: dict, exclude=None):
    """Send a JSON message to ALL connected clients, optionally excluding one."""
    for ws_client, info in list(connected_clients.items()):
        if ws_client == exclude:
            continue
        try:
            await ws_client.send_text(json.dumps(data))
        except Exception:
            pass


async def broadcast_inventory():
    """Push current inventory + orders + suspended to ALL connected clients."""
    items = get_all_inventory()
    orders = get_confirmed_orders()
    suspended = get_suspended_orders()
    total = sum(o["agreed_price_eur"] * o["quantity"] for o in orders)
    await broadcast_to_all({"type": "inventory", "items": items})
    await broadcast_to_all({"type": "orders", "orders": orders, "total_revenue": total})
    await broadcast_to_all({"type": "suspended", "orders": suspended})


async def _tts_task(send_fn, text: str):
    """Background TTS: synthesize + send audio without blocking caller."""
    try:
        audio_bytes = await synthesize_speech(text)
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        await send_fn({"type": "tts_audio", "audio": audio_b64})
    except Exception as e:
        print(f"[TTS Background] {e}")


def fire_tts(send_fn, text: str):
    """Fire-and-forget TTS — returns immediately, audio arrives async."""
    asyncio.create_task(_tts_task(send_fn, text))


# Serve frontend
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/inventory")
async def api_inventory():
    return get_all_inventory()


@app.get("/api/orders")
async def api_orders():
    orders = get_confirmed_orders()
    suspended = get_suspended_orders()
    total = sum(o["agreed_price_eur"] * o["quantity"] for o in orders)
    return {"orders": orders, "suspended": suspended, "total_revenue": total}


# ─── WebSocket Handler ───

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Session state
    session = {
        "extracted": None,
        "inventory_report": None,
        "strategy": None,
        "order_id": None,
        "deepgram": None,
        "demo_mode": False,
    }

    # Register this client for multi-session broadcasting
    rep_name = "Rep"
    connected_clients[websocket] = {"rep_name": rep_name, "session": session}
    # Notify others that a new rep connected
    await broadcast_to_all({"type": "rep_connected", "rep_name": rep_name, "total_reps": len(connected_clients)}, exclude=websocket)

    async def send_json(data: dict):
        """Safe JSON send."""
        try:
            await websocket.send_text(json.dumps(data))
        except Exception:
            pass

    async def send_inventory_update():
        """Push current inventory + orders + suspended to frontend."""
        items = get_all_inventory()
        orders = get_confirmed_orders()
        suspended = get_suspended_orders()
        total = sum(o["agreed_price_eur"] * o["quantity"] for o in orders)
        await send_json({"type": "inventory", "items": items})
        await send_json({"type": "orders", "orders": orders, "total_revenue": total})
        await send_json({"type": "suspended", "orders": suspended})

    # Send initial inventory on connect
    await send_inventory_update()

    try:
        while True:
            message = await websocket.receive()

            # Binary data = audio from mic
            if "bytes" in message:
                audio_data = message["bytes"]
                if session["deepgram"]:
                    await session["deepgram"].send_audio(audio_data)
                continue

            # Text data = JSON command
            if "text" in message:
                try:
                    data = json.loads(message["text"])
                except json.JSONDecodeError:
                    continue

                msg_type = data.get("type", "")

                # ─── Start Recording ───
                if msg_type == "start_recording":
                    async def on_transcript(transcript: str, is_final: bool):
                        await send_json({
                            "type": "transcript",
                            "text": transcript,
                            "is_final": is_final,
                        })
                        if is_final and transcript.strip():
                            has_active = bool(session.get("extracted"))
                            intent = classify_intent(transcript, has_active_deal=has_active)
                            await handle_intent(intent, session, send_json, broadcast_inventory, websocket)

                    try:
                        streamer = DeepgramStreamer(on_transcript)
                        await streamer.start()
                        session["deepgram"] = streamer
                        await send_json({"type": "recording_started"})
                    except Exception as e:
                        await send_json({"type": "error", "message": f"Deepgram error: {str(e)}"})

                # ─── Stop Recording ───
                elif msg_type == "stop_recording":
                    if session["deepgram"]:
                        await session["deepgram"].stop()
                        session["deepgram"] = None
                    await send_json({"type": "recording_stopped"})

                # ─── Demo Mode ───
                elif msg_type == "demo":
                    await handle_demo(session, send_json, broadcast_inventory)

                # ─── Confirm Order ───
                elif msg_type == "confirm":
                    # Capture deal info before confirm (session gets reset inside)
                    deal_item = session.get("extracted", {}).get("item", "item") if session.get("extracted") else "item"
                    deal_qty = session.get("strategy", {}).get("suggested_quantity", 0) if session.get("strategy") else 0
                    deal_buyer = session.get("extracted", {}).get("buyer", "buyer") if session.get("extracted") else "buyer"

                    await handle_confirm(session, send_json, broadcast_inventory)

                    # Cross-session notification
                    rep_name = connected_clients.get(websocket, {}).get("rep_name", "Rep")
                    await broadcast_to_all({
                        "type": "colleague_deal",
                        "action": "confirmed",
                        "rep_name": rep_name,
                        "item": deal_item,
                        "quantity": deal_qty,
                        "buyer": deal_buyer,
                    }, exclude=websocket)

                # ─── Suspend Order ───
                elif msg_type == "suspend":
                    # Capture deal info before suspend (session gets reset inside)
                    deal_item = session.get("extracted", {}).get("item", "item") if session.get("extracted") else "item"
                    deal_buyer = session.get("extracted", {}).get("buyer", "buyer") if session.get("extracted") else "buyer"

                    await handle_suspend(session, send_json, broadcast_inventory)

                    # Cross-session notification
                    rep_name = connected_clients.get(websocket, {}).get("rep_name", "Rep")
                    await broadcast_to_all({
                        "type": "colleague_deal",
                        "action": "suspended",
                        "rep_name": rep_name,
                        "item": deal_item,
                        "buyer": deal_buyer,
                    }, exclude=websocket)

                # ─── Inject Transcript (test mode, bypass Deepgram) ───
                elif msg_type == "inject_transcript":
                    transcript = data.get("text", "")
                    if transcript:
                        await send_json({"type": "transcript", "text": transcript, "is_final": True})
                        has_active = bool(session.get("extracted"))
                        intent = classify_intent(transcript, has_active_deal=has_active)
                        await handle_intent(intent, session, send_json, broadcast_inventory, websocket)

                # ─── Update Buyer Info (editable fields) ───
                elif msg_type == "update_buyer_info":
                    if session.get("extracted"):
                        if data.get("buyer"):
                            session["extracted"]["buyer"] = data["buyer"]
                        if data.get("store"):
                            session["extracted"]["store"] = data["store"]
                        if data.get("email"):
                            session["extracted"]["email"] = data["email"]
                        if data.get("phone"):
                            session["extracted"]["phone"] = data["phone"]
                        if data.get("address"):
                            session["extracted"]["address"] = data["address"]

                # ─── Get Inventory ───
                elif msg_type == "get_inventory":
                    await send_inventory_update()

                # ─── Set Rep Name (multi-session) ───
                elif msg_type == "set_rep_name":
                    new_name = data.get("name", "").strip()
                    if new_name:
                        old_name = connected_clients.get(websocket, {}).get("rep_name", "Rep")
                        if websocket in connected_clients:
                            connected_clients[websocket]["rep_name"] = new_name
                        await broadcast_to_all({"type": "rep_connected", "rep_name": new_name, "total_reps": len(connected_clients)}, exclude=websocket)

                # ─── Reset Inventory ───
                elif msg_type == "reset":
                    reset_inventory()
                    await broadcast_to_all({"type": "agent_log", "agent": 0, "label": "AURA",
                        "content": "Inventory reset to original stock levels. All orders cleared.", "data": {}})
                    await broadcast_to_all({"type": "inventory_reset"})
                    await broadcast_inventory()
                    # Reset local session
                    session["extracted"] = None
                    session["inventory_report"] = None
                    session["strategy"] = None
                    session["order_id"] = None
                    session["demo_mode"] = False

                # ─── Colleague Stock Deduction Simulation ───
                elif msg_type == "colleague_deduct":
                    item_name = data.get("item", "Crimson Silk Blouse")
                    qty = data.get("quantity", 30)
                    colleague = data.get("colleague", "Marc (Showroom B)")
                    result = deduct_stock_external(item_name, qty, colleague)
                    if result:
                        await send_json({"type": "agent_log", "agent": 0, "label": "ALERT",
                            "content": f"Stock alert: {colleague} just sold {qty}x {result['item_name']}. Remaining: {result['stock_qty']}",
                            "data": {"colleague": colleague, "item": result["item_name"], "deducted": qty, "remaining": result["stock_qty"]}})
                        await send_json({"type": "stock_alert", "colleague": colleague,
                            "item_name": result["item_name"], "quantity_deducted": qty, "remaining_stock": result["stock_qty"]})
                        await broadcast_inventory()
                        # Cross-session notification
                        await broadcast_to_all({
                            "type": "colleague_deal",
                            "action": "deducted",
                            "rep_name": connected_clients.get(websocket, {}).get("rep_name", "Rep"),
                            "item": result["item_name"],
                            "quantity": qty,
                            "buyer": colleague,
                        }, exclude=websocket)
                        # TTS alert (non-blocking)
                        fire_tts(send_json, f"Heads up: {colleague} just sold {qty} units of {result['item_name']}. Only {result['stock_qty']} left.")

                # ─── Colleague Competing Order Simulation ───
                elif msg_type == "colleague_order":
                    # Simulate another rep putting a hold on a similar item
                    item_name = data.get("item", "")
                    qty = data.get("quantity", 0)
                    buyer = data.get("buyer", "Unknown Buyer")
                    colleague = data.get("colleague", "Elise (Showroom C)")

                    # If no item provided, use current deal's item
                    if not item_name and session.get("extracted"):
                        item_name = session["extracted"].get("item", "Crimson Silk Blouse")
                    elif not item_name:
                        item_name = "Crimson Silk Blouse"
                    if not qty:
                        qty = 20

                    # Create the competing suspended order
                    item = find_item_by_name(item_name)
                    if item:
                        order_id = create_order(buyer, f"{colleague}'s client", item["id"], qty, 0)
                        suspend_order(order_id)
                        await send_json({"type": "agent_log", "agent": 0, "label": "ALERT",
                            "content": f"Competing order: {colleague} has a pending deal for {qty}x {item['item_name']} from {buyer}. Stock pressure!",
                            "data": {"colleague": colleague, "item": item["item_name"], "quantity": qty, "buyer": buyer}})
                        await send_json({"type": "competing_order", "colleague": colleague,
                            "item_name": item["item_name"], "quantity": qty, "buyer": buyer})
                        await broadcast_inventory()
                        # Cross-session notification
                        await broadcast_to_all({
                            "type": "colleague_deal",
                            "action": "competing_order",
                            "rep_name": connected_clients.get(websocket, {}).get("rep_name", "Rep"),
                            "item": item["item_name"],
                            "quantity": qty,
                            "buyer": buyer,
                        }, exclude=websocket)
                        # TTS alert (non-blocking)
                        fire_tts(send_json, f"Alert: {colleague} also has a pending order for {qty} units of {item['item_name']}. You might want to close this deal quickly.")

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WS Error] {e}")
    finally:
        if session["deepgram"]:
            await session["deepgram"].stop()
        # Deregister client and notify others
        rep_info = connected_clients.pop(websocket, {})
        rep_name = rep_info.get("rep_name", "Rep")
        await broadcast_to_all({"type": "rep_disconnected", "rep_name": rep_name, "total_reps": len(connected_clients)})


# ─── Intent Router ───

async def handle_intent(intent: dict, session: dict, send_json, send_inventory_update, ws_client=None):
    """Route classified intent to appropriate handler."""
    intent_type = intent.get("intent", "deal")
    transcript = intent.get("transcript", "")

    if intent_type == "confirm" and session.get("extracted"):
        # Capture deal info before confirm (session gets reset inside)
        deal_item = session.get("extracted", {}).get("item", "item") if session.get("extracted") else "item"
        deal_qty = session.get("strategy", {}).get("suggested_quantity", 0) if session.get("strategy") else 0
        deal_buyer = session.get("extracted", {}).get("buyer", "buyer") if session.get("extracted") else "buyer"

        await send_json({"type": "voice_command", "action": "confirm"})
        await handle_confirm(session, send_json, send_inventory_update)

        # Cross-session notification (voice-triggered)
        if ws_client:
            rep_name = connected_clients.get(ws_client, {}).get("rep_name", "Rep")
            await broadcast_to_all({
                "type": "colleague_deal",
                "action": "confirmed",
                "rep_name": rep_name,
                "item": deal_item,
                "quantity": deal_qty,
                "buyer": deal_buyer,
            }, exclude=ws_client)

    elif intent_type == "suspend" and session.get("extracted"):
        # Capture deal info before suspend
        deal_item = session.get("extracted", {}).get("item", "item") if session.get("extracted") else "item"
        deal_buyer = session.get("extracted", {}).get("buyer", "buyer") if session.get("extracted") else "buyer"

        await send_json({"type": "voice_command", "action": "suspend"})
        await handle_suspend(session, send_json, send_inventory_update)

        # Cross-session notification (voice-triggered)
        if ws_client:
            rep_name = connected_clients.get(ws_client, {}).get("rep_name", "Rep")
            await broadcast_to_all({
                "type": "colleague_deal",
                "action": "suspended",
                "rep_name": rep_name,
                "item": deal_item,
                "buyer": deal_buyer,
            }, exclude=ws_client)

    elif intent_type == "confirm" or intent_type == "suspend":
        # Voice command but no active deal
        await send_json({"type": "agent_log", "agent": 0, "label": "AURA",
            "content": f"No active deal to {intent_type}. Speak a deal first.", "data": {}})

    elif intent_type == "email":
        await handle_email_intent(intent, session, send_json)

    elif intent_type == "stock_add":
        await handle_stock_add(intent, session, send_json, send_inventory_update)

    elif intent_type == "model_query":
        await handle_model_query(intent, session, send_json, send_inventory_update)

    elif intent_type == "model_assign":
        await handle_model_assign(intent, session, send_json, send_inventory_update)

    elif intent_type == "catalog_query":
        await handle_catalog_query(intent, session, send_json, send_inventory_update)

    else:
        # Default: regular deal transcript
        await handle_pipeline(transcript, session, send_json, send_inventory_update)


# ─── Email Intent Handler ───

async def handle_email_intent(intent: dict, session: dict, send_json):
    """Handle email provided by voice -- attach to active session if exists."""
    email = intent.get("email", "")
    if session.get("extracted"):
        session["extracted"]["email"] = email
        await send_json({"type": "agent_log", "agent": 1, "label": "EXTRACTOR",
            "content": f"Email captured by voice: {email}", "data": {"email": email}})
        await send_json({"type": "email_captured", "email": email})
        # TTS confirmation (non-blocking)
        fire_tts(send_json, f"Got it, I've noted the email {email}.")
    else:
        await send_json({"type": "agent_log", "agent": 0, "label": "AURA",
            "content": f"Email noted: {email} -- will attach to next deal.", "data": {"email": email}})
        session["pending_email"] = email


# ─── Stock Add Handler ───

async def handle_stock_add(intent: dict, session: dict, send_json, send_inventory_update):
    """Handle voice stock addition: 'we received 50 new Crimson Silk Blouse'."""
    transcript = intent.get("transcript", "")
    await send_json({"type": "agent_log", "agent": 0, "label": "AURA",
        "content": "Detected stock addition request -- extracting details...", "data": {}})

    try:
        extracted = agent_extract_stock_add(transcript)
        item_name = extracted.get("item", "")
        quantity = extracted.get("quantity", 0)

        if not item_name or not quantity:
            await send_json({"type": "agent_log", "agent": 0, "label": "AURA",
                "content": "Could not extract item or quantity from stock addition request.", "data": extracted})
            return

        result = add_stock(item_name, quantity)
        if result:
            await send_json({"type": "agent_log", "agent": 0, "label": "INVENTORY",
                "content": f"Stock added: +{quantity} {result['item_name']} (now {result['stock_qty']} total)",
                "data": {"item": result["item_name"], "added": quantity, "new_total": result["stock_qty"]}})
            await send_json({"type": "stock_added", "item_name": result["item_name"],
                "quantity_added": quantity, "new_stock": result["stock_qty"]})
            await send_inventory_update()
            # TTS feedback (non-blocking)
            fire_tts(send_json, f"Done. Added {quantity} units of {result['item_name']}. New total: {result['stock_qty']}.")
        else:
            await send_json({"type": "agent_log", "agent": 0, "label": "AURA",
                "content": f"Could not find item '{item_name}' in inventory to add stock.", "data": {}})
    except Exception as e:
        await send_json({"type": "error", "message": f"Stock add error: {str(e)}"})


# ─── Model Query Handler ───

async def handle_model_query(intent: dict, session: dict, send_json, send_inventory_update):
    """Handle 'I want what Jade Li wore' -- resolve model to item and run deal pipeline."""
    model_name = intent.get("model_name", "")
    transcript = intent.get("transcript", "")

    items = find_item_by_model(model_name)
    if items:
        item = items[0]  # Take the first match
        await send_json({"type": "agent_log", "agent": 0, "label": "AURA",
            "content": f"Model reference resolved: {item['model_name']} wore {item['item_name']} ({item['event']})",
            "data": {"model": item["model_name"], "item": item["item_name"], "event": item["event"]}})
        await send_json({"type": "model_resolved", "model_name": item["model_name"],
            "item_name": item["item_name"], "event": item["event"]})
        # Run the pipeline with the original transcript -- Agent 1 already has model context
        await handle_pipeline(transcript, session, send_json, send_inventory_update)
    else:
        await send_json({"type": "agent_log", "agent": 0, "label": "AURA",
            "content": f"No items found for model '{model_name}'. Check model name and try again.", "data": {}})
        fire_tts(send_json, f"Sorry, I don't have any items associated with {model_name}.")


# ─── Model Assign Handler ───

async def handle_model_assign(intent: dict, session: dict, send_json, send_inventory_update):
    """Handle 'Jade Li wore the Noir Midi Dress' -- assign model to item."""
    transcript = intent.get("transcript", "")

    try:
        extracted = agent_extract_model_assign(transcript)
        model_name = extracted.get("model_name", "")
        item_name = extracted.get("item", "")
        event = extracted.get("event", "runway show")

        if not model_name or not item_name:
            await send_json({"type": "agent_log", "agent": 0, "label": "AURA",
                "content": "Could not extract model or item from assignment request.", "data": extracted})
            return

        result = assign_model(model_name, item_name, event)
        if result:
            await send_json({"type": "agent_log", "agent": 0, "label": "AURA",
                "content": f"Model assigned: {result['model_name']} -> {result['item_name']} ({result['event']})",
                "data": result})
            await send_json({"type": "model_assigned", "model_name": result["model_name"],
                "item_name": result["item_name"], "event": result["event"]})
            fire_tts(send_json, f"Noted. {result['model_name']} wore the {result['item_name']} at the {result['event']}.")
        else:
            await send_json({"type": "agent_log", "agent": 0, "label": "AURA",
                "content": f"Could not find item '{item_name}' in catalog for model assignment.", "data": {}})
    except Exception as e:
        await send_json({"type": "error", "message": f"Model assignment error: {str(e)}"})


# ─── Catalog Query Handler ───

async def handle_catalog_query(intent: dict, session: dict, send_json, send_inventory_update):
    """Handle 'show me Jade Li's catalog' — display items assigned to a designer/model."""
    designer_name = intent.get("designer_name", "")
    transcript = intent.get("transcript", "")

    await send_json({"type": "agent_log", "agent": 0, "label": "AURA",
        "content": f"Catalog query: looking up items for '{designer_name}'...", "data": {}})

    # Find items by model/designer name
    items = find_item_by_model(designer_name)
    if items:
        # Build catalog display data
        catalog_items = []
        for item in items:
            demand = get_demand_data(item["id"])
            catalog_items.append({
                "item_name": item["item_name"],
                "collection": item["collection"],
                "color": item["color"],
                "stock_qty": item["stock_qty"],
                "wholesale_price_eur": item["wholesale_price_eur"],
                "model_name": item["model_name"],
                "event": item["event"],
                "demand_level": demand["demand_level"],
            })

        designer_display = items[0]["model_name"]  # Use the DB-stored name (proper casing)

        await send_json({"type": "agent_log", "agent": 0, "label": "CATALOG",
            "content": f"Found {len(catalog_items)} item(s) for {designer_display}",
            "data": {"designer": designer_display, "items": catalog_items}})

        await send_json({
            "type": "catalog_display",
            "designer": designer_display,
            "items": catalog_items,
        })

        # TTS readout (non-blocking)
        if len(catalog_items) == 1:
            it = catalog_items[0]
            tts_text = f"{designer_display} wore the {it['item_name']} from the {it['collection']} collection at the {it['event']}. We have {it['stock_qty']} units in stock."
        else:
            names = ", ".join(it["item_name"] for it in catalog_items)
            tts_text = f"{designer_display} has {len(catalog_items)} items: {names}."
        fire_tts(send_json, tts_text)
    else:
        await send_json({"type": "agent_log", "agent": 0, "label": "AURA",
            "content": f"No catalog items found for '{designer_name}'. They may not have any assigned pieces.", "data": {}})
        fire_tts(send_json, f"Sorry, I couldn't find any items in the catalog for {designer_name}.")


# ─── Pipeline Handler (Live Mode) ───

async def handle_pipeline(transcript: str, session: dict, send_json, send_inventory_update):
    """Run the 4-agent pipeline on a transcript."""

    async def send_log(agent_num: int, label: str, content: str, data: dict):
        await send_json({
            "type": "agent_log",
            "agent": agent_num,
            "label": label,
            "content": content,
            "data": data,
        })

    try:
        extracted, inventory_report, strategy = await run_pipeline(transcript, send_log)

        # Attach pending email from voice if available
        if session.get("pending_email") and not extracted.get("email"):
            extracted["email"] = session.pop("pending_email")

        session["extracted"] = extracted
        session["inventory_report"] = inventory_report
        session["strategy"] = strategy

        # Create pending order if item was found
        if inventory_report.get("item_found"):
            # ALTERNATIVE: resolve the alternative item to get correct item_id
            action = strategy.get("action", "")
            if action == "ALTERNATIVE" and strategy.get("alternative_item"):
                alt_item = find_item_by_name(strategy["alternative_item"])
                if alt_item:
                    order_item_id = alt_item["id"]
                    # Update inventory report context for frontend display
                    inventory_report["alternative_item_id"] = alt_item["id"]
                    inventory_report["alternative_item_name"] = alt_item["item_name"]
                    inventory_report["alternative_collection"] = alt_item["collection"]
                    inventory_report["alternative_stock"] = alt_item["stock_qty"]
                    session["inventory_report"] = inventory_report
                else:
                    # Fallback to original item if alt not found
                    order_item_id = inventory_report["item_id"]
            else:
                order_item_id = inventory_report["item_id"]

            order_id = create_order(
                buyer_name=extracted.get("buyer", "Unknown"),
                store_name=extracted.get("store", "Unknown"),
                item_id=order_item_id,
                quantity=strategy.get("suggested_quantity", extracted.get("quantity", 0)),
                agreed_price=strategy.get("suggested_price", extracted.get("price", 0)),
            )
            session["order_id"] = order_id

        # Send recommendation to frontend
        await send_json({
            "type": "recommendation",
            "action": strategy.get("action", "COUNTER"),
            "data": strategy,
            "extracted": extracted,
            "inventory": inventory_report,
        })

        # Generate TTS for voice summary (non-blocking)
        voice_text = strategy.get("voice_summary", "Processing complete.")
        # If no email was provided by the buyer, append a gentle ask
        buyer_email = extracted.get("email")
        if not buyer_email:
            voice_text += " By the way, do you have an email for the buyer? It's optional but useful for the confirmation."
        fire_tts(send_json, voice_text)

    except Exception as e:
        await send_json({"type": "error", "message": f"Pipeline error: {str(e)}"})


# ─── Demo Mode Handler ───

async def handle_demo(session: dict, send_json, send_inventory_update):
    """Run demo mode with pre-baked data and timed animations."""

    # Show transcript
    await send_json({
        "type": "transcript",
        "text": DEMO_TRANSCRIPT,
        "is_final": True,
    })
    await asyncio.sleep(0.5)

    # Agent logs with delays
    for log in DEMO_AGENT_LOGS:
        await send_json({
            "type": "agent_log",
            "agent": log["agent"],
            "label": log["label"],
            "content": log["content"],
            "data": [DEMO_AGENT1_RESULT, DEMO_AGENT2_RESULT, DEMO_AGENT3_RESULT][log["agent"] - 1],
        })
        await asyncio.sleep(0.8)

    # Store session data
    session["extracted"] = DEMO_AGENT1_RESULT
    session["inventory_report"] = DEMO_AGENT2_RESULT
    session["strategy"] = DEMO_AGENT3_RESULT
    session["demo_mode"] = True

    # Create pending order
    order_id = create_order(
        buyer_name=DEMO_AGENT1_RESULT["buyer"],
        store_name=DEMO_AGENT1_RESULT["store"],
        item_id=DEMO_AGENT2_RESULT["item_id"],
        quantity=DEMO_AGENT3_RESULT["suggested_quantity"],
        agreed_price=DEMO_AGENT3_RESULT["suggested_price"],
    )
    session["order_id"] = order_id

    # Send recommendation
    await send_json({
        "type": "recommendation",
        "action": DEMO_AGENT3_RESULT["action"],
        "data": DEMO_AGENT3_RESULT,
        "extracted": DEMO_AGENT1_RESULT,
        "inventory": DEMO_AGENT2_RESULT,
    })

    # TTS (non-blocking)
    fire_tts(send_json, DEMO_TTS_TEXT)


# ─── Confirm Handler ───

async def handle_confirm(session: dict, send_json, send_inventory_update):
    """Handle order confirmation: run Agent 4, save email, generate receipt if ACCEPT, update inventory."""
    extracted = session.get("extracted")
    strategy = session.get("strategy")
    order_id = session.get("order_id")

    if not extracted or not strategy:
        await send_json({"type": "error", "message": "No active deal to confirm."})
        return

    try:
        # Agent 4 — Generate luxury email (use pre-baked in demo mode)
        if session.get("demo_mode"):
            email = DEMO_AGENT4_EMAIL
        else:
            email = agent_copywriter(extracted, strategy)

        await send_json({
            "type": "agent_log",
            "agent": 4,
            "label": "COPYWRITER",
            "content": "Luxury confirmation email generated",
            "data": {"email": email},
        })

        # Save to DB
        if order_id:
            confirm_order(order_id, email)

        # Send email to frontend
        await send_json({
            "type": "confirmation_email",
            "content": email,
        })

        # Generate payment receipt if action was ACCEPT (instant deal)
        action = strategy.get("action", "")
        if action == "ACCEPT" and order_id:
            try:
                if session.get("demo_mode"):
                    receipt_text = generate_demo_receipt(extracted, strategy, order_id)
                else:
                    receipt_text = agent_receipt(extracted, strategy, order_id)
                await send_json({
                    "type": "agent_log",
                    "agent": 5,
                    "label": "RECEIPT",
                    "content": "Payment receipt generated for instant ACCEPT",
                    "data": {"receipt": receipt_text},
                })
                await send_json({
                    "type": "payment_receipt",
                    "content": receipt_text,
                })
            except Exception as e:
                print(f"[Receipt Error] {e}")

        # Refresh inventory + orders on frontend
        await send_inventory_update()

        # Reset session for next deal
        session["extracted"] = None
        session["inventory_report"] = None
        session["strategy"] = None
        session["order_id"] = None
        session["demo_mode"] = False

        # Tell frontend to clear the deal card
        await send_json({"type": "clear_deal_card"})

    except Exception as e:
        await send_json({"type": "error", "message": f"Confirmation error: {str(e)}"})


def generate_demo_receipt(extracted: dict, strategy: dict, order_id: int) -> str:
    """Generate a pre-baked receipt for demo mode (no API call)."""
    from datetime import datetime
    qty = strategy.get('suggested_quantity', extracted.get('quantity', 0))
    price = strategy.get('suggested_price', extracted.get('price', 0))
    total = qty * price
    return f"""═══════════════════════════════════════════
              MAISON AURA
       Paris Fashion Week — AW25
═══════════════════════════════════════════

PAYMENT RECEIPT

Receipt No:  AURA-{order_id:04d}
Date:        {datetime.now().strftime('%d %B %Y')}

───────────────────────────────────────────
BILLED TO:
  {extracted.get('buyer', 'Client')}
  {extracted.get('store', '')}

───────────────────────────────────────────
ITEM DETAILS:

  {extracted.get('item', 'Item')}
  Quantity:    {qty} units
  Unit Price:  EUR {price:,.2f}
                              ────────────
  SUBTOTAL:    EUR {total:,.2f}
  TAX (0%):    EUR 0.00  (B2B Intra-EU)
                              ────────────
  TOTAL DUE:   EUR {total:,.2f}

───────────────────────────────────────────
Payment Terms: Net 30
Bank: BNP Paribas — IBAN FR76 XXXX XXXX XXXX

═══════════════════════════════════════════
           Merci pour votre confiance.
              Maison AURA, Paris
═══════════════════════════════════════════"""


# ─── Suspend Handler ───

async def handle_suspend(session: dict, send_json, send_inventory_update):
    """Suspend/hold an order — no stock deduction, deal kept on hold for later decision."""
    order_id = session.get("order_id")
    extracted = session.get("extracted")
    strategy = session.get("strategy")

    if not order_id:
        await send_json({"type": "error", "message": "No active deal to suspend."})
        return

    try:
        suspend_order(order_id)

        await send_json({
            "type": "agent_log",
            "agent": 3,
            "label": "STRATEGIST",
            "content": "Deal SUSPENDED -- on hold for later decision. No stock deducted.",
            "data": {"action": "SUSPEND", "order_id": order_id},
        })

        await send_json({
            "type": "order_suspended",
            "order_id": order_id,
            "buyer": extracted.get("buyer", "Unknown") if extracted else "Unknown",
            "store": extracted.get("store", "Unknown") if extracted else "Unknown",
        })

        # Refresh data
        await send_inventory_update()

        # Reset session for next deal
        session["extracted"] = None
        session["inventory_report"] = None
        session["strategy"] = None
        session["order_id"] = None
        session["demo_mode"] = False

        # Tell frontend to clear the deal card
        await send_json({"type": "clear_deal_card"})

    except Exception as e:
        await send_json({"type": "error", "message": f"Suspend error: {str(e)}"})


# ─── Startup ───

@app.on_event("startup")
async def startup():
    init_db()
    print("[AURA] Backend ready - inventory seeded")
    print("[AURA] For multi-rep: run with --host 0.0.0.0 and connect from other machines on LAN")
