"""Actual Streamable HTTP MCP client, deliberately limited to research reads."""
import json
from decimal import Decimal
from .contracts import ContractError, symbol
from .transport import MCP_READ_TOOLS, ProviderError, PublicHTTP

READ_TOOLS = MCP_READ_TOOLS
PROTOCOL = "2025-03-26"


def parse_json(body):
    def reject_constant(_):
        raise ProviderError("NONSTANDARD_JSON_NUMBER")
    try:
        return json.loads(body, parse_float=Decimal, parse_constant=reject_constant)
    except (ValueError, UnicodeError):
        raise ProviderError("MALFORMED_JSON") from None


def rpc_result(body, request_id):
    # Accept JSON and the data events of Streamable HTTP SSE. Never follow links.
    try:
        text = body.decode("utf-8")
    except UnicodeError:
        raise ProviderError("MALFORMED_JSON") from None
    if text.lstrip().startswith(("event:", "data:", ":")):
        messages = []
        for block in text.replace("\r\n", "\n").split("\n\n"):
            data = "\n".join(line[5:].lstrip() for line in block.splitlines() if line.startswith("data:"))
            if data:
                messages.append(parse_json(data))
        matches = [x for x in messages if isinstance(x, dict) and x.get("id") == request_id]
        if len(matches) != 1:
            raise ProviderError("MCP_SSE_ID_MISMATCH")
        envelope = matches[0]
    else:
        envelope = parse_json(body)
    if (not isinstance(envelope, dict) or envelope.get("jsonrpc") != "2.0"
            or envelope.get("id") != request_id):
        raise ProviderError("MCP_ENVELOPE_MISMATCH")
    if "error" in envelope or "result" not in envelope:
        raise ProviderError("MCP_RPC_ERROR")
    result = envelope["result"]
    if not isinstance(result, dict) or result.get("isError"):
        raise ProviderError("MCP_TOOL_ERROR")
    return result


def tool_object(result):
    if result.get("isError"):
        raise ProviderError("MCP_TOOL_ERROR")
    if isinstance(result.get("structuredContent"), dict):
        value = result["structuredContent"]
    else:
        values = []
        blocks = result.get("content", [])
        if not isinstance(blocks, list) or any(not isinstance(b, dict) for b in blocks):
            raise ProviderError("MCP_CONTENT_SCHEMA")
        for block in blocks:
            if block.get("type") != "text":
                continue
            try:
                candidate = parse_json(block.get("text", ""))
            except ProviderError:
                continue
            if isinstance(candidate, dict):
                values.append(candidate)
        if len(values) != 1:
            raise ProviderError("MCP_DATA_OBJECT_REQUIRED")
        value = values[0]
    if value.get("error") or value.get("isError"):
        raise ProviderError("MCP_TOOL_ERROR")
    return value


