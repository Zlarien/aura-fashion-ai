# AURA — Script de Pitch (200 secondes)

## Chorégraphie de la Démo (Total : ~200s)

---

### HOOK — 0:00 à 0:15 (15s)

> "Imaginez la Fashion Week de Paris. Un showroom bondé d'acheteurs de chez Harrods, Bergdorf ou Selfridges — et un seul commercial qui doit enchainer 40 rendez-vous par jour. Chaque vente implique de vérifier les stocks, calculer les marges, gérer les contre-propositions et envoyer des emails de confirmation — tout en gardant un contact visuel permanent avec l'acheteur."
>
> "AURA est une oreillette assistée par IA qui gère tout cela en temps réel, par la voix."

**[Screen: Dashboard is open, dark luxury UI visible, mic off]**

---

### DEMO PARTIE 1 — La Négociation (0:15 à 0:50, ~35s)

> "Laissez-moi vous montrer."

**[Action: Press Shift+D to trigger demo mode — OR speak into mic if using live mode]**

Phrase de démo (à dire ou déclencher) :
> *"Sophie Laurent de chez Harrods veut 150 unités de l'Obsidian Trench à 1200 euros."*

**[Point to screen as agents cascade:]**

> "Regardez — quatre agents IA s'enchaînent en séquence :"
>
> "L'Agent 1 **extrait** les données de la vente : acheteur, boutique, article, quantité, prix — même si je prononce mal 'Obsidian Trench', l'IA fait la correspondance."
>
> "L'Agent 2 **vérifie les stocks** : il n'en reste que 120, mais la marge est excellente à 41%."
>
> "L'Agent 3 — le **stratège** — recommande une contre-proposition : 120 unités à 1350 euros. C'est une prime à l'exclusivité sur une allocation limitée."

**[Point to stock bar turning yellow, the recommendation badge, the counter-offer details]**

> "Et AURA murmure cette contre-proposition directement dans l'oreillette — l'acheteur ne voit jamais d'écran."

---

### DEMO PARTIE 2 — Confirmation Vocale + Email (0:50 à 1:10, ~20s)

> "Maintenant, l'acheteur accepte."

**[Action: Say "confirmed" into mic — OR click Confirm button]**

> "Je viens de dire 'confirmé' — sans bouton, sans toucher l'écran. AURA l'a détecté à la voix."

**[Point to: Confirm button turning green, email preview appearing, stock deducting]**

> "Instantanément : un email de confirmation est généré, le stock est déduit, et un reçu de paiement est prêt. Je peux même modifier l'email, le téléphone ou l'adresse de livraison directement sur la fiche."

---

### DEMO PARTIE 3 — Alternatives Intelligentes + Tarification Dynamique (1:10 à 1:35, ~25s)

> "Et si nous sommes en rupture de stock ? Un acheteur veut 200 Midnight Velvet Suits — mais il n'en reste que 15."

**[Action: Use Shift+T debug input or mic: "Marc Dupont from Galeries Lafayette wants 200 Midnight Velvet Suit at 1800 euros"]**

> "AURA ne se contente pas de dire 'en rupture'. Le stratège scanne tout le catalogue, trouve un article similaire — comme l'Obsidian Trench — et le propose avec une remise de 10% en compensation. Le badge affiche ALTERNATIVE en vert."

**[Point to: ALTERNATIVE badge, alternative item name, discount percentage]**

> "C'est encore plus intelligent : si un article est très demandé — plusieurs commandes, peu de stock — AURA négocie plus fermement. La loi de l'offre et de la demande, intégrée à chaque transaction."

---

### DEMO PARTIE 4 — Consultation du Catalogue + Référence Mannequin (1:35 à 1:55, ~20s)

> "L'acheteur demande : 'Montre-moi le catalogue de Jade Li.'"

**[Action: Say "show me Jade Li catalog" or type via Shift+T]**

> "AURA affiche chaque article porté par Jade Li — comme la Noir Midi Dress du pré-show AW25 — avec les niveaux de stock et les indicateurs de demande. L'acheteur l'entend également lu à haute voix via le TTS."

**[Point to: Catalog display in deal card, stock info, TTS playing]**

