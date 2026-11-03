"""Scoped native dry-run funding accounting; no order or exchange execution API.

Install on this native Exchange instance only. Native Freqtrade remains the bot,
wallet, order manager and funding valuer. A source outage preserves last known
fees, marks accounting UNKNOWN and inhibits entry; protective exits continue.
"""
from datetime import datetime, timezone
import math
import types
import pandas as pd
from freqtrade.enums import CandleType
from freqtrade.persistence import Trade


def install(exchange,contracts,clock=None):
    if not exchange._config.get('dry_run'):
        raise ValueError('event-once adapter is exclusively native dry-run')
    if getattr(exchange,'_policy_funding_installed',False) is True:return
    clock=clock or (lambda:datetime.now(timezone.utc))
    def funding(self,pair,amount,is_short,open_date):
        matches=[t for t in Trade.get_open_trades() if t.pair==pair]
        if len(matches)!=1:raise ValueError('one native trade per symbol required for funding')
        trade=matches[0];observed=clock();existing=float(trade.funding_fee_running or 0)
        try:
            interval=contracts[pair]['funding_interval_seconds']
            if not isinstance(interval,int) or interval<=0:raise ValueError('funding schedule unknown')
            tf=self._ft_has['mark_ohlcv_timeframe'];ftf=self._ft_has['funding_fee_timeframe']
            mark_kind=CandleType.from_string(self._ft_has['mark_ohlcv_price'])
            mkey=(pair,tf,mark_kind);fkey=(pair,ftf,CandleType.FUNDING_RATE)
            since=int(trade.open_date_utc.timestamp()//3600*3600*1000)
            histories=self.refresh_latest_ohlcv([mkey,fkey],since_ms=since,cache=False,drop_incomplete=False)
            rates=histories[fkey];marks=histories[mkey]
            if rates.date.duplicated().any() or marks.date.duplicated().any():raise ValueError('duplicate source funding/mark clock')
            if not rates.date.is_monotonic_increasing or not marks.date.is_monotonic_increasing:raise ValueError('unordered funding source')
            combined=self.combine_funding_and_mark(rates,marks)
            ledger=trade.get_custom_data('policy_paper_funding_events',[])
            seen={r['at'] for r in ledger}
            entry_clocks=[o.order_filled_utc.timestamp() for o in trade.orders if o.ft_order_side==trade.entry_side and o.filled and o.order_filled_utc]
            start=min(entry_clocks,default=trade.open_date_utc.timestamp());end=observed.timestamp()
            first=math.ceil(start/interval)*interval
            expected=[pd.Timestamp(at,unit='s',tz='UTC').isoformat() for at in range(int(first),int(end)+1,interval)]
            source={pd.Timestamp(r.date).isoformat():r for _,r in combined.iterrows()}
            if any(at not in source and at not in seen for at in expected):raise ValueError('scheduled funding event/mark unavailable')
            new=[];additional=0.
            for at in expected:
                if at in seen:continue
                stamp=pd.Timestamp(at);row=source[at];quantity=0.
                for order in trade.orders:
                    if not order.filled:continue
                    # A cumulative open partial has no complete per-fill clock.
                    # Cancel/crystallize through native timeout before valuation.
                    if order.ft_is_open:raise ValueError('unresolved open partial fill chronology')
                    if order.order_filled_utc is None:raise ValueError('native fill clock unavailable')
                    when=pd.Timestamp(order.order_filled_utc)
                    if order.ft_order_side==trade.entry_side and when<=stamp:quantity+=float(order.filled)
                    if order.ft_order_side==trade.exit_side and when<stamp:quantity-=float(order.filled)
                if quantity<0:raise ValueError('negative reconstructed funding quantity')
                one=combined.loc[combined.date.eq(stamp)]
                fee=float(self.calculate_funding_fees(one,amount=quantity,is_short=is_short,
                    open_date=trade.open_date_utc,close_date=observed))
                if not math.isfinite(fee):raise ValueError('invalid funding valuation')
                additional+=fee;new.append(dict(at=at,quantity=quantity,rate=float(row.open_fund),mark=float(row.open_mark),signed_fee=fee,
                    observed_at=observed.isoformat(),priority='ENTRY_BEFORE_EVENT_BEFORE_SAME_CLOCK_EXIT_VENUE_PRIORITY_UNKNOWN'))
            # Set monetary state before custom-data publication (the native
            # session commits both). Durable event IDs survive a cursor restart.
            trade.set_funding_fees(existing+additional)
            trade.set_custom_data('policy_paper_funding_events',ledger+new)
            trade.set_custom_data('policy_funding_health',dict(status='CHECKED_NATIVE_DRY_RUN',asof=observed.isoformat()))
            Trade.commit()
            return existing+additional
        except Exception as error:
            trade.set_custom_data('policy_funding_health',dict(status='UNKNOWN',asof=observed.isoformat(),reason=type(error).__name__+': '+str(error)[:200]))
            Trade.commit()
            return existing
    exchange.get_funding_fees=types.MethodType(funding,exchange)
    exchange._policy_funding_installed=True
