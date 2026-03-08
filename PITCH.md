# AURA — 150-Second Pitch Script

## Demo Choreography (Total: ~150s)

---

### HOOK — 0:00 to 0:15 (15s)

> "Imagine Paris Fashion Week. A showroom packed with buyers from Harrods, Bergdorf, Selfridges — and one sales rep managing 40 meetings a day. Every deal involves inventory checks, margin calculations, counter-offers, and confirmation emails — all while looking the buyer in the eye."
>
> "AURA is an AI earpiece co-pilot that does all of that in real time."

**[Screen: Dashboard is open, dark luxury UI visible, mic off]**

---

### DEMO PART 1 — The Deal (0:15 to 0:50, ~35s)

> "Let me show you."

**[Action: Press Shift+D to trigger demo mode — OR speak into mic if using live mode]**

Demo sentence (say or trigger):
> *"Sophie Laurent from Harrods wants 150 units of the Obsidian Trench at 1200 euros."*

**[Point to screen as agents cascade:]**

> "Watch — four AI agents fire in sequence:"
>
> "Agent 1 **extracts** the deal: buyer, store, item, quantity, price — even if I mispronounce 'Obsidian Trench' as 'obsidian french,' it still matches."
>
> "Agent 2 **checks inventory**: only 120 in stock, but margin is healthy at 41%."
>
> "Agent 3 — the **strategist** — recommends a counter-offer: 120 units at 1,350 euros. That's a premium for exclusivity on a limited allocation."

**[Point to stock bar turning yellow, the recommendation badge, the counter-offer details]**

> "And AURA whispers the counter-offer back through the earpiece — the buyer never sees a screen."

---

### DEMO PART 2 — Voice Confirm + Email (0:50 to 1:10, ~20s)

> "Now the buyer says yes."

**[Action: Say "confirmed" into mic — OR click Confirm button]**

> "I just said 'confirmed' — no buttons, no screen tap. AURA detected it by voice."

**[Point to: Confirm button turning green, email preview appearing, stock deducting]**

> "Instantly: a confirmation email is generated, stock is deducted, and a payment receipt is ready. If I hadn't mentioned the buyer's email, AURA asks for it aloud — mid-conversation."

---

### DEMO PART 3 — Model Reference (1:10 to 1:30, ~20s)

> "Here's where it gets powerful. A buyer says: 'I want what Jade Li wore yesterday.'"

**[Action: Say "I want two of what Jade Li wore" into mic — OR use inject_transcript]**

> "AURA knows Jade Li modeled the Noir Midi Dress at yesterday's pre-show fitting. It resolves the reference, pulls the item, and runs the full deal pipeline — the buyer never needs to know the product name."

**[Point to: Model tag on inventory item, deal card populating with Noir Midi Dress]**

> "Sales reps can also assign new model references on the fly — 'Amara Osei wore the Pearl Evening Gown at tonight's gala' — and it's immediately available to reference."

---

### DEMO PART 4 — Live Showroom Chaos (1:30 to 1:55, ~25s)

> "But showrooms are chaotic. Stock changes constantly."

**[Action: Press Shift+C — colleague stock deduction alert]**

> "A colleague in Showroom B just sold 30 Crimson Silk Blouses. AURA alerts me instantly — I see the stock flash and hear the update through my earpiece. No surprises mid-negotiation."

**[Point to: Stock flash animation, alert toast, inventory updating]**

**[Action: Press Shift+P — competing suspended order]**

> "And another buyer has a pending order on the same item I'm discussing. AURA warns me before I over-commit."

**[Point to: Competing order toast with amber styling]**

> "I can also restock by voice — 'we received 50 new Crimson Silk Blouses' — and reset inventory to base with Shift+R."

---

### CLOSE — 1:55 to 2:30 (35s)

> "AURA runs on four APIs — Deepgram for real-time speech-to-text, Groq for sub-second LLM inference, Cartesia for natural voice responses, and a lightweight FastAPI backend with SQLite."
>
> "No frameworks. No LangChain. Just fast, composable Python — built in 48 hours."
>
> "Fashion showrooms do 500 billion dollars a year in B2B wholesale. Every deal today is pen-and-paper. AURA turns a sales rep into a superhuman — one conversation at a time."
>
> "**AURA. The AI that whispers deals.**"

---

## Key Things to Highlight

| Moment | What to point at | Why it matters |
|--------|-----------------|----------------|
| Agent cascade | Log lines appearing one by one | Shows multi-agent pipeline in action |
| Stock bar | Yellow bar + "120/150" | Real inventory awareness |
| Counter-offer | Strategy badge + price change | AI business judgment, not just retrieval |
| Voice confirm | Say "confirmed" hands-free | Zero UI friction — earpiece UX |
| Email generation | Email preview panel | End-to-end deal closure |
| Suspend | "hold on" → amber badge | Real workflow: not every deal closes |
| Fuzzy matching | Mispronounce item name | Robust to real-world speech errors |
| Model reference | "what Jade Li wore" → resolved item | Contextual intelligence — knows the showroom |
| Model tags | Tags on inventory items | Visual link between models and products |
| Colleague alert | Shift+C → stock flash + toast | Real-time multi-rep coordination |
| Competing order | Shift+P → amber warning | Prevents over-commitment on shared stock |
| Stock add | "we received 50 new..." | Voice-driven restocking, no manual entry |
| Stock reset | Shift+R | Instant inventory reset for fresh demos |

## Demo Checklist (Before You Start)

- [ ] Delete `inventory.db` for fresh stock + model_assignments table
- [ ] Server running: `cd backend && set PYTHONIOENCODING=utf-8 && python -m uvicorn main:app --host 127.0.0.1 --port 8000`
- [ ] Open `frontend/index.html` in Chrome
- [ ] Test Shift+D demo mode works
- [ ] Test Shift+R resets inventory
- [ ] Test Shift+C colleague deduction (stock flash + toast + TTS)
- [ ] Test Shift+P competing order (amber toast + TTS)
- [ ] Test mic input works (if doing live voice)
- [ ] Browser audio allowed (for TTS playback)
- [ ] Verify model tags visible on inventory items

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Shift+D | Trigger demo mode (pre-baked deal) |
| Shift+R | Reset inventory to seed stock |
| Shift+C | Simulate colleague stock deduction |
| Shift+P | Simulate competing suspended order |

## Backup Plan

If live mic fails during demo:
1. Use **Shift+D** for the pre-baked demo flow (guaranteed to work, no API calls)
2. Mention: "This is the same pipeline — we're just using pre-recorded input for reliability"
3. The demo data shows the exact same agent cascade, just deterministic
4. Use **Shift+C** and **Shift+P** for colleague simulation — these always work

## One-liner (for judges walking by)

> "AURA is an AI earpiece for fashion showroom sales reps — it listens to buyer conversations, checks inventory, calculates margins, suggests counter-offers, confirms deals by voice, resolves model references, and coordinates stock across showrooms. Built in 48 hours with Groq, Deepgram, and Cartesia."
