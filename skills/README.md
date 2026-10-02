# ChainSentinel Skills

These are [Claude Code skills](https://docs.claude.com/en/docs/claude-code/skills)
(also loadable by other agents as structured prompts) that drive the AI side of an
audit. The tool gathers evidence; the skills tell the model how to judge it.

## Layout
- **`chainsentinel-setup/`** — bootstrap skill. Initialises and starts up the repo in
  any agent (Claude Code or ChatGPT Codex): clone, venv, deps, `.env`, tests, live check.
- **`smart-contract-audit/`** — master orchestrator. Start here for an audit. It runs
  ChainSentinel, resolves the proxy first, then dispatches to each exploit-class skill.
- One skill per exploit class, mapped from `data/taxonomy.yaml`:

| Skill | Covers |
|---|---|
| `proxy-resolution` | Proxy detection, implementation resolution, upgrade authority (**run first**) |
| `reentrancy-review` | All reentrancy variants |
| `access-control-review` | Authorization + initialization |
| `oracle-price-review` | Price oracles + flash loans |
| `arithmetic-review` | Overflow/rounding/casting |
| `amm-liquidity-review` | AMM/vault-share/donation attacks |
| `token-standard-review` | ERC-20/BEP-20 handling |
| `vault-lending-review` | Lending/staking/vault logic |
| `governance-review` | DAO/governor/timelock |
| `signature-review` | ECDSA/EIP-712/Merkle |
| `randomness-review` | PRNG/VRF |
| `dos-review` | Denial of service |
| `external-call-review` | Low-level calls/delegatecall |
| `storage-review` | Assembly/storage/layout |
| `business-logic-review` | Invariants/edge cases |
| `bridge-review` | Cross-chain/bridges |
| `rugpull-honeypot-review` | Malicious-admin/honeypot traits |

## Installing for Claude Code
Symlink or copy into your skills directory so Claude Code discovers them:

```bash
# project-scoped
mkdir -p .claude/skills
cp -R skills/* .claude/skills/

# or user-scoped (available in every project)
cp -R skills/* ~/.claude/skills/
```

Then in Claude Code: give it an address and say "audit this contract", or invoke
`/smart-contract-audit <address>`.

## Using with Codex / ChatGPT
The skills are plain Markdown. Either:
- run `chainsentinel audit <addr> --ai none`, then paste the generated `*.prompt.md`
  plus the relevant `SKILL.md` into your assistant, or
- run `--ai codex` / `--ai openai` to have the tool call the model for you.
