---
name: bridge-review
description: >
  Review cross-chain / bridge and cross-chain messaging contracts: forged deposit/message
  proofs, cross-chain replay, validator/relayer trust, mint-burn desync, light-client /
  Merkle verification bugs, and unauthenticated message handlers (LayerZero lzReceive,
  CCIP ccipReceive, custom relayers). Use for bridges and omnichain apps.
---

# Cross-Chain / Bridge Review

Bridges concentrate value and have produced some of the largest losses in the space.

## Checklist
1. **Message authentication:** the receive handler (`lzReceive`,
   `_nonblockingLzReceive`, `ccipReceive`, custom `onMessage`) must verify:
   - the **caller** is the trusted endpoint/router,
   - the **source chain id** is expected,
   - the **source sender** (remote app address) is the trusted peer.
   Any missing check lets anyone forge messages → mint/withdraw at will.
2. **Proof verification:** for light-client/Merkle bridges, is the proof actually
   validated against a trusted root? Is the root update authenticated? Any way to submit a
   forged proof or reuse an old one?
3. **Replay:** is each message consumed once (nonce / processed-hash set)? Can the same
   proof be replayed on the same chain or a sibling deployment (chainId in the payload)?
4. **Mint/burn parity:** does locking/burning on the source always match
   minting/releasing on the destination, with no path to mint without a corresponding
   lock? Decimals consistent across chains?
5. **Validator/relayer trust:** how many signers, what threshold, EOA or multisig? Key
   compromise blast radius?
6. **Pausing / rate limits:** is there a circuit breaker and per-period withdrawal cap?

## Confirm vs downgrade
- CONFIRMED critical: receive handler not verifying caller + source chain + source sender;
  unauthenticated root/proof; mint without matching lock; missing replay protection.
- Downgrade: full source authentication + replay nonce + verified proofs + rate limits.

## Remediation
- Authenticate every message (endpoint, srcChainId, srcSender) and consume once.
- Verify proofs against an authenticated root; include chainId to stop cross-chain replay.
- Enforce mint/burn parity; add rate limits and a pause guardian.
