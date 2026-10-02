---
name: signature-review
description: >
  Review signature & cryptographic handling: replay (missing nonce/chainId/domain),
  cross-chain replay, ECDSA malleability, ecrecover returning address(0), missing EIP-712
  domain separation, permit front-running/griefing, Merkle proof forgery. Use for any
  contract verifying signatures or Merkle proofs.
---

# Signature & Cryptographic Review

## Checklist
1. **ecrecover zero-address:** `ecrecover` returns `address(0)` on bad input. If the
   contract compares against an unset/zero value, forgery is possible. Use OZ ECDSA
   (`tryRecover`/`recover`) which reverts on zero.
2. **Malleability:** raw `ecrecover` accepts both `s` and `-s`. Enforce low-`s` and
   `v ∈ {27,28}` (OZ ECDSA does this). Matters where the sig itself is used as an id.
3. **Replay protection:** does the signed message include a **nonce** (monotonic per
   signer), **chainId**, **verifying contract address**, and an **expiry/deadline**?
   Missing any → replay on this chain, another chain, or another deployment.
4. **EIP-712 domain separator:** present and correct (name, version, chainId, address)?
   Is chainId re-derived on fork, or cached and stale?
5. **Permit (EIP-2612):** can a griefer front-run `permit` to consume the nonce and DoS
   the subsequent action? Handle permit failure gracefully.
6. **Merkle proofs:** leaf construction unambiguous (hash of typed, length-prefixed data)
   to avoid second-preimage / forged leaves? Is the root upgradeable by admin only?

## Confirm vs downgrade
- CONFIRMED: raw ecrecover compared to a value that can be address(0); no nonce/chainId
  in signed data; cached domain separator without chainId fork handling.
- Downgrade: OZ ECDSA + full EIP-712 domain + nonce + deadline.

## Remediation
- Use OpenZeppelin ECDSA + EIP712 helpers.
- Include nonce, chainId, verifyingContract, and deadline in every signed struct.
- Validate Merkle leaf encoding; restrict root updates.
