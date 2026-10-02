# ChainSentinel — Presentation Brief

Audience-facing material for demoing ChainSentinel: a **voiceover script** and
**infographic content** you can drop into slides, a poster, or a reel.

---

## 🎙️ Voiceover Script

*Runtime ~90 seconds. Timecodes are a guide; adjust to your pacing.*

**[0:00–0:10] — Hook**
> "Every week, smart contracts on BNB Chain lose millions — to flash-loan price
> manipulation, broken access control, and outright rug pulls. The code is public. The
> exploits are known. So why do they keep happening? Because reading a contract
> line-by-line is slow, and most people never do it. ChainSentinel changes that."

**[0:10–0:22] — What it is**
> "ChainSentinel is a terminal-based security auditor that works alongside your AI —
> Claude, Codex, or ChatGPT. You give it one thing: a contract address. It pulls the
> public source straight off the blockchain and walks it through a full exploit
> checklist. And it's strictly read-only — it never signs, never deploys, never touches
> a transaction."

**[0:22–0:40] — The pipeline**
> "Here's how a scan runs. Step one, and this is the key move: it checks for a proxy
> first. Most serious contracts hide their real logic behind a proxy, so ChainSentinel
> resolves the implementation before anything else — otherwise you'd be auditing an
> empty shell. Step two, it fetches the verified source. Step three, it scans that
> source against a taxonomy of twenty exploit classes. Step four, optional deep static
> analysis with Slither. And step five, it hands the whole evidence bundle to an AI
> auditor — guided by a dedicated skill file for every single exploit class."

**[0:40–0:58] — The taxonomy**
> "Those twenty classes cover the real attack surface: reentrancy, oracle and
> flash-loan manipulation, access-control and proxy bugs, signature replay, governance
> capture, cross-chain bridge forgery — and the big one for BNB Chain: rug-pull and
> honeypot traits, like hidden mints, sell-blocking blacklists, and un-renounced owner
> keys. Each class has a skill that tells the AI exactly what to look for, how to
> confirm it, and how to rule out false positives."

**[0:58–1:12] — How you run it**
> "Setup is one command — a bootstrap script spins up the environment, installs
> everything, and runs a live test. Then auditing is one line: `chainsentinel audit`,
> the address, done. It writes three files — a human-readable report, a
> machine-readable JSON, and a ready-to-paste AI prompt. Works the same whether you're
> in Claude Code or ChatGPT Codex."

**[1:12–1:25] — Close**
> "The tool gathers the evidence. The AI makes the judgment. You get a prioritized
> report — severity, location, exploit path, and a fix — in minutes, not days. It's
> open source, it's read-only, and it's live on GitHub right now. ChainSentinel: see
> the loophole before someone else does."

---

## 📊 Infographic Content

*Each panel is ready to drop into Canva / slides / a poster.*

### Header
- **Title:** ChainSentinel
- **Tagline:** AI-assisted smart-contract auditor — see the loophole first
- **Badges:** `READ-ONLY` · `BSC + EVM` · `Open Source` · `Works with Claude / Codex / ChatGPT`
- **One-liner:** Give it a contract address. Get a prioritized vulnerability report.

### Panel 1 — The Problem
- Most BSC/DeFi losses come from a **handful of repeat offenders**.
- Top 3 loss vectors on BNB Chain:
  1. **Flash-loan + oracle price manipulation**
  2. **Access-control / proxy bugs**
  3. **Rug pulls & honeypots**
- Root cause: huge volume of **unaudited forks**; nobody reads the code.

### Panel 2 — The Pipeline (5 steps)

| # | Step | What happens |
|---|------|--------------|
| 1 | **Proxy resolution** *(always first)* | Detects EIP-1967 / 1822 / 1167 / beacon proxies, resolves the real implementation + upgrade authority |
| 2 | **Fetch source** | Pulls verified source + ABI from the block explorer |
| 3 | **Heuristic scan** | Flags code against a 20-class exploit taxonomy |
| 4 | **Static analysis** *(optional)* | Runs Slither, folds results in |
| 5 | **AI review** | Hands evidence to Claude / Codex / ChatGPT, guided by per-class skill files |

→ **Output:** `report.md` · `report.json` · `prompt.md`

### Panel 3 — 20 Exploit Classes (color by severity)

**🔴 CRITICAL**
- Oracle / price manipulation
- Flash-loan attacks
- Cross-chain / bridge forgery
- Rug pull / honeypot / malicious admin

**🟠 HIGH**
- Reentrancy
- Access control & authorization
- Proxy & upgradeability
- AMM / liquidity / share inflation
- Vault / lending / staking logic
- Governance capture
- Signature & cryptographic
- Initialization & lifecycle
- Business logic / invariants

**🟡 MEDIUM**
- Arithmetic & numeric
- Token standard / BEP-20 handling
- Randomness
- Denial of service
- External call / interaction
- State & storage

### Panel 4 — How to Run It

**Setup (once):**
```bash
bash scripts/bootstrap.sh --install-skills
```

**Audit a contract:**
```bash
chainsentinel audit 0xCONTRACT --chain bsc --ai claude
```

**Just check for a proxy:**
```bash
chainsentinel proxy 0xCONTRACT --chain bsc
```

### Panel 5 — Works in Either Agent

| Claude Code | ChatGPT / Codex |
|-------------|-----------------|
| Reads the `SKILL.md` files | Auto-reads `AGENTS.md` |
| Say "audit this contract 0x…" | Run the same bootstrap script |
| Skills auto-invoked | Reads skill checklists directly |

### Footer / Guardrails
- ✅ **Read-only** — never signs, deploys, or sends transactions
- ✅ Audit only contracts you own or are authorized to review
- ⚠️ Heuristic hits are **leads, not verdicts** — always confirm
- ⚠️ **Not financial advice** — technical risk ≠ investment call
- 🔗 **github.com/dharaemon/chainsentinel**

### Key Stat Callouts (big-number tiles)
- **1** command to set up
- **5** steps per scan
- **20** exploit classes checked
- **8** chains supported (BSC, ETH, Polygon, Arbitrum, Base, Optimism, Avalanche, BSC-testnet)
- **3** AI backends (Claude / Codex / ChatGPT)
