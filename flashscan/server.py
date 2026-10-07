"""Local web UI + JSON API.

    python -m flashscan.server [--port 8765] [--host 127.0.0.1]

Then open the printed URL. The page calls GET /api/scan and renders the result.
Everything runs locally; no data leaves your machine except the JSON-RPC reads
to the Ethereum endpoint you configure.
"""

from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import config
from .scanner import scan

WEB_DIR = os.path.join(os.path.dirname(__file__), "web")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quieter console
        pass

    def handle_one_request(self):
        # The browser aborting a slow request (refresh / new scan) raises a
        # connection error here; swallow it instead of dumping a traceback.
        try:
            super().handle_one_request()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            self.close_connection = True

    def _send(self, code: int, body: bytes, ctype: str):
        try:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            self.close_connection = True  # client went away mid-reply; ignore

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            return self._serve_file("index.html", "text/html; charset=utf-8")
        if parsed.path == "/api/config":
            payload = {
                "chains": [
                    {"name": c.name, "label": c.label, "chain_id": c.chain_id,
                     "explorer": c.explorer, "dexes": [d.name for d in c.dexes]}
                    for c in config.CHAINS.values()
                ],
                "default_chain": config.DEFAULT_CHAIN,
                "premium_bps": config.AAVE_PREMIUM_BPS_DEFAULT,
                "gas_units": config.GAS_UNITS_DEFAULT,
            }
            return self._send(200, json.dumps(payload).encode(), "application/json")
        if parsed.path == "/api/scan":
            return self._api_scan(parse_qs(parsed.query))
        if parsed.path == "/api/plan":
            return self._api_plan(parse_qs(parsed.query))
        return self._send(404, b"not found", "text/plain")

    def _serve_file(self, name: str, ctype: str):
        path = os.path.join(WEB_DIR, name)
        try:
            with open(path, "rb") as f:
                self._send(200, f.read(), ctype)
        except FileNotFoundError:
            self._send(404, b"not found", "text/plain")

    def _api_scan(self, q: dict):
        demo = q.get("demo", ["0"])[0] in ("1", "true", "yes")
        rpc_url = q.get("rpc", [None])[0] or None
        chain = q.get("chain", ["ethereum"])[0] or "ethereum"
        try:
            premium = int(q.get("premium_bps", [config.AAVE_PREMIUM_BPS_DEFAULT])[0])
            gas_units = int(q.get("gas_units", [config.GAS_UNITS_DEFAULT])[0])
            amount_usd = float(q.get("amount_usd", ["0"])[0] or 0)
        except ValueError:
            return self._send(400, b'{"error":"bad params"}', "application/json")
        try:
            result = scan(rpc_url=rpc_url, demo=demo, premium_bps=premium, gas_units=gas_units,
                          chain=chain, amount_usd=amount_usd)
        except Exception as e:  # noqa: BLE001
            result = {"meta": {}, "rows": [], "error": str(e)}
        self._send(200, json.dumps(result).encode(), "application/json")

    def _api_plan(self, q: dict):
        """Return the best executable plan + calldata + a wallet tx object."""
        from .execution import planner
        from .execution.abi import calldata_hex, Hop
        demo = q.get("demo", ["0"])[0] in ("1", "true", "yes")
        rpc_url = q.get("rpc", [None])[0] or None
        arb = q.get("arb", [None])[0] or None
        chain = q.get("chain", ["ethereum"])[0] or "ethereum"
        try:
            premium = int(q.get("premium_bps", [config.AAVE_PREMIUM_BPS_DEFAULT])[0])
            gas_units = int(q.get("gas_units", [config.GAS_UNITS_DEFAULT])[0])
            slippage = int(q.get("slippage_bps", [50])[0])
            amount_usd = float(q.get("amount_usd", ["0"])[0] or 0)
        except ValueError:
            return self._send(400, b'{"error":"bad params"}', "application/json")
        try:
            if demo:
                plan = planner.find_best_demo(premium, gas_units, slippage, amount_usd=amount_usd)
            else:
                plan = planner.find_best_live(rpc_url, premium, gas_units, slippage, chain=chain, amount_usd=amount_usd)
        except Exception as e:  # noqa: BLE001
            return self._send(200, json.dumps({"error": str(e)}).encode(), "application/json")
        if plan is None:
            return self._send(200, json.dumps({"error": "no cycle found"}).encode(), "application/json")
        hops = [Hop(**h) for h in [h.__dict__ for h in plan.hops]]
        data = calldata_hex(plan.asset, plan.amount, hops)
        tx = {"to": arb, "data": data, "value": "0x0"} if arb else None
        self._send(200, json.dumps({"plan": plan.to_dict(), "calldata": data, "tx": tx}).encode(),
                   "application/json")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="flashscan.server")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    args = p.parse_args(argv)
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}/"
    print(f"flashscan web UI → {url}  (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
