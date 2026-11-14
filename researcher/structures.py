"""Causal selected-symbol reconstruction; no broad local detector engine.

Trial predicates implement blueprint §§7–9 formation facts. No readiness,
profitability, hidden liquidity, institution or order-execution claims.
"""
from dataclasses import dataclass, asdict
from decimal import Decimal as D
import json
import sqlite3
from pathlib import Path
from functools import cached_property
from .contracts import ContractError, digest, encode, symbol, utc
from .numerics import (validate_bars, confirmed_swings, swing_ladder, wilder_atr,
                       displacement, efficiency, compression, distance)

VERSION="causal-trial-3.0.0"
REFERENCE_KINDS={"SWING_HIGH","SWING_LOW","RANGE_TOP","RANGE_BOTTOM","DAILY_HIGH","DAILY_LOW",
                 "WEEKLY_HIGH","WEEKLY_LOW","FVG_CANDIDATE","IFVG_CANDIDATE","CRT_CANDLE",
                 "SUPPLY_DEMAND_CANDIDATE","ORDER_BLOCK_CANDIDATE","BREAKER_CANDIDATE",
                 "SESSION_VWAP_ANCHOR","EVENT_VWAP_ANCHOR","SHOCK_BOUNDARY",
                 "EQH_POOL_INFERRED","EQL_POOL_INFERRED","TRUE_VA_EDGE","TRUE_POC",
                 "TRUE_HVN_LVN","PROFILE_PROXY_LEVEL"}


def stable_id(*parts):
    return digest(encode(parts).encode())


@dataclass(frozen=True)
class Reference:
    native_symbol: str
    timeframe: str
    kind: str
    lo: D
    hi: D
    atr: D
    tick: D
    direction: int
    created_at: str
    known_at: str
    available_at: str
    valid_until: str
    source_ids: tuple[str,...]
    origin: str
    fidelity: str="OBSERVABLE_PRICE_GEOMETRY"

    def __post_init__(self):
        from .contracts import number
        from .observations import WIDTHS
        symbol(self.native_symbol)
        if (self.timeframe not in WIDTHS or self.kind not in REFERENCE_KINDS or self.direction not in {-1,1}
                or self.lo>self.hi or not self.source_ids or not self.origin):
            raise ContractError("REFERENCE_IDENTITY_OR_BOUNDS")
        for x in (self.lo,self.hi,self.atr,self.tick):number(x,positive=True)
        if not utc(self.created_at)<=utc(self.known_at)<=utc(self.available_at)<=utc(self.valid_until):
            raise ContractError("REFERENCE_CAUSAL_TIME")

    @cached_property
    def id(self):
        identity=asdict(self)
        for field in ('available_at','atr','tick'):
            identity.pop(field)  # Reuse original frozen scale on later retrieval.
        return stable_id(VERSION,identity)

    @property
    def buffer(self):
        return max(2*self.tick,D("0.15")*self.atr)


@dataclass(frozen=True)
class StructuralEvent:
    reference_id: str
    kind: str
    occurred_from: str
    occurred_to: str
    known_at: str
    available_at: str
    source_ids: tuple[str,...]
    direction: int
    evidence: str
    formula_version: str=VERSION

    def __post_init__(self):
        if not (utc(self.occurred_from)<utc(self.occurred_to)<=utc(self.known_at)<=utc(self.available_at)):
            raise ContractError("EVENT_CAUSAL_TIME")
        if not self.reference_id or not self.source_ids:raise ContractError("EVENT_SOURCE_REQUIRED")

    @cached_property
    def id(self):
        identity=asdict(self)
        identity.pop('available_at')
        return stable_id(identity)


