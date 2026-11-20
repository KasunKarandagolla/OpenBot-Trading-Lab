"""Typed Session 4 research evidence. No execution or provider write surface."""
from dataclasses import dataclass
from decimal import Decimal
from .contracts import ContractError, Instrument, Fidelity, number, utc, digest, encode


@dataclass(frozen=True)
class Fact:
    id: str
    instrument: Instrument
    measurement: str
    value: object
    units: str
    timeframe: str
    window_end: str
    known_at: str
    available_at: str
    received_at: str
    source_id: str
    response_hash: str
    fidelity: str
    complete: bool
    qualification: str
    mode: str
    max_age_seconds: int
    verdict: str = 'SUPPORTED'
    reason: str | None = None
    cluster: str = 'PRICE_PATH'

    def __post_init__(self):
        Fidelity(self.fidelity)
        if (not all((self.id,self.measurement,self.units,self.source_id,self.response_hash))
                or self.qualification not in {'QUALIFIED','TRIAL','UNQUALIFIED'}
                or self.mode not in {'LIVE','AUTHENTIC_REPLAY','SYNTHETIC'}
                or self.verdict not in {'SUPPORTED','CONTRADICTED','UNKNOWN'}
                or type(self.complete) is not bool or type(self.max_age_seconds) is not int
                or self.max_age_seconds <= 0):
            raise ContractError('FACT_PROVENANCE')
        if not utc(self.window_end)<=utc(self.known_at)<=utc(self.available_at)<=utc(self.received_at):
            raise ContractError('CAUSAL_TIMESTAMP_ORDER')
        if self.value is None and (self.verdict != 'UNKNOWN' or not self.reason):
            raise ContractError('MISSING_VALUE_REQUIRES_REASON')
        if isinstance(self.value,(Decimal,int,float)) and not isinstance(self.value,bool): number(self.value)

    def usable(self, *, as_of, native_symbol=None, venue='BINANCE_USDM', units=None,
               qualified=False, cutoff=None):
        return (self.instrument.venue==venue
            and (native_symbol is None or self.instrument.native_symbol==native_symbol)
            and (units is None or self.units==units)
            and utc(self.received_at)<=utc(as_of)
            and 0<=(utc(as_of)-utc(self.window_end)).total_seconds()<=self.max_age_seconds
            and (cutoff is None or utc(self.window_end)==utc(cutoff))
            and self.complete and self.verdict=='SUPPORTED' and self.value is not None
            and (not qualified or self.qualification=='QUALIFIED'
                 and self.instrument.identity_status=='EXCHANGE_VERIFIED'
                 and self.instrument.captured_at_utc is not None
                 and 0<=(utc(as_of)-utc(self.instrument.captured_at_utc)).total_seconds()<=86400
                 and self.fidelity in {'EXACT_REPORTED','SYNCHRONIZED_REMOTE_RECONSTRUCTION'}))


def fact_id(*parts): return digest(encode(parts).encode())


def cited(ids, facts, *, as_of, native_symbol=None, qualified=False):
    return bool(ids) and all(i in facts and facts[i].usable(as_of=as_of,
        native_symbol=native_symbol,qualified=qualified) for i in ids)
