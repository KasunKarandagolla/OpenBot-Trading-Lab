"""Live official public API on the operator's authorized, ordinary host.

One bounded transport; no auth, redirects, alternate hosts or route recovery.
Only current aggregate data and at most five selected-symbol history samples.
"""
import time
from .contracts import ContractError, digest, now_utc
from .inventory import OfficialBinanceInventory, json_document
from .market import normalize_market
from .numerics import parse_klines
from .transport import ProviderError, PublicHTTP


class CachedPublicHTTP:
    """Short in-memory reuse; configuration never contains API payloads."""
    def __init__(self,http=None,*,clock=time.monotonic):
        # Preserve managed-host transport/trust settings. Never change routes
        # or retry a denial; on hosts without a proxy this is the normal route.
        self.http=http or PublicHTTP(max_requests=20)
        self.clock=clock;self.cache={};self.cache_hits=0

    @property
    def receipts(self):return self.http.receipts

    def request(self,endpoint,*,query=None):
        key=(endpoint,tuple(sorted((query or {}).items())))
        now=self.clock()
        ttl=300 if endpoint=="binance_inventory" else 10 if query is None else 60
        if key in self.cache and now-self.cache[key][0]<ttl:
            self.cache_hits+=1;return self.cache[key][1]
        response=self.http.request(endpoint,**({"query":query} if query else {}))
        self.cache[key]=(self.clock(),response)
        return response


class OfficialResearchAPI:
    def __init__(self,http=None,*,access_denial=None):
        # A fresh authorized host probes its normal official route. Existing
        # recorded denials can still be supplied; never clear one within a run.
        self.http=CachedPublicHTTP(http)
        self.access_denial=access_denial
        self.sample_symbols=set()
        self.sample_calls=0

    def inventory(self):
        return OfficialBinanceInventory(self.http,access_denial=self.access_denial).load(now_utc())

    def pulse(self,inventory):
        if self.access_denial in {403,451}:raise ProviderError("RECORDED_BINANCE_ACCESS_DENIAL")
        out=[]
        for kind in ("ticker","book","premium"):
            response=self.http.request("binance_"+kind)
            out.append(normalize_market(json_document(response.body),kind=kind,inventory=inventory,
                captured_at=response.receipt["received_at_utc"],response_hash=digest(response.body)))
        return out

    def klines(self,instrument,*,timeframe,cutoff,bars=300):
        from .contracts import utc
        from .observations import WIDTHS
        if self.access_denial in {403,451}:raise ProviderError("RECORDED_BINANCE_ACCESS_DENIAL")
        if instrument.identity_status!="EXCHANGE_VERIFIED":raise ContractError("KLINES_REQUIRE_VERIFIED_IDENTITY")
        names=self.sample_symbols|{instrument.native_symbol}
        if len(names)>5 or self.sample_calls>=10:
            raise ContractError("SELECTED_SAMPLE_BUDGET_EXHAUSTED")
        if (timeframe not in WIDTHS or type(bars) is not int or not 1<=bars<=300
                or int(utc(cutoff).timestamp())%WIDTHS[timeframe]
                or utc(cutoff)>utc(now_utc())):
            raise ContractError("BOUNDED_CLOSED_SAMPLE_REQUIRED")
        self.sample_symbols=names;self.sample_calls+=1
        query={"symbol":instrument.native_symbol,"interval":timeframe,"limit":bars,
               "endTime":int(utc(cutoff).timestamp()*1000)-1}
        response=self.http.request("binance_klines",query=query)
        data=parse_klines(json_document(response.body),native_symbol=instrument.native_symbol,
            timeframe=timeframe,cutoff=cutoff,receipt=response.receipt,requested_bars=bars)
        return data,{"requested_bars":bars,"returned_bars":len(data),"native_symbol":instrument.native_symbol,
            "timeframe":timeframe,"cutoff":cutoff,"source_response_sha256":digest(response.body),
            "receipt":response.receipt,"closed_bar_semantics":"OPEN_MS; CLOSE_INCLUSIVE_END_MINUS_1MS",
            "units":"BASE_ASSET_AND_USDT_QUOTE","earliest_publication":"UNKNOWN"}
