"""Bridge the evidence bundle to an AI reviewer.

Three modes:
  - claude : shell out to the `claude` CLI in headless mode (`claude -p`).
  - codex  : shell out to the `codex exec` CLI.
  - openai : POST to the OpenAI-compatible chat completions API (needs OPENAI_API_KEY).
  - none   : skip the live call; just write the prompt bundle to disk so the user
             can paste it into any assistant.

The prompt instructs the model to confirm/deny each heuristic lead using the
matching skill file, so the AI does the judgment while the tool does the evidence
gathering.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.request
import urllib.error


SYSTEM_INSTRUCTIONS = """\
You are a senior smart-contract security auditor performing a DEFENSIVE review of a
PUBLIC, already-deployed contract. Your job is to find and explain vulnerabilities so
they can be fixed or avoided - not to weaponize them.

You are given:
  1. Contract metadata (chain, address, proxy status, compiler).
  2. The verified source (or bytecode notes if unverified).
  3. Heuristic leads and any static-analysis findings, each tagged with an exploit
     category and the name of a skill file describing how to review that category.

For EACH exploit category with leads, work through the matching skill's checklist and:
  - State whether a real vulnerability is present: CONFIRMED / LIKELY / UNLIKELY / N/A.
  - Give the precise function + line, the exploit path (attacker steps), and impact.
  - Give a concrete remediation.
Be rigorous about false positives: a heuristic hit is only a lead. Downgrade leads
that are already mitigated (e.g. nonReentrant guard present, SafeERC20 used).
Finish with a prioritized summary table (severity, category, location, status).
"""


def build_prompt(bundle: dict) -> str:
    meta = bundle["meta"]
    header = [
        "# ChainSentinel evidence bundle",
        f"Chain: {meta['chain']} (id {meta['chain_id']})",
        f"Address: {meta['address']}",
        f"Explorer: {meta['explorer_web']}/address/{meta['address']}",
    ]
    proxy = bundle["proxy"]
    header.append(f"Proxy: {proxy['is_proxy']} ({proxy.get('proxy_type')})")
    if proxy.get("implementation"):
        header.append(f"Implementation audited: {proxy['implementation']}")
    header.append(f"Verified source: {bundle['meta'].get('verified')}")

    leads_lines = ["\n## Heuristic leads & static findings (category -> skill)"]
    for f in bundle["findings"]:
        loc = f"{f['file']}:{f['line']}" if f.get("file") else "-"
        leads_lines.append(
            f"- [{f['severity']}] ({f['source']}) {f['category']} @ {loc}: "
            f"{f['title']} | {f['detail']} "
            f"{'=> skill: ' + f['skill'] if f.get('skill') else ''}"
        )

    src_section = ["\n## Verified source"]
    for path, code in bundle.get("source_files", {}).items():
        src_section.append(f"\n### FILE: {path}\n```solidity\n{code}\n```")

    return "\n".join(
        [SYSTEM_INSTRUCTIONS, "\n".join(header), "\n".join(leads_lines), "\n".join(src_section)]
    )


def run_claude(prompt: str, timeout: int = 1200) -> str:
    if not shutil.which("claude"):
        raise RuntimeError("`claude` CLI not found on PATH.")
    proc = subprocess.run(
        ["claude", "-p", prompt],
        capture_output=True, text=True, timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude CLI failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def run_codex(prompt: str, timeout: int = 1200) -> str:
    if not shutil.which("codex"):
        raise RuntimeError("`codex` CLI not found on PATH.")
    proc = subprocess.run(
        ["codex", "exec", prompt],
        capture_output=True, text=True, timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"codex CLI failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def run_openai(prompt: str, model: str = "gpt-4o", timeout: int = 300) -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set.")
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    payload = json.dumps({
        "model": os.environ.get("OPENAI_MODEL", model),
        "messages": [
            {"role": "system", "content": SYSTEM_INSTRUCTIONS},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
    }).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        raise RuntimeError(f"OpenAI request failed: {e}") from e
    return data["choices"][0]["message"]["content"]


def review(prompt: str, provider: str) -> str:
    provider = (provider or "none").lower()
    if provider == "claude":
        return run_claude(prompt)
    if provider == "codex":
        return run_codex(prompt)
    if provider in ("openai", "chatgpt"):
        return run_openai(prompt)
    raise ValueError(f"Unknown AI provider: {provider}")