def event(ref,bar,kind,*,evidence="CLOSED_BAR_GEOMETRY; INTRABAR_PATH_UNKNOWN"):
    from .observations import iso_seconds
    return StructuralEvent(ref.id,kind,iso_seconds(bar.open_ms//1000),bar.end,bar.end,
        max((ref.available_at,bar.available_at or bar.received_at),key=utc),
        (bar.id,*ref.source_ids),ref.direction,evidence)


def visible_bars(bars,as_of):
    validate_bars(bars)
    selected=[b for b in bars if utc(b.end)<=utc(as_of)
              and (not b.available_at or utc(b.available_at)<=utc(as_of))]
    if selected:validate_bars(selected)  # Delayed publication cannot hide a middle gap.
    return selected


def boundary_events(ref,bars,*,as_of):
    """Mirror upper/lower reference state machines. References never roll.

    Two independent touch episodes establish trial pressure. F2 requires this
    pressure, a close outside and two *later* outside bars. F5 requires a true
    reclaim, a later opposing attempt, a later rebreak, then two later holds.
    """
    bars=visible_bars(bars,as_of)
    if utc(ref.available_at)>utc(as_of):return {"reference_id":ref.id,"events":[],"hypotheses":[],"status":"NOT_AVAILABLE"}
    if any(b.native_symbol!=ref.native_symbol or b.timeframe!=ref.timeframe for b in bars):
        raise ContractError("REFERENCE_BAR_IDENTITY")
    events=[];active=True;armed=True;touches=0;pressure=False;excursion=None
    reclaim=None;opposing=None;break_bar=None;branch=None;holds=0;last=None
    support={"F2":[],"F4":[],"F5":[],"F6":[],"NULL":[]}
    contradiction={k:[] for k in support}
    def emit(b,kind):
        e=event(ref,b,kind);events.append(e);return e.id
    for b in bars:
        # No event may use a reference that was confirmed during this candle.
        if utc(ref.known_at).timestamp()*1000>b.open_ms:continue
        if utc(b.end)>utc(ref.valid_until):
            emit(b,"EXPIRED");active=False;break
        upper=ref.direction==1
        outside=b.close>ref.hi+ref.buffer if upper else b.close<ref.lo-ref.buffer
        inside=b.close<ref.lo-ref.buffer if upper else b.close>ref.hi+ref.buffer
        pierced=b.high>ref.hi+ref.buffer if upper else b.low<ref.lo-ref.buffer
        touched=b.high>=ref.lo-ref.buffer and b.low<=ref.hi+ref.buffer
        if touched and armed:
            touches+=1;armed=False;emit(b,"TOUCH_EPISODE")
            if touches>=2 and not pressure and not pierced:
                support["F2"].append(emit(b,"PRESSURE"));pressure=True
        elif not touched and max(ref.lo-b.high,b.low-ref.hi,D(0))>=D("0.5")*ref.atr:
            armed=True
        if pierced and excursion is None:
            excursion=b;emit(b,"WICK_EXCURSION")
        if excursion is not None and inside and reclaim is None:
            reclaim=b;holds=0;break_bar=None;branch=None
            rid=emit(b,"RECLAIM");support["F4"].append(rid);support["F6"].append(rid)
            contradiction["F2"].append(rid)
        elif reclaim is not None and b.open_ms>reclaim.open_ms and inside and opposing is None:
            progress=ref.direction*(reclaim.close-b.close)
            if progress>=D("0.25")*ref.atr:
                opposing=b;support["F5"].append(emit(b,"OPPOSING_ATTEMPT"))
                if last:
                    d=displacement(last,b,ref.atr,ref.tick)
                    if d["tr_atr_previous"]>=D("1.2") and d["body_fraction"]>=D("0.5"):
                        support["F4"].append(emit(b,"OPPOSING_INITIATIVE"))
        if outside and break_bar is None:
            if reclaim is None:
                break_bar=b;branch="F2";holds=0
                support["F2"].append(emit(b,"CLOSE_OUTSIDE"))
            elif opposing is not None and b.open_ms>opposing.open_ms:
                break_bar=b;branch="F5";holds=0
                fid=emit(b,"FAILED_RECLAIM");contradiction["F4"].append(fid)
                support["F5"].append(emit(b,"REBREAK_SAME_REFERENCE"))
        elif break_bar is not None and b.open_ms>break_bar.open_ms:
            if outside:
                holds+=1
                if holds==2:
                    eid=emit(b,"OUTSIDE_HOLD");support[branch].append(eid)
                    contradiction["F4"].append(eid);contradiction["F6"].append(eid)
            else:
                if holds>=2:
                    eid=emit(b,"ACCEPTANCE_FAILED");contradiction[branch].append(eid)
                holds=0;break_bar=None;branch=None
        last=b
    kinds={e.id:e.kind for e in events}
    hypotheses=[]
    for family in support:
        ids=support[family]
        supported=(family=="F2" and pressure and any(kinds[i]=="OUTSIDE_HOLD" for i in ids)
                   or family=="F4" and any(kinds[i]=="OPPOSING_INITIATIVE" for i in ids)
                   or family=="F5" and any(kinds[i]=="OUTSIDE_HOLD" for i in ids))
        verdict="CONTRADICTED" if contradiction[family] else "SUPPORTED" if supported else "UNKNOWN"
        hypotheses.append({"id":stable_id(ref.id,family),"family":family,"reference_id":ref.id,
            "current_formation_verdict":verdict,"supporting_ids":ids,"contradicting_ids":contradiction[family],
            "rivals":[stable_id(ref.id,f) for f in support if f!=family],
            "stage":"INVALIDATED" if not active else "DEVELOPING" if ids else "UNKNOWN",
            "unknowns":["ROOM_AND_ECONOMICS_NOT_EVALUATED","FUTURE_OUTCOME_UNKNOWN"]+
                       (["PRICE_ONLY_BALANCE_NOT_ESTABLISHED"] if family=="F6" else []),
            "next_discriminator":"Later closed response to the same valid frozen reference",
            "evidence_cluster":"PRICE_PATH","production_enabled":False})
    return {"reference_id":ref.id,"status":"ACTIVE" if active else "EXPIRED",
            "events":[{**asdict(e),"id":e.id} for e in events],"hypotheses":hypotheses,
            "as_of":as_of,"reconstruction":"RETROSPECTIVE_SELECTED_SAMPLE; NOT_PROSPECTIVE_NOMINATION"}


def swing_references(bars,tick,*,as_of,ttl_seconds=7*86400):
    from datetime import timedelta
    from .observations import iso_seconds
    bars=visible_bars(bars,as_of)
    if len(bars)<15:return []
    atr=wilder_atr(bars)
    refs=[]
    for s in confirmed_swings(bars):
        k=s["known_index"]
        if atr[k] is None or atr[k]<=0:continue
        b=bars[k];p=bars[s["index"]]
        available=b.available_at or b.received_at
        expires=(utc(b.end)+timedelta(seconds=ttl_seconds)).isoformat()
        if utc(available)>utc(expires):continue
        refs.append(Reference(b.native_symbol,b.timeframe,s["kind"],s["price"],s["price"],atr[k],tick,
            1 if s["kind"]=="SWING_HIGH" else -1,iso_seconds(p.open_ms//1000),b.end,
            available,expires,(s["pivot_bar_id"],b.id),s["id"]))
    return refs


def equal_level_references(bars,tick,*,as_of):
    """Selected EQH/EQL trial: two confirmed pivots plus an actual retreat.

    Freeze the first pivot's known ATR; cluster birth is the second pivot's
    confirmation. These are inferred price-sensitive levels, never stop prints.
    """
    from datetime import timedelta
    from .observations import iso_seconds
    bars=visible_bars(bars,as_of)
    if len(bars)<15:return []
    atr=wilder_atr(bars);swings=confirmed_swings(bars);result=[]
    for j,second in enumerate(swings):
        prior=[s for s in swings[:j] if s['kind']==second['kind']]
        for first in reversed(prior):
            scale=atr[first['known_index']]
            if scale is None or scale<=0:continue
            if abs(first['price']-second['price'])>max(2*tick,D('.15')*scale):continue
            between=bars[first['index']+1:second['index']]
            if not between:continue
            high=second['kind']=='SWING_HIGH'
            retreat=(min(first['price'],second['price'])-min(b.low for b in between) if high
                else max(b.high for b in between)-max(first['price'],second['price']))
            if retreat<D('.5')*scale:continue
            confirmation=bars[second['known_index']];until=(utc(confirmation.end)+timedelta(days=7)).isoformat()
            available=confirmation.available_at or confirmation.received_at
            if utc(available)>utc(until):continue
            result.append(Reference(confirmation.native_symbol,confirmation.timeframe,second['kind'],
                min(first['price'],second['price']),max(first['price'],second['price']),scale,tick,
                1 if high else -1,iso_seconds(bars[first['index']].open_ms//1000),confirmation.end,
                available,until,(first['pivot_bar_id'],bars[first['known_index']].id,second['pivot_bar_id'],confirmation.id),
                'EQH_EQL:'+stable_id(first['id'],second['id']),fidelity='INFERRED_LIQUIDITY_PRICE_GEOMETRY'))
            break
    return result


def swing_breaks(bars,tick,*,as_of):
    bars=visible_bars(bars,as_of)
    refs=swing_references(bars,tick,as_of=as_of)
    events=[];trend="UNKNOWN"
    swings=confirmed_swings(bars) if bars else []
    for b in bars:
        known=[s for s in swings if utc(s["known_at"]).timestamp()*1000<=b.open_ms]
        ladder=swing_ladder(known)
        if ladder in {"HH_HL","LH_LL"}:trend=ladder
        for r in refs:
            if (utc(r.known_at).timestamp()*1000>b.open_ms or utc(r.valid_until)<utc(b.end)
                    or any(e.reference_id==r.id for e in events)):continue
            broken=b.close>r.hi+r.buffer if r.direction==1 else b.close<r.lo-r.buffer
            if broken:
                opposing=(trend=="HH_HL" and r.direction==-1 or trend=="LH_LL" and r.direction==1)
                kind="CHOCH_CANDIDATE" if opposing else "BOS" if trend!="UNKNOWN" else "SWING_BREAK_UNCLASSIFIED"
                events.append(event(r,b,kind,evidence="PREKNOWN_SWING_BREAK; MSS_REQUIRES_CONTEXT"))
    return {"references":refs,"events":events}


def gap_lifecycle(bars,tick,*,as_of):
    from datetime import timedelta
    from .observations import iso_seconds
    bars=visible_bars(bars,as_of)
    gaps=[]
    for i in range(2,len(bars)):
        a,m,b=bars[i-2:i+1]
        direction=1 if b.low>a.high else -1 if b.high<a.low else 0
        if not direction:continue
        lo,hi=(a.high,b.low) if direction==1 else (b.high,a.low)
        available=b.available_at or b.received_at
        expires=(utc(b.end)+timedelta(days=7)).isoformat()
        if utc(available)>utc(expires):continue
        # ATR optional: a raw three-bar gap is distinguishable from meaningful displacement gap.
        atr=wilder_atr(bars[:i+1])[-1] if i>=14 else None
        ref=Reference(b.native_symbol,b.timeframe,"FVG_CANDIDATE",lo,hi,atr or tick,tick,direction,
            iso_seconds(a.open_ms//1000),b.end,available,expires,(a.id,m.id,b.id),stable_id(a.id,b.id,"FVG"))
        ev=[event(ref,b,"ZONE_BIRTH")];breach=None;consecutive=0;state="BORN"
        inverse=False;mitigated=D(0)
        for later in bars[i+1:]:
            if utc(later.end)>utc(expires):ev.append(event(ref,later,"EXPIRED"));state="EXPIRED";break
            touched=later.high>=lo and later.low<=hi
            penetration=max(D(0),min(later.high,hi)-max(later.low,lo))/(hi-lo)
            if touched and breach is None:
                mitigated=max(mitigated,penetration)
                ev.append(event(ref,later,"ZONE_MITIGATED"));state="MITIGATED"
            through=later.close<lo-ref.buffer if direction==1 else later.close>hi+ref.buffer
            if breach is None:
                consecutive=consecutive+1 if through else 0
                if consecutive==2:
                    breach=later;ev.append(event(ref,later,"ZONE_ACCEPTED_THROUGH"));state="INVALIDATED"
            elif later.open_ms>breach.open_ms and touched and through and not inverse:
                inverse=True;ev.append(event(ref,later,"IFVG_OPPOSITE_SIDE_RETEST"));state="IFVG_CANDIDATE"
            elif inverse and (later.close>hi+ref.buffer if direction==1 else later.close<lo-ref.buffer):
                ev.append(event(ref,later,"IFVG_INVALIDATED"));state="IFVG_INVALIDATED";break
        meaningful=False
        if atr and atr>0:
            dp=displacement(a,m, wilder_atr(bars[:i])[-2],tick) if i>=16 else None
            meaningful=bool(hi-lo>max(2*tick,D("0.1")*atr) and dp
                and dp["tr_atr_previous"]>=D("1.2") and dp["body_fraction"]>=D("0.5"))
        gaps.append({"reference":ref,"events":[{**asdict(e),"id":e.id} for e in ev],"status":state,
            "mitigation_fraction_max_bar_overlap":mitigated,"meaningful_displacement_subclass":meaningful,
            "institutional_intent":None,"production_enabled":False})
    return gaps


def formation_candidates(bars,tick,*,as_of):
    """F1/F3/F6 partial formation facts; never full readiness detectors."""
    bars=visible_bars(bars,as_of)
    if not bars:return []
    swings=confirmed_swings(bars);ladder=swing_ladder(swings)
    result=[]
    if ladder in {"HH_HL","LH_LL"}:
        direction=1 if ladder=="HH_HL" else -1
        ends=[s for s in swings if s["kind"]==("SWING_HIGH" if direction==1 else "SWING_LOW")]
        if ends:
            end=ends[-1];starts=[s for s in swings if s["index"]<end["index"] and s["kind"]!=end["kind"]]
            if starts and bars[-1].open_ms>bars[end["known_index"]].open_ms:
                start=starts[-1];amplitude=direction*(end["price"]-start["price"])
                rho=direction*(end["price"]-bars[-1].close)/amplitude if amplitude>0 else None
                impulse=bars[start["index"]:end["index"]+1];pullback=bars[end["known_index"]+1:]
                from statistics import median
                controlled=bool(pullback and D("0.15")<=rho<=D("0.70")
                    and median(b.high-b.low for b in pullback)<=median(b.high-b.low for b in impulse)
                    and all(direction*(b.close-start["price"])>0 for b in pullback)) if rho is not None else False
                result.append({"family":"F1","status":"PARTIAL_FORMATION","ladder":ladder,
                    "retracement":rho,"controlled_range_predicate":controlled,"impulse_known_at":end["known_at"],
                    "unknowns":["DEFENDED_ZONE_RESPONSE","FIRST_OPPOSING_OBSTACLE","ECONOMICS"],"production_enabled":False})
    try:
        before=compression(bars[:-1],tick=tick)
        atr=wilder_atr(bars)[-2]
        dp=displacement(bars[-2],bars[-1],atr,tick)
        result.append({"family":"F3","status":"PARTIAL_FORMATION","quiet_known_at":bars[-2].end,
            "quiet_percentile":before["past_percentile"],"displacement":dp,
            "quiet_then_expansion":before["past_percentile"]<=D("0.20") and dp["tr_atr_previous"]>=D("1.2"),
            "unknowns":["DECISION_REFERENCE","RETENTION","ROOM"],"production_enabled":False})
    except (ContractError,IndexError):
        result.append({"family":"F3","status":"INSUFFICIENT_HISTORY","production_enabled":False})
    result.append({"family":"F6","status":"PRICE_ONLY_PRIMITIVES","efficiency16":efficiency(bars) if len(bars)>16 else None,
        "unknowns":["PREDECLARED_BALANCE_BOUNDS","SEPARATED_EDGE_VISITS","ROTATION_RESPONSE"],
        "true_profile":False,"production_enabled":False})
    return result


def selected_family_facts(bars,tick,*,as_of,benchmark=None):
    """Source-backed, bounded F1/F3/F6/F7/F8/F9 watch evidence.

    Current historical reconstruction does not establish prospective discovery,
    first opposing room, profile/footprint or research admission economics.
    """
    from .numerics import anchored_value, lag_trained_beta, relative_return, overlap
    from statistics import median
    bars=visible_bars(bars,as_of)
    result=formation_candidates(bars,tick,as_of=as_of)
    if len(bars)<34:return result
    atr=wilder_atr(bars);last=bars[-1]
    # Actual quiet prefixes precede the displacement, with separate subsequent
    # retention observations. No current low-width flag used as a past state.
    expansions=[]
    for i in range(max(160,len(bars)-8),len(bars)):
        if atr[i-1] is None or atr[i-1]<=0:continue
        quiet=compression(bars[:i],tick=tick)
        dp=displacement(bars[i-1],bars[i],atr[i-1],tick)
        if quiet['past_percentile']<=D('.20') and dp['tr_atr_previous']>=D('1.2') and dp['body_fraction']>=D('.5'):
            direction=1 if bars[i].close>bars[i].open else -1
            retained=bool(bars[i+1:]) and all(direction*(b.close-bars[i].open)>0 for b in bars[i+1:])
            expansions.append({'quiet_known_at':bars[i-1].end,'displacement_known_at':bars[i].end,
                'retention_known_at':last.end if retained else None,'direction':direction,
                'quiet_percentile':quiet['past_percentile'],'displacement':dp,
                'retained':retained,'source_ids':[b.id for b in bars[i-1:]]})
    result.append({'family':'F3','status':'TARGETED_CHRONOLOGICAL_WATCH','expansions':expansions,
        'unknowns':['SIGNIFICANT_DECISION_REFERENCE','ROOM','ECONOMICS'],'production_enabled':False})
    prior=bars[-48:-16];hi=max(b.high for b in prior);lo=min(b.low for b in prior)
    scale=atr[-17];buffer=max(2*tick,D('.15')*scale)
    def episodes(edge):
        count=0;armed=True
        for b in prior:
            touch=b.high>=edge-buffer and b.low<=edge+buffer
            if touch and armed:count+=1;armed=False
            elif not touch and max(edge-b.high,b.low-edge,D(0))>=D('.5')*scale:armed=True
        return count
    er=efficiency(prior);visits=(episodes(lo),episodes(hi));balance=len(prior)==32 and er is not None and er<=D('.35') and min(visits)>=2
    result.append({'family':'F6','status':'PRICE_ONLY_BALANCE_WATCH','bounds':[lo,hi],
        'reference_known_at':prior[-1].end,'efficiency':er,'separated_visits':visits,'balance_supported':balance,
        'current_inside':lo<=last.close<=hi,'history_bars':len(prior),'true_profile':False,'production_enabled':False,
        'unknowns':['QUALIFIED_ROTATION_RESPONSE','FIRST_OBSTACLE','ECONOMICS']})
    day=utc(last.end).replace(hour=0,minute=0,second=0,microsecond=0)
    # If last close is midnight, its bar belongs to the prior UTC session.
    if int(day.timestamp()*1000)==last.end_ms:
        from datetime import timedelta
        day-=timedelta(days=1)
    session=[b for b in bars if b.open_ms>=int(day.timestamp()*1000)]
    if session and session[0].open_ms==int(day.timestamp()*1000):
        value=anchored_value(session,anchor_ms=session[0].open_ms,anchor_known_at=day.isoformat())
        result.append({'family':'F7','status':'TARGETED_WHOLE_BAR_SESSION_VALUE','anchor':day.isoformat(),
            'value':value,'extension_atr':(last.close-value['vwap_whole_bars'])/atr[-1] if value['vwap_whole_bars'] is not None and atr[-1]>0 else None,
            'true_profile':False,'true_weighted_variance':False,'production_enabled':False,
            'unknowns':['FAILED_DIRECTIONAL_ACCEPTANCE','CONDITIONAL_REVERSION','ROOM','ECONOMICS']})
    if benchmark is not None and len(benchmark)>=34:
        result.append({'family':'F8','status':'TARGETED_LAG_TRAINED_RELATIVE','benchmark':'BTCUSDT',
            'relative_log_return16':relative_return(bars,benchmark),
            'lag_trained':lag_trained_beta(bars,benchmark),'sector':'UNKNOWN_NO_DATED_MAPPING',
            'production_enabled':False,'unknowns':['PERSISTENCE','LOCAL_STRUCTURAL_CONSEQUENCE','ROOM','ECONOMICS']})
    shocks=[]
    for i in range(max(15,len(bars)-8),len(bars)):
        if atr[i-1] is None or atr[i-1]<=0:continue
        dp=displacement(bars[i-1],bars[i],atr[i-1],tick)
        if dp['tr_atr_previous']<3:continue
        later=bars[i+1:];stable=len(later)>=2 and all(b.high<=bars[i].high and b.low>=bars[i].low for b in later)
        shocks.append({'kind':'POST_SHOCK','known_at':bars[i].end,'source_id':bars[i].id,
            'tr_atr_previous':dp['tr_atr_previous'],'stabilization_supported':stable,
            'later_closed_bars':len(later),'confirmed_liquidation':False})
    result.append({'family':'F9','status':'TARGETED_POST_SHOCK_WATCH','shocks':shocks,'production_enabled':False,
        'unknowns':['COVERED_LIQUIDATIONS','CURRENT_DEPTH','ROOM','ECONOMICS']})
    return result


class ResearchLedger:
    """Append-only metadata/events; immutable snapshots and explicit lifecycle.

    No bar table. Identical writes are idempotent, conflicting IDs fail. SQLite
    transaction rolls back the entire batch on any causal/identity violation.
    """
    def __init__(self,path=":memory:"):
        if str(path)!=":memory:":
            from .settings import ROOT
            p=Path(path).absolute()
            if (not p.is_relative_to(ROOT/"work") or ".." in p.parts
                    or any(x.is_symlink() for x in [p,*p.parents])):
                raise ContractError("LEDGER_MUST_BE_UNDER_WORK")
            p.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(str(path),timeout=5)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS reference(id TEXT PRIMARY KEY, symbol TEXT NOT NULL, known_at TEXT NOT NULL, body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS event(id TEXT PRIMARY KEY, reference_id TEXT NOT NULL REFERENCES reference(id), known_at TEXT NOT NULL, body TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS event_reference_time ON event(reference_id,known_at);
            CREATE TABLE IF NOT EXISTS hypothesis(id TEXT PRIMARY KEY, reference_id TEXT NOT NULL REFERENCES reference(id), cutoff TEXT NOT NULL, body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS lifecycle(id TEXT PRIMARY KEY, reference_id TEXT NOT NULL REFERENCES reference(id), at TEXT NOT NULL, state TEXT NOT NULL);
        ''')
        self.db.commit()

    def close(self):self.db.close()

    def transaction(self):
        """Savepoints compose with an outer atomic run transaction."""
        from contextlib import contextmanager
        @contextmanager
        def savepoint():
            self.db.execute('SAVEPOINT research_metadata')
            try:
                yield
                self.db.execute('RELEASE SAVEPOINT research_metadata')
            except BaseException:
                self.db.execute('ROLLBACK TO SAVEPOINT research_metadata')
                self.db.execute('RELEASE SAVEPOINT research_metadata')
                raise
        return savepoint()

    def freeze_reference(self,ref):
        """Reuse the first recorded scale/availability for the same origin."""
        row=self.db.execute('SELECT body FROM reference WHERE id=?',(ref.id,)).fetchone()
        if not row:return ref
        raw=json.loads(row[0])
        for key in ('lo','hi','atr','tick'):raw[key]=D(raw[key])
        raw['source_ids']=tuple(raw['source_ids'])
        frozen=Reference(**raw)
        if frozen.id!=ref.id:raise ContractError('IMMUTABLE_LEDGER_CONFLICT')
        return frozen

    def _immutable(self,table,key,columns,values,body):
        row=self.db.execute(f"SELECT body FROM {table} WHERE id=?",(key,)).fetchone()
        if row:
            if row[0]!=body:
                old,new=json.loads(row[0]),json.loads(body)
                if table in {'reference','event'}:
                    earlier,later=old.pop('available_at'),new.pop('available_at')
                    if old==new and utc(later)>=utc(earlier):
                        return  # Preserve first recorded availability, never rewrite it.
                raise ContractError("IMMUTABLE_LEDGER_CONFLICT")
            return
        self.db.execute(f"INSERT INTO {table} (id,{columns},body) VALUES ({','.join('?' for _ in range(len(values)+2))})",
                        (key,*values,body))

    def record(self,ref,events,*,hypotheses=(),cutoff,snapshot_cutoff=None,allow_historical_insert=False):
        utc(cutoff)
        if utc(ref.available_at)>utc(cutoff):raise ContractError("REFERENCE_NOT_AVAILABLE")
        with self.transaction():
            self._immutable("reference",ref.id,"symbol,known_at",(ref.native_symbol,ref.known_at),encode(asdict(ref)))
            last=self.db.execute("SELECT max(known_at) FROM event WHERE reference_id=?",(ref.id,)).fetchone()[0]
            prior=utc(last) if last else utc(ref.known_at)
            for raw in events:
                e=raw if isinstance(raw,StructuralEvent) else StructuralEvent(**{k:v for k,v in raw.items() if k!="id"})
                existing=self.db.execute("SELECT 1 FROM event WHERE id=?",(e.id,)).fetchone()
                historical=(allow_historical_insert and utc(e.available_at)>prior)
                if (e.reference_id!=ref.id or utc(e.known_at)<utc(ref.known_at)
                        or utc(e.available_at)>utc(cutoff) or (not existing and utc(e.known_at)<prior and not historical)):
                    raise ContractError("LEDGER_NONCHRONOLOGICAL_EVENT")
                self._immutable("event",e.id,"reference_id,known_at",(ref.id,e.known_at),encode(asdict(e)))
                prior=max(prior,utc(e.known_at))
            for h in hypotheses:
                if h.get("reference_id")!=ref.id:raise ContractError("HYPOTHESIS_REFERENCE")
                claimed=set(h.get("supporting_ids",[])+h.get("contradicting_ids",[]))
                known={x[0] for x in self.db.execute("SELECT id FROM event WHERE reference_id=?",(ref.id,))}
                if not claimed<=known:raise ContractError("HYPOTHESIS_UNKNOWN_EVIDENCE")
                effective=snapshot_cutoff or cutoff
                utc(effective)
                key=stable_id(h["id"],effective)
                self._immutable("hypothesis",key,"reference_id,cutoff",(ref.id,effective),encode(h))

    def transition(self,ref,*,state,at):
        if state not in {"CONSUMED","INVALIDATED","EXPIRED"}:raise ContractError("REFERENCE_LIFECYCLE_STATE")
        if utc(at)<utc(ref.available_at):raise ContractError("REFERENCE_CAUSAL_TIME")
        if state=='EXPIRED' and utc(at)<utc(ref.valid_until):raise ContractError("REFERENCE_CAUSAL_TIME")
        previous=self.db.execute("SELECT max(at) FROM lifecycle WHERE reference_id=?",(ref.id,)).fetchone()[0]
        if previous and utc(at)<utc(previous):raise ContractError("LIFECYCLE_TIME_REGRESSION")
        with self.transaction():self.db.execute("INSERT OR IGNORE INTO lifecycle VALUES(?,?,?,?)",(stable_id(ref.id,state,at),ref.id,at,state))

    def active_references(self,at):
        utc(at)
        rows=self.db.execute("SELECT id,body FROM reference ORDER BY id").fetchall()
        result=[]
        for key,body in rows:
            r=json.loads(body)
            if utc(r["available_at"])<=utc(at)<=utc(r["valid_until"]):
                terminal=self.db.execute("SELECT at FROM lifecycle WHERE reference_id=?",(key,)).fetchall()
                if not any(utc(x[0])<=utc(at) for x in terminal):result.append(r)
        return result

    def counts(self):
        return {t:self.db.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                for t in ("reference","event","hypothesis","lifecycle")}