> "Ils peuvent aussi dire : 'Je veux ce que Jade Li portait' — l'IA identifie l'article exact et lance tout le processus de vente."

---

### DEMO PARTIE 5 — Coordination Multi-Agents (1:55 à 2:25, ~30s)

> "Dans les showrooms, plusieurs commerciaux travaillent sur le même stock. AURA gère cela."

**[Action: Open a second browser tab (or second machine on LAN) → enter a different rep name]**

> "Deux commerciaux, deux écrans, un seul stock partagé. Regardez ce qui se passe quand je confirme une vente sur cet écran."

**[Action: On Tab 1, confirm the current deal. Point to Tab 2.]**

> "L'onglet 2 voit le stock se mettre à jour instantanément — et reçoit une notification : 'Sophie vient de confirmer 120 Obsidian Trenches pour Harrods'. Pas de synchro manuelle. Pas de tableur. Du temps réel."

**[Point to: Gold toast on Tab 2, inventory updating live, rep count badge]**

**[Action: Press Shift+C on Tab 2 — colleague stock deduction]**

> "Et quand un collègue vend du stock depuis un autre showroom, les deux commerciaux reçoivent l'alerte visuelle et sonore dans leur oreillette."

**[Point to: Stock flash on both tabs, TTS playing]**

---

### DEMO PARTIE 6 — Chaos du Showroom (2:25 à 2:40, ~15s)

**[Action: Press Shift+P — competing suspended order]**

> "Un autre acheteur a une commande en attente sur le même article. AURA m'avertit avant que je ne m'engage sur un stock déjà réservé."

**[Point to: Competing order toast, amber warning]**

---

### CONCLUSION — 2:40 à 3:20 (40s)

> "AURA repose sur quatre APIs — Deepgram pour la reconnaissance vocale en temps réel, Groq pour l'inférence LLM ultra-rapide, Cartesia pour les réponses vocales naturelles, et un backend FastAPI léger avec SQLite."
>
> "Pas de frameworks lourds. Pas de LangChain. Juste du Python rapide et modulaire — conçu en 48 heures."
>
> "Cinq actions clés : ACCEPTER, CONTRE-PROPOSER, UPSELL, ALTERNATIVE, SUSPENDRE. Une tarification sensible à la demande. Une navigation catalogue par mannequin. Une saisie texte de secours. Et maintenant — une coordination multi-commerciaux synchronisée en direct sur tout le showroom."
>
> "Le commerce de gros dans le luxe représente 500 milliards de dollars par an. Aujourd'hui, tout se fait encore au stylo et au papier. AURA transforme chaque commercial en un super-humain — une conversation après l'autre."
>
> "**AURA. L'IA qui murmure les ventes.**"

---

## Points Clés à Mettre en Avant

| Moment | Quoi pointer | Pourquoi c'est important |
|--------|--------------|-------------------------|
| Cascade d'agents | Les lignes de log qui défilent | Montre le pipeline multi-agents en action |
| Barre de stock | Barre jaune + "120/150" | Conscience réelle de l'inventaire |
| Contre-proposition | Badge stratégie + changement de prix | Jugement business de l'IA, pas juste de la recherche |
| Confirmation vocale | Dire "confirmed" sans les mains | Zéro friction UI — expérience oreillette |
| Génération d'email | Panneau de prévisualisation email | Clôture de la vente de bout en bout |
| Infos modifiables | Champs email/téléphone/adresse | Reprise en main manuelle si la voix ne suffit pas |
| Mise en attente (Suspend) | "hold on" → badge orange | Flux de travail réel : toutes les ventes ne se concluent pas |
| **Alternative** | **Badge vert ALTERNATIVE** | **Récupération intelligente en cas de rupture** |
| **Prix selon demande** | **Niveaux de demande dans le catalogue** | **L'offre et la demande dictent la négociation** |
| **Requête catalogue** | **"show me Jade Li catalog"** | **Navigation par mannequin, pas par codes produits** |
| **Saisie texte debug** | **Shift+T → taper le transcript** | **Secours si le micro échoue** |
| **Sync multi-commerciaux** | **Deux onglets/machines, même stock** | **Coordination temps réel dans le showroom** |
| **Notifications collègues** | **Notification dorée : "Sophie a confirmé..."** | **Plus besoin de synchro manuelle** |
| **Badge compte agents** | **Compteur vert dans le header** | **Voir qui est connecté** |
| Correspondance floue | Mauvaise prononciation de l'article | Robuste face aux erreurs de diction réelles |
| Référence mannequin | "ce que Jade Li portait" → article trouvé | Intelligence contextuelle — connaît le showroom |
| Tags mannequins | Tags sur les articles d'inventaire | Lien visuel entre mannequins et produits |
| Alerte collègue | Shift+C → flash stock + notification | Coordination multi-commerciaux en temps réel |
| Commande concurrente | Shift+P → alerte orange | Évite de survendre sur un stock partagé |
| Ajout de stock | "nous avons reçu 50 nouveaux..." | Réapprovisionnement à la voix, sans saisie manuelle |
| Reset du stock | Shift+R | Réinitialisation instantanée pour une nouvelle démo |
| Nettoyage fiche | Après confirmation/mise en attente | Prêt pour la vente suivante automatiquement |

