"""Preserve actual Gate settlement clocks when joining hourly source marks.

Some public funding events occur seconds after the scheduled hour. An equality
join silently drops those real costs. Use the last observed hourly mark OPEN;
do not move event times, invent rates, or infer a minute mark that was not saved.
Native Freqtrade still calculates signed funding and the persisted cursor ensures
each actual event is charged once.
"""
class EventClockFunding:
    """Charge actual events at every native decision check, before exit order fill.

    The parent hourly gate is appropriate for canonical hour-aligned events.
    Actual second-offset events require every checkpoint: otherwise a short
    position can close before the next whole hour and its order can snapshot
    funding before a forced after-fill update.
    """
    def _run_funding_fees(self,trade,current_time,force=False):
        import pandas as pd
        from freqtrade.enums import TradingMode
        if self.trading_mode!=TradingMode.FUTURES:return
        f=self.futures_data[trade.pair]
        clocks=[o.order_filled_utc for o in trade.orders if o.ft_order_side==trade.entry_side and o.filled and o.order_filled_utc]
        if not clocks:return
        first=min(clocks);cursor=trade.get_custom_data('v3_funding_cursor')
        eligible=f.loc[(f.date>=pd.Timestamp(first))&(f.date<=pd.Timestamp(current_time))]
        if cursor is not None:eligible=eligible.loc[eligible.date>pd.Timestamp(cursor)]
        fee=0.
        if len(eligible):
            fee=self.exchange.calculate_funding_fees(eligible,amount=trade.amount,is_short=trade.is_short,open_date=first,close_date=current_time)
            trade.set_custom_data('v3_funding_cursor',eligible.date.iloc[-1].isoformat())
            ledger=trade.get_custom_data('v3_funding_events',[])
            ledger.extend(dict(at=r.date.isoformat(),quantity=float(trade.amount),rate=float(r.open_fund),mark=float(r.open_mark)) for _,r in eligible.iterrows())
            trade.set_custom_data('v3_funding_events',ledger)
        trade.set_funding_fees(float(trade.funding_fee_running or 0)+fee)

def install():
    import pandas as pd
    from freqtrade.exchange.exchange import Exchange
    def combine(funding_rates,mark_rates,futures_funding_rate=None):
        if futures_funding_rate is not None:raise ValueError('invented funding fallback forbidden')
        key='funding_rate' if 'funding_rate' in funding_rates else 'open'
        f=funding_rates[['date',key]].rename(columns={key:'open_fund'}).sort_values('date')
        m=mark_rates[['date','open']].rename(columns={'date':'mark_clock','open':'open_mark'}).sort_values('mark_clock')
        if f.date.duplicated().any():raise ValueError('duplicate funding event')
        q=pd.merge_asof(f,m,left_on='date',right_on='mark_clock',direction='backward',tolerance=pd.Timedelta(hours=1))
        if q.open_mark.isna().any():raise ValueError('funding mark unavailable')
        return Exchange._add_funding_columns(q[['date','open_mark','open_fund']])
    Exchange.combine_funding_and_mark=staticmethod(combine)
