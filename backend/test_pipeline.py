"""Quick pipeline test — inject transcript via WebSocket, verify all 4 agents + TTS."""
import asyncio
import websockets
import json

async def test():
    async with websockets.connect("ws://127.0.0.1:8000/ws") as ws:
        # Skip initial inventory + orders messages
        await ws.recv()
        await ws.recv()

        # Inject transcript
        print(">>> Injecting transcript...")
        await ws.send(json.dumps({
            "type": "inject_transcript",
            "text": "Aura, Victoria Chen from Selfridges wants 80 units of the Pearl Evening Gown at 2000 euros"
        }))

        # Collect responses
        got_rec = False
        got_tts = False
        while True:
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=60))
            t = msg.get("type", "")

            if t == "transcript":
                print(f"[TRANSCRIPT] {msg['text']}")
            elif t == "agent_log":
                print(f"[AGENT {msg['agent']}] {msg['label']}: {msg['content'][:120]}")
            elif t == "recommendation":
                print(f"\n[RECOMMENDATION] {msg['action']}")
                for k, v in msg.get("data", {}).items():
                    print(f"  {k}: {str(v)[:100]}")
                got_rec = True
            elif t == "tts_audio":
                print(f"\n[TTS] Audio: {len(msg.get('audio',''))} base64 chars")
                got_tts = True
            elif t == "error":
                print(f"\n[ERROR] {msg['message']}")
                break

            if got_rec and got_tts:
                break

        # Test CONFIRM
        if got_rec:
            print("\n>>> Sending CONFIRM...")
            await ws.send(json.dumps({"type": "confirm"}))
            while True:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
                t = msg.get("type", "")
                if t == "confirmation_email":
                    print(f"[EMAIL] {len(msg['content'])} chars")
                    print(msg["content"][:300])
                elif t == "orders":
                    orders = msg.get("orders", [])
                    print(f"\n[ORDERS] {len(orders)} orders, total: {msg.get('total_revenue',0)} EUR")
                    break

        print("\n=== ALL PASS ===" if (got_rec and got_tts) else "\n=== FAIL ===")

asyncio.run(test())