class BasisMCP:
    def __init__(self, http=None, *, qualification=False, session4=False, session5=False):
        self.http = http or PublicHTTP()
        self.session = None
        self.counter = 0
        self.tools = {}
        self.initialized = False
        self.qualification = qualification
        self.session4 = session4
        self.session5 = session5

    def _rpc(self, method, params, *, notification=False):
        self.counter += 1
        payload = {"jsonrpc": "2.0", "method": method, "params": params}
        if not notification:
            payload["id"] = self.counter
        headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
        if self.initialized:
            headers["MCP-Protocol-Version"] = PROTOCOL
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        response = self.http.request("basis", payload=payload, headers=headers)
        if method == "initialize":
            self.session = response.headers.get("mcp-session-id")
        if notification:
            if response.body:
                raise ProviderError("MCP_NOTIFICATION_BODY_UNEXPECTED")
            return {}
        return rpc_result(response.body, self.counter)

    def connect(self):
        result = self._rpc("initialize", {"protocolVersion": PROTOCOL, "capabilities": {},
                    "clientInfo": {"name": "openbot-readonly-research", "version": "0.1.0"}})
        if result.get("protocolVersion") != PROTOCOL or "tools" not in result.get("capabilities", {}):
            raise ProviderError("MCP_PROTOCOL_OR_CAPABILITY")
        self.initialized = True
        self._rpc("notifications/initialized", {}, notification=True)
        cursor = None
        for _ in range(3):
            result = self._rpc("tools/list", {"cursor": cursor} if cursor else {})
            listed = result.get("tools")
            if not isinstance(listed, list):
                raise ProviderError("MCP_TOOLS_SCHEMA")
            for tool in listed:
                if (not isinstance(tool, dict) or not isinstance(tool.get("name"), str)
                        or not isinstance(tool.get("inputSchema"), dict)
                        or not isinstance(tool.get("annotations", {}), dict)):
                    raise ProviderError("MCP_TOOLS_SCHEMA")
                if tool["name"] in READ_TOOLS:
                    if tool.get("annotations", {}).get("readOnlyHint") is not True:
                        raise ProviderError("READ_ONLY_ANNOTATION_CHANGED")
                    self.tools[tool["name"]] = tool
            cursor = result.get("nextCursor")
            if not cursor:
                return self.tools
            if not isinstance(cursor, str):
                raise ProviderError("MCP_CURSOR_SCHEMA")
        raise ProviderError("TOOLS_LIST_PAGINATION_LIMIT")

    def call(self, name, arguments):
        if not self.initialized or name not in READ_TOOLS or name not in self.tools:
            raise ProviderError("RESEARCH_TOOL_NOT_ALLOWED")
        schema = self.tools[name]["inputSchema"]
        if self.session5 and name=='formula_evaluate' and 'ref' not in arguments:
            raise ContractError('TARGETED_BOUNDED_REF_REQUIRED')
        if set(arguments) - set(schema.get("properties", {})) or not set(schema.get("required", [])) <= set(arguments):
            raise ContractError("TOOL_ARGUMENT_SCHEMA")
        if name in {"formula_evaluate", "screener_run"}:
            if not self.qualification:
                raise ContractError("UNQUALIFIED_OPERATION_USE_EXPLICIT_PROBE")
            from .settings import load_config
            specs = load_config()
            registered = {s["expression"] for s in specs["qualification_formulas"].values()}
            registered.add(specs["qualification_failure_expression"])
            if self.session4:
                from .precursors import FEATURES
                registered.update(f.expression for f in FEATURES.values())
            if self.session5:
                from .core import EXPRESSIONS
                registered.update(EXPRESSIONS)
            expressions = ([arguments["expression"]] if name == "formula_evaluate" else
                           [r.get("left", {}).get("expression") for r in arguments.get("rules", [])])
            if not expressions or any(e not in registered for e in expressions):
                raise ContractError("UNREGISTERED_FORMULA")
        if name in {"market_candles", "formula_evaluate", "screener_run"}:
            if name != "formula_evaluate" or "ref" not in arguments:
                if arguments.get("exchange") != "binance" or arguments.get("market") != "futures":
                    raise ContractError("EXPLICIT_SOURCE_REQUIRED")
            if "symbol" in arguments:
                symbol(arguments["symbol"])
            if "bars" in arguments and (type(arguments["bars"]) is not int or not 1 <= arguments["bars"] <= (300 if (self.session4 or self.session5) and self.qualification else 65)):
                raise ContractError("TARGETED_HISTORY_LIMIT")
            if name == "formula_evaluate" and arguments.get("includeForming") is not False:
                raise ContractError("CLOSED_FORMULA_REQUIRED")
            if name == "screener_run":
                if (arguments.get("universeSize") not in {20, 50} or arguments.get("quote") != "USDT"
                        or arguments.get("lookback") != 300 or arguments.get("limit") != 60):
                    raise ContractError("BOUNDED_SCREEN_PROBE_REQUIRED")
                names = arguments.get("manualSymbols", [])
                if not 1 <= len(names) <= 50 or len(set(names)) != len(names):
                    raise ContractError("EXPLICIT_BOUNDED_PARTITION_REQUIRED")
                for native in names:
                    symbol(native)
        result = self._rpc("tools/call", {"name": name, "arguments": arguments})
        return tool_object(result)
