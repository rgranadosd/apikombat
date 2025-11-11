# How to Play – API Kombat

## Objective

Be the first player to place **four healthy aspects** on your board. An aspect is healthy when it is **not vulnerable**.

## Game components

### Players

- Two competitors: **You** versus the **AI**.
- Each player controls:
  - A hand of cards (no hard limit; you draw back to three cards at the end of the turn).
  - A board with **four aspect slots**.
  - An optional **Code Freeze** shield activated via a special card.

### Deck breakdown (89 cards)

1. **Aspects (Scoring)** – 17 cards  
   - Four copies of each color: Security, Documentation, Governance, Performance.  
   - One multicolor wildcard.

2. **Attacks & Problems** – 29 cards  
   - 16 security attacks (4× DoS, SQL Injection, OWASP, Brute-Force).  
   - 12 problems (4× Documentation, Governance, Performance).  
   - One multicolor attack/problem wildcard.

3. **Protections** – 29 cards  
   - 16 security protections (4× OAuth2/JWT, HTTPS/SSL, Input Validation, Rate Limiting).  
   - 12 generic protections (4× Documentation, Governance, Performance).  
   - One multicolor protection wildcard.

4. **Interventions** – 14 cards  
   - 4× Refactoring, 4× Migration, 4× Active-Active.  
   - 1× Code Freeze, 1× Rollback.

## Aspect states

1. **Vulnerable** – the next attack destroys the aspect; marked visually with alerts.  
2. **Protections** *(0–2)*  
   - **0**: unprotected.  
   - **1**: shielded (blocks attacks).  
   - **2**: fortified (blocks attacks and cannot be targeted by Active-Active).

## Card types and effects

### Aspects (`aspecto` / `scoring`)
- Place a new aspect on your board.  
- No duplicate colors; max four aspects.  
- Multicolor cards resolve to the first missing color.  
- Every aspect enters healthy (not vulnerable, 0 protections).

### Attacks & Problems (`ataque`, `problema`, `virus`)
- Target the opponent’s board.  
- Code Freeze cancels the attack and is consumed.  
- Protections ≥1 block the effect.  
- If the target aspect is healthy → it becomes vulnerable.  
  If it is already vulnerable → it is destroyed.

### Protections (`proteccion`, `medicina`)
- Target your own aspects.  
- If vulnerable, the protection heals it first.  
- Then raise the protection level up to two.

### Interventions (`intervencion`, `tratamiento`)

**Migration (`migracion` / `ladrón`)**  
Steal an aspect your foe controls and you do not. States (vulnerability/protections) are kept. Code Freeze blocks it.  
Restriction: the opponent must own at least one aspect you are missing; if you specify a color, it must exist.

**Refactoring (`refactoring` / `trasplante`)**  
Swap one of your aspects with one from the opponent. You may target a specific color. States are preserved. Code Freeze blocks it.  
Restriction: both players must control at least one aspect.

**Active-Active (`activo_activo` / `contagio`)**  
Expose an opponent aspect that matches a vulnerable aspect you already have. Fails if the target is fortified or already vulnerable. Code Freeze blocks it.

**Code Freeze (`code_freeze` / `guante`)**  
Activates a shield that blocks the next attack/intervention that would affect you. The shield is consumed after blocking.

**Rollback (`rollback` / `error`)**  
Reduce an opponent aspect’s protection by 1. Requires the target to have protection ≥1. Code Freeze blocks it.

## Turn flow

1. **Setup**: shuffle the full deck, deal three cards to each player, randomly choose who starts.  
2. **Turn phase** – on your turn you may:
   - **Play a card** (if valid, resolve its effect and end your turn).  
   - **Discard** one or more cards (end your turn).  
   - **Pass** (if you cannot or prefer not to play/discard).  
3. **End of turn**: draw back to three cards. If the deck runs out, recycle the discard pile.  
4. **Victory check**: if someone controls four healthy aspects, that player immediately wins.

## Wildcards (multicolor)

- **Aspect wildcards**: resolve to the first color you don’t control.  
- **Attack/problem wildcards**: target the first opponent aspect without protection.  
- **Protection wildcards**: attach to the first aspect you control.

## Discard recycle

When the deck is empty, shuffle the entire discard pile and use it as the new deck.

## Special states

### Code Freeze
- Activated by the card of the same name.  
- Blocks the next hostile action affecting you.  
- Consumed once it blocks successfully.

### Protections
- Level 1: shields against attacks.  
- Level 2: shields and prevents Active-Active.  
- Cannot exceed level 2.

### Vulnerability
- A second hit will destroy the aspect.  
- Can be cleared by applying a protection.

## Victory conditions

### Win
- Reach four healthy aspects.  
- If both players reach it simultaneously, the first to achieve it wins.

### Stalemate / Blocked game
- After 50 consecutive turns without valid plays, declare a stalemate.

## Global restrictions

1. **Aspect limit**: four maximum, one per color.  
2. **Hand size**: no cap; draw back to three cards at turn end if possible.  
3. **Play validation**: a card must satisfy its constraints to be played.  
4. **Effect order**: effects resolve immediately; if they fail, the card is still spent.

## Technical notes

- Turns alternate between human and AI.  
- Every turn you can play, discard, or pass.  
- The discard pile recycles automatically.  
- Victory is checked after each action.  
- Card effects are atomic: they either complete fully or not at all.

---

**End of the how-to-play guide.**

