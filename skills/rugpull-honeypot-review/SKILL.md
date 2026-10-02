---
name: rugpull-honeypot-review
description: >
  Review a token/contract for rug-pull, honeypot, and malicious-admin traits: hidden or
  uncapped mint, owner-removable liquidity, blacklist/anti-bot sell traps, disabled sells,
  arbitrary tax changes, pausing of user funds, backdoor admin powers, un-renounced
  ownership. The dominant risk class for low-cap BSC tokens. Use for token/presale contracts.
---

# Rug Pull / Honeypot / Malicious Admin Review

These aren't always "bugs" — they're intentional owner powers. The job is to surface
every way the deployer can trap or drain holders. This is the most common BSC loss class.

## Checklist
1. **Mint:** any `mint`/`_mint` callable by owner, uncapped? Can supply be inflated after
   launch? Is minting renounced/disabled?
2. **Sell blocking (honeypot):**
   - blacklist / `isBot` / `_excluded` lists the owner can add any address to, blocking
     sells while allowing buys.
   - `tradingEnabled`/`canTransfer` flags only the owner flips.
   - max-tx / max-wallet set so low that selling reverts.
   - transfer logic with asymmetric buy vs sell conditions.
3. **Tax/fee abuse:** owner can set buy/sell tax arbitrarily high (e.g. `setFee` with no
   cap) → effectively confiscatory. Check for a hard cap in code.
4. **Liquidity:** can the owner pull LP, or does the contract hold LP tokens it can
   withdraw? Is LP locked/burned? (Lock status is off-chain — note it needs manual check.)
5. **Pausability:** `pause()`/`whenNotPaused` that can freeze all holder transfers.
6. **Backdoors:** owner functions that withdraw arbitrary tokens/ETH from the contract,
   change router/pair, or `delegatecall` to owner-chosen code.
7. **Ownership:** is ownership renounced? If not, all the above are live. A "renounced"
   owner plus a privileged second role (e.g. `authorized`) is a fake-out — check all roles.
8. **Proxy:** upgradeable token = owner can rewrite everything later (see proxy-resolution).

## Confirm vs downgrade
- CONFIRMED high/critical: uncapped owner mint, addable blacklist that blocks sells,
  uncapped settable tax, owner-removable liquidity, pausable transfers, upgradeable token
  with live admin.
- Downgrade: ownership renounced AND no second privileged role AND capped fees AND
  non-upgradeable AND no mint.

## Report
List each owner power, whether it's currently live (ownership renounced?), and the worst-
case holder impact. Be explicit that LP-lock and team-wallet distribution need off-chain
verification. Describe technical risk only — do not give a buy/sell recommendation.
