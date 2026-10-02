---
name: dos-review
description: >
  Review denial-of-service vectors: unbounded loops / gas-limit DoS, revert-in-loop
  (one bad element blocks all), gas griefing, forced-ether balance assumptions,
  push-payment failures. Use for contracts iterating over user-controlled collections
  or making push payments.
---

# Denial of Service Review

## Checklist
1. **Unbounded loops:** any loop over an array/mapping whose length attackers can grow
   (e.g. a list of stakers, recipients, pending claims). If iteration can exceed the
   block gas limit, the function becomes permanently stuck.
2. **Revert-in-loop:** distributing to many addresses in one loop — a single recipient
   that reverts (malicious receiver, blacklisted on the token) blocks everyone. Prefer
   pull-over-push.
3. **Push payments:** `.transfer`/`.send` to a contract that reverts or consumes all gas;
   also 2300-gas stipend issues.
4. **Forced ether:** `selfdestruct` or coinbase can force-send ETH; any logic asserting
   exact `address(this).balance` can be bricked.
5. **Griefing:** operations where an attacker makes an action arbitrarily expensive for
   others at low cost to themselves (e.g. seeding many dust positions).
6. **External dependency DoS:** a required external call that an attacker can make fail.

## Confirm vs downgrade
- CONFIRMED: attacker-growable unbounded loop in a critical path; push distribution that
  one reverting recipient can freeze.
- Downgrade: bounded/paginated iteration, pull-payment pattern, no exact-balance asserts.

## Remediation
- Pull-over-push withdrawals; per-user claim instead of batch push.
- Bound/paginate iteration; cap list sizes.
- Never assert exact `balance`; isolate external-call failures.