## Checklist Démo (Avant de Commencer)

- [ ] Supprimer `inventory.db` pour un stock neuf + table model_assignments
- [ ] Serveur lancé : `cd backend && set PYTHONIOENCODING=utf-8 && python -m uvicorn main:app --host 0.0.0.0 --port 8000`
- [ ] Ouvrir `http://VOTRE_IP_LAN:8000/` dans Chrome (sur les deux machines)
- [ ] Entrer le nom du commercial sur chaque machine
- [ ] Tester le mode démo Shift+D
- [ ] Tester la saisie texte Shift+T (taper une vente, Entrée ou ENVOYER)
- [ ] Tester Shift+R pour réinitialiser l'inventaire
- [ ] Tester Shift+C pour la déduction collègue (flash + notification + TTS)
- [ ] Tester Shift+P pour la commande concurrente (alerte orange + TTS)
- [ ] Tester la requête catalogue : "show me Jade Li catalog"
- [ ] Tester la suggestion alternative (demander un article avec stock insuffisant)
- [ ] Tester les champs modifiables (email/téléphone/adresse) sur la fiche
- [ ] Vérifier que la fiche se vide après confirmation/mise en attente
- [ ] Tester le multi-agents : deux onglets ou machines, vérifier la synchro du stock
- [ ] Tester la notification de vente collègue entre les onglets
- [ ] Tester l'entrée micro (si démo vocale live)
- [ ] Audio du navigateur autorisé (pour le TTS)
- [ ] Vérifier que les tags mannequins sont visibles sur les articles

## Raccourcis Clavier

| Raccourci | Action |
|-----------|--------|
| Shift+D | Déclencher le mode démo (vente pré-enregistrée) |
| Shift+T | Activer la saisie texte debug (taper les transcripts) |
| Shift+R | Réinitialiser l'inventaire au stock de départ |
| Shift+C | Simuler une vente de stock par un collègue |
| Shift+P | Simuler une commande concurrente en attente |

## Plan de Secours

Si le micro live échoue pendant la démo :
1. Utilisez **Shift+D** pour le flux de démo pré-enregistré (garanti de fonctionner, sans appels API vocaux)
2. Précisez : "C'est le même pipeline — nous utilisons simplement une entrée pré-enregistrée pour plus de fiabilité"
3. Les données de démo montrent exactement la même cascade d'agents, de manière déterministe
4. Utilisez **Shift+C** et **Shift+P** pour les simulations de collègues — ils fonctionnent toujours

## Le pitch en une phrase (pour les juges de passage)

> "AURA est une oreillette IA pour les commerciaux en showroom de mode — elle écoute les conversations avec les acheteurs, vérifie les stocks, calcule les marges, suggère des contre-propositions et des alternatives intelligentes, ajuste les prix selon la demande, permet de consulter le catalogue par mannequin à la voix, confirme les ventes les mains libres et coordonne les stocks en temps réel entre tous les vendeurs du showroom. Six actions IA : ACCEPTER, CONTRE-PROPOSER, UPSELL, ALTERNATIVE, SUSPENDRE, et synchro live multi-reps. Développé en 48 heures avec Groq, Deepgram et Cartesia."
