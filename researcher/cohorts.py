"""Independent quiet/medium cohort planning, usable only with verified inputs."""
from .contracts import ContractError, number, utc


def independent_tail_cohort(inventory, ticker, *, as_of, full_size=50, footer_size=7):
    """Freeze lower and medium liquidity members without a provider top board.

    This is a deterministic qualification cohort, not a strategy or an estimate
    of opportunity prevalence. Global direction is deliberately not an input.
    Young and multiplier members are included only when metadata supplies facts.
    """
    if (inventory.mode != "VERIFIED_INVENTORY" or ticker.get("kind") != "ticker"
            or type(full_size) is not int or not 1 <= full_size <= 50
            or type(footer_size) is not int or not 1 <= footer_size < full_size):
        raise ContractError("TAIL_REQUIRES_VERIFIED_INVENTORY_AND_LIQUIDITY")
    members = {i.native_symbol: i for i in inventory.instruments}
    if not 0 <= (utc(as_of) - utc(inventory.captured_at_utc)).total_seconds() <= inventory.max_age_seconds:
        raise ContractError("STALE_TAIL_INVENTORY")
    observations = ticker.get("observations", [])
    if (len({o["native_symbol"] for o in observations}) != len(observations)
            or any(o["source_scope"] != "OFFICIAL_BINANCE_USDM" for o in observations)):
        raise ContractError("TAIL_LIQUIDITY_SOURCE")
    liquidity = {}
    for row in observations:
        if row["native_symbol"] not in members:
            continue
        age = (utc(as_of) - utc(row["received_at_utc"])).total_seconds()
        if not 0 <= age <= 300:
            raise ContractError("STALE_TAIL_LIQUIDITY")
        liquidity[row["native_symbol"]] = number(row["values"]["quoteVolume"], positive=True)
    if set(liquidity) != set(inventory.eligible_symbols):
        raise ContractError("INCOMPLETE_TAIL_LIQUIDITY_DENOMINATOR")
    ranked = sorted(liquidity, key=lambda n: (liquidity[n], n))
    # Keep the highest-liquidity quartile out of the tail qualification cohort.
    pool = ranked[:len(ranked) * 3 // 4]
    if len(pool) < full_size + footer_size:
        raise ContractError("INSUFFICIENT_INDEPENDENT_TAIL_MEMBERS")
    young = [n for n in pool if members[n].onboard_at_utc
             and 0 <= (utc(as_of) - utc(members[n].onboard_at_utc)).total_seconds() <= 30 * 86400]
    multiplied = [n for n in pool if members[n].contract_multiplier is not None
                  and members[n].contract_multiplier != 1]
    # Preserve medium liquidity alongside the quiet lower half. Exact selection
    # and ranks are recorded, never inferred from performance or BTC direction.
    medium = pool[len(ranked) // 2:]
    priority = [*young[:2], *multiplied[:2], *medium[:max(1, full_size // 5)], *pool]
    chosen = list(dict.fromkeys(priority))[:full_size + footer_size]
    return {"full_partition": chosen[:full_size], "footer_partition": chosen[full_size:],
        "inventory_sha256": inventory.content_sha256, "as_of_utc": as_of,
        "selection": "LOWER_THREE_QUARTILES_WITH_MEDIUM_YOUNG_MULTIPLIER_INCLUSION",
        "global_direction_used": False, "provider_top_lists_used": False,
        "ranks_ascending_quote_volume": {n: ranked.index(n) + 1 for n in chosen},
        "liquidity_denominator": len(ranked), "verified_young_members": [n for n in chosen if n in young],
        "verified_multiplier_members": [n for n in chosen if n in multiplied],
        "qualification_status": "COHORT_PLANNED_NOT_REMOTE_TESTED"}


def independent_partitions(inventory,ticker,*,as_of):
    """Two disjoint authentic 50-name partitions plus a seven-name footer.

    Select from all verified contracts by official turnover, independently of
    Basis. Zero turnover is a separately reported non-positive stratum. Include
    verified young and unusual native spellings, never inferred multipliers.
    """
    if inventory.at(as_of).mode!="VERIFIED_INVENTORY" or ticker.get("kind")!="ticker":
        raise ContractError("TAIL_REQUIRES_VERIFIED_INVENTORY_AND_LIQUIDITY")
    members={i.native_symbol:i for i in inventory.instruments}
    obs=ticker.get("observations",[])
    if len({o["native_symbol"] for o in obs})!=len(obs):raise ContractError("DUPLICATE_MARKET_ROW")
    volumes={}
    for o in obs:
        if (o["source_scope"]!="OFFICIAL_BINANCE_USDM"
                or not 0<=(utc(as_of)-utc(o["received_at_utc"])).total_seconds()<=300):
            raise ContractError("TAIL_LIQUIDITY_SOURCE")
        q=number(o["values"]["quoteVolume"])
        if q<0:raise ContractError("NEGATIVE_VOLUME")
        volumes[o["native_symbol"]]=q
    if set(volumes)!=set(inventory.eligible_symbols):raise ContractError("INCOMPLETE_TAIL_LIQUIDITY_DENOMINATOR")
    ranked=sorted(volumes,key=lambda n:(volumes[n],n))
    positive=[n for n in ranked if volumes[n]>0]
    lower=positive[:len(positive)//2]
    medium=positive[len(positive)//2:len(positive)*3//4]
    if len(lower)<57 or len(medium)<50:raise ContractError("INSUFFICIENT_INDEPENDENT_TAIL_MEMBERS")
    young=[n for n in lower if members[n].onboard_at_utc
           and 0<=(utc(as_of)-utc(members[n].onboard_at_utc)).total_seconds()<=30*86400]
    unusual=[n for n in lower if not n.isascii() or n[0].isdigit()]
    low=list(dict.fromkeys([*young[:2],*unusual[:3],*lower]))[:50]
    mid=medium[:50]
    used=set(low+mid)
    footer=list(dict.fromkeys([n for n in positive if not n.isascii() and n not in used]+
                             [n for n in lower if n not in used]))[:7]
    chosen=low+mid+footer
    return {"partitions":[low,mid,footer],"strata":["LOWER_HALF","MEDIUM_HALF_TO_THREE_QUARTERS","FOOTER"],
        "as_of_utc":as_of,"inventory_sha256":inventory.content_sha256,"liquidity_denominator":len(ranked),
        "zero_turnover_symbols":[n for n in ranked if volumes[n]==0],
        "ranks_ascending_quote_volume":{n:ranked.index(n)+1 for n in chosen},
        "verified_young_members":[n for n in chosen if members[n].onboard_at_utc and
            0<=(utc(as_of)-utc(members[n].onboard_at_utc)).total_seconds()<=30*86400],
        "unusual_native_spellings":[n for n in chosen if not n.isascii() or n[0].isdigit()],
        "verified_multiplier_members":[n for n in chosen if members[n].contract_multiplier is not None and members[n].contract_multiplier!=1],
        "multiplier_inference_used":False,"provider_top_lists_used":False,"global_direction_used":False}
