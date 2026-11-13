"""Bounded public HTTPS only. Default TLS/proxy trust is preserved."""
from dataclasses import dataclass
from email.utils import format_datetime, parsedate_to_datetime
from datetime import timezone
import json
import time
import urllib.error
import urllib.request

from .contracts import ContractError, digest, now_utc

ENDPOINTS = {
    "basis": "https://www.basischarts.com/api/mcp",
    "binance_inventory": "https://fapi.binance.com/fapi/v1/exchangeInfo",
    "binance_ticker": "https://fapi.binance.com/fapi/v1/ticker/24hr",
    "binance_book": "https://fapi.binance.com/fapi/v1/ticker/bookTicker",
    "binance_premium": "https://fapi.binance.com/fapi/v1/premiumIndex",
}
MAX_BYTES = 2 * 1024 * 1024
MCP_READ_TOOLS = frozenset({"catalog_search", "catalog_describe", "market_candles",
                            "formula_evaluate", "screener_run"})


class ProviderError(ContractError):
    def __init__(self, code, receipt=None):
        super().__init__(code)
        self.receipt = receipt or {}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass
class Response:
    body: bytes
    headers: dict
    receipt: dict


def safe_retry_after(value):
    """Keep only valid HTTP delay/date syntax, never arbitrary header text."""
    if not isinstance(value, str) or len(value) > 128:
        return None
    value = value.strip()
    if value.isascii() and value.isdigit():
        return str(int(value))
    try:
        parsed = parsedate_to_datetime(value)
        return format_datetime(parsed.astimezone(timezone.utc), usegmt=True) if parsed.tzinfo else None
    except (ValueError, TypeError, OverflowError):
        return None


class PublicHTTP:
    def __init__(self, *, max_requests=8, timeout=25, opener=None):
        if not 1 <= max_requests <= 80 or not 1 <= timeout <= 35:
            raise ContractError("BOUNDED_HTTP_REQUIRED")
        self.remaining = max_requests
        self.timeout = timeout
        self.opener = opener or urllib.request.build_opener(NoRedirect())
        self.stopped = set()
        self.receipts = []

    def request(self, endpoint, *, payload=None, headers=None):
        if endpoint not in ENDPOINTS or endpoint in self.stopped:
            raise ProviderError("ROUTE_DISABLED")
        if self.remaining <= 0:
            raise ProviderError("REQUEST_BUDGET_EXHAUSTED")
        if (endpoint == "basis") != (payload is not None):
            raise ProviderError("PUBLIC_METHOD_REJECTED")
        if endpoint == "basis":
            if (not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0"
                    or payload.get("method") not in {"initialize", "notifications/initialized", "tools/list", "tools/call"}):
                raise ProviderError("MCP_METHOD_NOT_ALLOWED")
            if payload["method"] == "tools/call" and payload.get("params", {}).get("name") not in MCP_READ_TOOLS:
                raise ProviderError("MCP_TOOL_NOT_ALLOWED")
        self.remaining -= 1
        allowed_headers = {"Accept", "Content-Type", "MCP-Protocol-Version", "Mcp-Session-Id"}
        if set(headers or {}) - allowed_headers:
            raise ProviderError("AUTH_OR_HEADER_REJECTED")
        data = json.dumps(payload, allow_nan=False).encode() if payload is not None else None
        req = urllib.request.Request(ENDPOINTS[endpoint], data=data, headers=headers or {},
                                     method="POST" if data is not None else "GET")
        started = time.monotonic()
        try:
            response = self.opener.open(req, timeout=self.timeout)
        except urllib.error.HTTPError as error:
            response = error
        except (OSError, ValueError):
            response = None
        try:
            if response is None:
                raise OSError()
            with response:
                body = response.read(MAX_BYTES + 1)
                status = response.code
                private_headers = {k.lower(): v for k, v in response.headers.items()}
        except OSError:
            receipt = {"endpoint": ENDPOINTS[endpoint], "http_status": None,
                       "received_at_utc": now_utc(), "response_bytes": None,
                       "response_sha256": None, "elapsed_ms": round((time.monotonic() - started) * 1000),
                       "retry_after": None, "quota_charged_units": None}
            self.receipts.append(receipt)
            raise ProviderError("NETWORK_OR_TLS_FAILURE", receipt) from None
        receipt = {"endpoint": ENDPOINTS[endpoint], "http_status": status,
                   "received_at_utc": now_utc(), "response_bytes": len(body),
                   "response_sha256": digest(body),
                   "elapsed_ms": round((time.monotonic() - started) * 1000),
                   "retry_after": safe_retry_after(private_headers.get("retry-after")),
                   "quota_charged_units": None}
        self.receipts.append(receipt)
        if len(body) > MAX_BYTES:
            raise ProviderError("RESPONSE_SIZE_LIMIT", receipt)
        if status in {403, 429, 451}:
            self.stopped.add(endpoint)
            if endpoint.startswith("binance_"):
                self.stopped.update(e for e in ENDPOINTS if e.startswith("binance_"))
        if not 200 <= status < 300:
            raise ProviderError(f"HTTP_{status}", receipt)
        return Response(body, private_headers, receipt)
