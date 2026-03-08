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
from database import init_db, get_all_inventory, get_confirmed_orders, get_suspended_orders, create_order, confirm_order, suspend_order
from agents import agent_extract, agent_inventory_check, agent_strategist, agent_copywriter, agent_receipt, run_pipeline, detect_voice_command
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
                            # Check for voice commands first (confirm/suspend)
                            voice_cmd = detect_voice_command(transcript)
                            if voice_cmd == "confirm" and session.get("extracted"):
                                await send_json({"type": "voice_command", "action": "confirm"})
                                await handle_confirm(session, send_json, send_inventory_update)
                            elif voice_cmd == "suspend" and session.get("extracted"):
                                await send_json({"type": "voice_command", "action": "suspend"})
                                await handle_suspend(session, send_json, send_inventory_update)
                            elif voice_cmd and not session.get("extracted"):
                                # Voice command but no active deal — ignore gracefully
                                await send_json({"type": "agent_log", "agent": 0, "label": "AURA",
                                    "content": "No active deal to " + voice_cmd + ". Speak a deal first.",
                                    "data": {}})
                            else:
                                # Regular deal transcript — run the agent pipeline
                                await handle_pipeline(transcript, session, send_json, send_inventory_update)

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
                    await handle_demo(session, send_json, send_inventory_update)

                # ─── Confirm Order ───
                elif msg_type == "confirm":
                    await handle_confirm(session, send_json, send_inventory_update)

                # ─── Suspend Order ───
                elif msg_type == "suspend":
                    await handle_suspend(session, send_json, send_inventory_update)

                # ─── Inject Transcript (test mode, bypass Deepgram) ───
                elif msg_type == "inject_transcript":
                    transcript = data.get("text", "")
                    if transcript:
                        await send_json({"type": "transcript", "text": transcript, "is_final": True})
                        # Check for voice commands first
                        voice_cmd = detect_voice_command(transcript)
                        if voice_cmd == "confirm" and session.get("extracted"):
                            await send_json({"type": "voice_command", "action": "confirm"})
                            await handle_confirm(session, send_json, send_inventory_update)
                        elif voice_cmd == "suspend" and session.get("extracted"):
                            await send_json({"type": "voice_command", "action": "suspend"})
                            await handle_suspend(session, send_json, send_inventory_update)
                        else:
                            await handle_pipeline(transcript, session, send_json, send_inventory_update)

                # ─── Get Inventory ───
                elif msg_type == "get_inventory":
                    await send_inventory_update()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WS Error] {e}")
    finally:
        if session["deepgram"]:
            await session["deepgram"].stop()


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

        session["extracted"] = extracted
        session["inventory_report"] = inventory_report
        session["strategy"] = strategy

        # Create pending order if item was found
        if inventory_report.get("item_found"):
            order_id = create_order(
                buyer_name=extracted.get("buyer", "Unknown"),
                store_name=extracted.get("store", "Unknown"),
                item_id=inventory_report["item_id"],
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

        # Generate TTS for voice summary
        try:
            voice_text = strategy.get("voice_summary", "Processing complete.")
            # If no email was provided by the buyer, append a gentle ask
            buyer_email = extracted.get("email")
            if not buyer_email:
                voice_text += " By the way, do you have an email for the buyer? It's optional but useful for the confirmation."
            audio_bytes = await synthesize_speech(voice_text)
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            await send_json({"type": "tts_audio", "audio": audio_b64})
        except Exception as e:
            print(f"[TTS Error] {e}")

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

    # TTS
    try:
        audio_bytes = await synthesize_speech(DEMO_TTS_TEXT)
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        await send_json({"type": "tts_audio", "audio": audio_b64})
    except Exception as e:
        print(f"[Demo TTS Error] {e} — skipping TTS in demo")


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

    except Exception as e:
        await send_json({"type": "error", "message": f"Suspend error: {str(e)}"})


# ─── Startup ───

@app.on_event("startup")
async def startup():
    init_db()
    print("[AURA] Backend ready - inventory seeded")
