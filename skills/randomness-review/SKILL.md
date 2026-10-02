---
name: randomness-review
description: >
  Review on-chain randomness: block-based PRNG (timestamp/blockhash/prevrandao),
  predictable seeds, validator/miner-influenced outcomes, insecure VRF integration.
  Use for lotteries, NFT mints, games, and any value-bearing random selection.
---

# Randomness Review

## Checklist
1. **Block-derived randomness:** `block.timestamp`, `blockhash`, `block.difficulty`/
   `block.prevrandao`, `block.number` are all known to or influenceable by the proposer.
   Any value-bearing outcome derived from them is exploitable.
2. **Same-tx predictability:** a contract can read the same "random" value the victim
   uses and only act when favorable (abuse via a wrapper contract).
3. **Commit-reveal:** if used, is there a real two-phase commit with penalties, and is
   the reveal unpredictable at commit time?
4. **VRF integration (Chainlink VRF etc.):** is the fulfillment callback authenticated
   (only the VRF coordinator)? Is state that depends on randomness locked between request
   and fulfillment to prevent front-running the outcome?

## Confirm vs downgrade
- CONFIRMED: payout/mint/winner chosen from block-derived values.
- Downgrade: proper VRF with authenticated callback and locked state, or commit-reveal
  with incentives.

## Remediation
- Use a verifiable randomness source (VRF) with an authenticated fulfillment path.
- Never derive value-bearing randomness from block fields.
- Lock dependent state between request and fulfillment.
