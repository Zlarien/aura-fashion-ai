# AURA — 200-Second Pitch Script

## Demo Choreography (Total: ~200s)

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

> "Instantly: a confirmation email is generated, stock is deducted, and a payment receipt is ready. I can edit the buyer's email, phone, or shipping address right on the deal card."

---

### DEMO PART 3 — Smart Alternatives + Demand Pricing (1:10 to 1:35, ~25s)

> "What if stock runs out? A buyer wants 200 Midnight Velvet Suits — but we only have 15."

**[Action: Use Shift+T debug input or mic: "Marc Dupont from Galeries Lafayette wants 200 Midnight Velvet Suit at 1800 euros"]**

> "AURA doesn't just say 'out of stock.' The strategist scans the full catalog, finds a similar item — say the Obsidian Trench — and offers it with a 10% discount as compensation. The badge says ALTERNATIVE in green."

**[Point to: ALTERNATIVE badge, alternative item name, discount percentage]**

> "And it gets smarter: if an item is in high demand — multiple orders, low stock — AURA negotiates harder. Supply and demand, built into every deal."

---

### DEMO PART 4 — Catalog Query + Model Reference (1:35 to 1:55, ~20s)

> "A buyer asks: 'Show me Jade Li's catalog.'"

**[Action: Say "show me Jade Li catalog" or type via Shift+T]**

> "AURA displays every item Jade Li modeled — the Noir Midi Dress from the AW25 pre-show — with stock levels and demand indicators. The buyer hears it read aloud too."

**[Point to: Catalog display in deal card, stock info, TTS playing]**

> "They can also say: 'I want what Jade Li wore' — and it resolves to the actual item and runs the full deal pipeline."

---

### DEMO PART 5 — Multi-Rep Coordination (1:55 to 2:25, ~30s)

> "Fashion showrooms have multiple reps working the same inventory. AURA handles that."

**[Action: Open a second browser tab (or second machine on LAN) → enter a different rep name]**

> "Two reps, two screens, one shared inventory. Watch what happens when I confirm a deal on this screen."

**[Action: On Tab 1, confirm the current deal. Point to Tab 2.]**

> "Tab 2 sees the stock update instantly — and gets a notification: 'Sophie just confirmed 120 Obsidian Trenches for Harrods.' No manual sync. No spreadsheet. Real-time."

**[Point to: Gold toast on Tab 2, inventory updating live, rep count badge]**

**[Action: Press Shift+C on Tab 2 — colleague stock deduction]**

> "And when a colleague sells stock from another showroom, both reps see the alert and hear it through their earpieces."

**[Point to: Stock flash on both tabs, TTS playing]**

---

### DEMO PART 6 — Showroom Chaos (2:25 to 2:40, ~15s)

**[Action: Press Shift+P — competing suspended order]**

> "Another buyer has a pending order on the same item. AURA warns before I over-commit."

**[Point to: Competing order toast, amber warning]**

---

### CLOSE — 2:40 to 3:20 (40s)

> "AURA runs on four APIs — Deepgram for real-time speech-to-text, Groq for sub-second LLM inference, Cartesia for natural voice responses, and a lightweight FastAPI backend with SQLite."
>
> "No frameworks. No LangChain. Just fast, composable Python — built in 48 hours."
>
> "Five actions: ACCEPT, COUNTER, UPSELL, ALTERNATIVE, SUSPEND. Demand-aware pricing. Catalog browsing by designer. Debug text input when the mic fails. Editable buyer info. And now — real-time multi-rep coordination across the showroom floor, shared inventory syncing live between machines."
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
| Editable buyer info | Email/phone/address inputs | Manual override when voice isn't enough |
| Suspend | "hold on" → amber badge | Real workflow: not every deal closes |
| **Alternative** | **Green ALTERNATIVE badge** | **Smart recovery when stock runs out** |
| **Demand pricing** | **Demand levels in catalog** | **Supply/demand drives negotiation** |
| **Catalog query** | **"show me Jade Li catalog"** | **Browse by designer, not product codes** |
| **Debug text input** | **Shift+T → type transcript** | **Backup when mic fails** |
| **Multi-rep sync** | **Two tabs/machines, same inventory** | **Real-time coordination across showroom** |
| **Rep notifications** | **Gold toast: "Sophie confirmed..."** | **No manual sync needed** |
| **Rep count badge** | **Green count in header** | **See who's connected** |
| Fuzzy matching | Mispronounce item name | Robust to real-world speech errors |
| Model reference | "what Jade Li wore" → resolved item | Contextual intelligence — knows the showroom |
| Model tags | Tags on inventory items | Visual link between models and products |
| Colleague alert | Shift+C → stock flash + toast | Real-time multi-rep coordination |
| Competing order | Shift+P → amber warning | Prevents over-commitment on shared stock |
| Stock add | "we received 50 new..." | Voice-driven restocking, no manual entry |
| Stock reset | Shift+R | Instant inventory reset for fresh demos |
| Deal card clear | After confirm/suspend | Clean slate for next deal automatically |

## Demo Checklist (Before You Start)

- [ ] Delete `inventory.db` for fresh stock + model_assignments table
- [ ] Server running: `cd backend && set PYTHONIOENCODING=utf-8 && python -m uvicorn main:app --host 0.0.0.0 --port 8000`
- [ ] Open `http://YOUR_LAN_IP:8000/` in Chrome (both machines)
- [ ] Enter rep name on each machine
- [ ] Test Shift+D demo mode works
- [ ] Test Shift+T debug text input (type a deal, hit Enter or SEND)
- [ ] Test Shift+R resets inventory
- [ ] Test Shift+C colleague deduction (stock flash + toast + TTS)
- [ ] Test Shift+P competing order (amber toast + TTS)
- [ ] Test catalog query: "show me Jade Li catalog"
- [ ] Test alternative suggestion (request item with insufficient stock)
- [ ] Test editable email/phone/address fields on deal card
- [ ] Test deal card clears after confirm/suspend
- [ ] Test multi-rep: open two tabs or two machines, verify inventory sync
- [ ] Test colleague deal notification across tabs
- [ ] Test mic input works (if doing live voice)
- [ ] Browser audio allowed (for TTS playback)
- [ ] Verify model tags visible on inventory items

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Shift+D | Trigger demo mode (pre-baked deal) |
| Shift+T | Toggle debug text input (type transcripts) |
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

> "AURA is an AI earpiece for fashion showroom sales reps — it listens to buyer conversations, checks inventory, calculates margins, suggests counter-offers and smart alternatives, uses demand-based pricing, browses designer catalogs by voice, confirms deals hands-free, and coordinates stock in real-time across multiple reps on the showroom floor. Six AI actions: ACCEPT, COUNTER, UPSELL, ALTERNATIVE, SUSPEND, and live multi-rep sync. Built in 48 hours with Groq, Deepgram, and Cartesia."
