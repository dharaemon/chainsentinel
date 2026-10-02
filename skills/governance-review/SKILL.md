---
name: governance-review
description: >
  Review on-chain governance: flash-loan / borrowed voting power, vote buying, timelock
  bypass, low-quorum capture, double-voting, snapshot manipulation, malicious proposal
  execution. Use for DAO/governor/timelock contracts.
---

# Governance Review

## Checklist
1. **Voting power source:** is it snapshotted at proposal creation (`getPriorVotes` at a
   past block) or read live? Live reads enable **flash-loan voting** — borrow tokens,
   vote, repay. Snapshot at a block *before* the proposal is the mitigation.
2. **Delegation timing:** can power be acquired after the snapshot and still count?
3. **Quorum & thresholds:** quorum high enough to resist cheap capture? proposal
   threshold meaningful?
4. **Timelock:** is execution gated behind a `TimelockController` with a real delay, so
   users can exit before a malicious proposal lands? Can the delay be bypassed?
5. **Double voting:** one address voting multiple times; voting with the same tokens
   across addresses within a snapshot.
6. **Proposal payload:** can a proposal call arbitrary targets (including the token
   minter, treasury, or upgrade function)? What's the blast radius?
7. **Emergency/guardian powers:** who can cancel/veto, and can that be abused?

## Confirm vs downgrade
- CONFIRMED: live (non-snapshot) voting power, or execution without timelock delay.
- Downgrade: past-block snapshot + timelock + sane quorum.

## Remediation
- Snapshot voting power at a block before proposal creation.
- Require a timelock delay on execution; reasonable quorum/threshold.
- Constrain proposal targets or add guardian veto with transparency.
