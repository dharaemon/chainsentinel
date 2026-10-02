"""Block-explorer (Etherscan V2 unified) client for verified source + ABI."""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
import urllib.error
from dataclasses import dataclass, field


class ExplorerError(RuntimeError):
    pass


@dataclass
class SourceResult:
    verified: bool = False
    contract_name: str = ""
    compiler_version: str = ""
    optimization: str = ""
    license: str = ""
    proxy_flag: str = ""          # explorer's own "Proxy" flag ("1"/"0")
    implementation: str = ""      # explorer's recorded implementation (if any)
    abi: str = ""
    files: dict[str, str] = field(default_factory=dict)   # path -> solidity source
    raw_source: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def combined_source(self) -> str:
        if self.files:
            parts = []
            for path, src in self.files.items():
                parts.append(f"// ===== FILE: {path} =====\n{src}")
            return "\n\n".join(parts)
        return self.raw_source


class Explorer:
    def __init__(self, api_base: str, chain_id: int, api_key: str, timeout: int = 30):
        self.api_base = api_base
        self.chain_id = chain_id
        self.api_key = api_key
        self.timeout = timeout

    def _get(self, params: dict) -> dict:
        params = {**params, "chainid": self.chain_id}
        if self.api_key:
            params["apikey"] = self.api_key
        url = self.api_base + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "ChainSentinel/0.1"})
        last_err = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode())
            except urllib.error.URLError as e:
                last_err = e
                time.sleep(1.5 * (attempt + 1))
        raise ExplorerError(f"Explorer request failed: {last_err}")

    def get_source(self, address: str) -> SourceResult:
        data = self._get(
            {"module": "contract", "action": "getsourcecode", "address": address}
        )
        result = SourceResult()
        if str(data.get("status")) != "1" or not data.get("result"):
            msg = data.get("result") or data.get("message") or "unknown error"
            result.notes.append(f"Explorer getsourcecode: {msg}")
            if "rate limit" in str(msg).lower() or "api key" in str(msg).lower():
                result.notes.append(
                    "Tip: set ETHERSCAN_API_KEY (free Etherscan V2 key works on all chains)."
                )
            return result

        entry = data["result"][0]
        src_field = entry.get("SourceCode", "") or ""
        result.contract_name = entry.get("ContractName", "")
        result.compiler_version = entry.get("CompilerVersion", "")
        result.optimization = entry.get("OptimizationUsed", "")
        result.license = entry.get("LicenseType", "")
        result.proxy_flag = entry.get("Proxy", "")
        result.implementation = entry.get("Implementation", "")
        result.abi = entry.get("ABI", "")

        if not src_field or src_field == "Contract source code not verified":
            result.verified = False
            result.notes.append("Source code is NOT verified on the explorer.")
            return result

        result.verified = True
        result.raw_source = src_field
        result.files = _parse_sources(src_field)
        return result


def _parse_sources(src_field: str) -> dict[str, str]:
    """Etherscan returns one of:
    - a single flat source string, or
    - a JSON standard-input object (sometimes double-wrapped in {{ }}).
    """
    s = src_field.strip()
    files: dict[str, str] = {}
    if s.startswith("{"):
        # Handle the double-brace wrapping Etherscan uses for standard-json input.
        candidate = s
        if s.startswith("{{") and s.endswith("}}"):
            candidate = s[1:-1]
        try:
            obj = json.loads(candidate)
        except json.JSONDecodeError:
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                return {"Contract.sol": src_field}
        sources = obj.get("sources", obj)
        if isinstance(sources, dict):
            for path, body in sources.items():
                if isinstance(body, dict) and "content" in body:
                    files[path] = body["content"]
                elif isinstance(body, str):
                    files[path] = body
        if files:
            return files
    return {"Contract.sol": src_field}
