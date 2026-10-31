"""Native research strategy: existing recipes, causal selection, native callbacks.

Not in the operational allowlist. Historical schedule is a causal cross-sectional
sample, not a historical reconstruction of Gate membership. No external agent gate.
"""
from datetime import timedelta
import json
import math
from pathlib import Path
import pandas as pd
import numpy as np
from freqtrade.strategy import informative, stoploss_from_absolute
from freqtrade.persistence import Trade
from PlaybookRiskV1 import PlaybookRiskV1, session_features
from VWAPTrendContinuationV1 import VWAPTrendContinuationV1
from LiquiditySweepReversalV1 import LiquiditySweepReversalV1
from causal_structure import structure
from advanced_features import advanced, qualifiers, plan


class OpportunityRouterV1(PlaybookRiskV1):
    variant='router'
    hold_hours=8
    stop_buffer=.2
    use_custom_roi=True
    minimal_roi={'0':100.}
    position_adjustment_enable=False
    max_entry_position_adjustment=0

    def version(self):return 'bonus-1.0.0'

    @informative('1h')
    def populate_indicators_1h(self,dataframe,metadata):
        return structure(super().populate_indicators_1h(dataframe,metadata),'1h')

    def populate_indicators(self,dataframe,metadata):
        return advanced(session_features(dataframe))

    def populate_entry_trend(self,d,metadata):
        v=VWAPTrendContinuationV1(self.config).populate_entry_trend(d.copy(),metadata)
        s=LiquiditySweepReversalV1(self.config).populate_entry_trend(d.copy(),metadata)
        schedule=json.loads(Path(self.config['bonus_schedule']).read_text())
        symbol=metadata['pair']; d=d.copy()
        d['enter_long']=0;d['enter_short']=0;d['enter_tag']=''
        d['bonus_plan']=None;d['bonus_reason']='NO_SETUP';d['bonus_recipe']=''
        d['parent_candidate']=0
        d['smc_ok']=False;d['ict_ok']=False;d['profile_ok']=False
        trend=d.adx_1h>=25
        possible=((trend & (v.enter_long.eq(1)|v.enter_short.eq(1)))
                  |(~trend & (s.enter_long.eq(1)|s.enter_short.eq(1))))
        for i in np.flatnonzero(possible.to_numpy()):
            recipe='vwap' if d.adx_1h.iloc[i]>=25 else 'sweep'
            parent=v.iloc[i] if recipe=='vwap' else s.iloc[i]
            sides=[side for side in ('long','short') if parent['enter_'+side]==1]
            if not sides:continue
            d.at[d.index[i],'parent_candidate']=1
            if len(sides)!=1:
                d.at[d.index[i],'bonus_reason']='CONFLICTING_SIDES';continue
            idx=d.index[i];row=d.iloc[i];side=sides[0]
            d.at[idx,'bonus_recipe']=recipe
            eligible=schedule['decisions'].get((row.date+pd.Timedelta(minutes=15)).isoformat(),{})
            if symbol not in eligible.get('selected',[]):
                d.at[idx,'bonus_reason']='CHEAP_SCREEN_OR_RANK';continue
            q=qualifiers(row,recipe,side)
            for key in q:d.at[idx,key+'_ok']=q[key]
            require={'smc':['smc'],'ict':['ict'],'profile':['profile']}.get(self.variant,[])
            if self.variant=='integrated':require=['smc'] if recipe=='vwap' else ['ict']
            if any(not q[k] for k in require):
                d.at[idx,'bonus_reason']='CONTEXT_'+('_'.join(k.upper() for k in require));continue
            g=plan(row,recipe,side,integrated=self.variant=='integrated',profile_only=self.variant=='profile')
            if g is None:
                d.at[idx,'bonus_reason']='TARGET_ROOM_OR_COST';continue
            d.at[idx,'enter_'+side]=1
            d.at[idx,'enter_tag']=recipe+':bonus-v1'
            d.at[idx,'bonus_plan']=json.dumps(g,sort_keys=True)
            d.at[idx,'bonus_reason']='TRADE'
        return d

    def row_plan(self,pair,now,side,rate):
        row=self.signal_row(pair,now,side)
        if row is None or not isinstance(row.get('bonus_plan'),str):return None
        g=json.loads(row.bonus_plan)
        if abs(rate/g['reference']-1)>min(.0015,.25*row.atr14/g['reference']):return None
        sign=-1 if side=='short' else 1
        loss=sign*(rate-g['stop'])/rate;reward=sign*(g['target']-rate)/rate
        if not .003<=loss<=.025 or (reward-.0035)/(loss+.0035)<1.25:return None
        return g|{'risk_fraction':loss,'modeled_loss_per_notional':loss+.0035}

    def custom_stake_amount(self,pair,current_time,current_rate,proposed_stake,min_stake,max_stake,leverage,entry_tag,side,**kwargs):
        try:
            g=self.row_plan(pair,current_time,side,current_rate)
            if not g or leverage!=1 or not math.isfinite(max_stake):return 0.
            amount=min(25.,max_stake,2.5/g['modeled_loss_per_notional'])
            return amount if amount>0 and (min_stake is None or amount>=min_stake) else 0.
        except Exception:return 0.

    def confirm_trade_entry(self,pair,order_type,amount,rate,time_in_force,current_time,entry_tag,side,**kwargs):
        try:
            g=self.row_plan(pair,current_time,side,rate)
            trades=Trade.get_open_trades()
            if g is None or len(trades)>=2 or any(t.pair==pair for t in trades):return False
            if not 0<amount*rate<=25.+1e-7:return False
            # Native wallet marks unrealized P&L using the current completed mark proxy.
            # No fallback to realized-only admission when an account mark is unavailable.
            total=float(self.wallets.get_total_stake_amount())
            unrealized=0.
            for t in trades:
                f,_=self.dp.get_analyzed_dataframe(t.pair,self.timeframe)
                if f.empty:return False
                last=f.iloc[-1]
                age=current_time-(last.date.to_pydatetime()+timedelta(minutes=15))
                if not timedelta(0)<=age<=timedelta(minutes=15):return False
                unrealized+=t.calc_profit(float(last.close))
            # Research reference day equity reconstructed deterministically from native trades.
            start=current_time.replace(hour=0,minute=0,second=0,microsecond=0)
            closed=Trade.get_trades_proxy(is_open=False)
            today=sum(float(t.close_profit_abs or 0) for t in closed if t.close_date_utc and start<=t.close_date_utc<=current_time)
            day_start=total-today
            equity=total+unrealized
            if not math.isfinite(equity) or equity<=day_start*.99:return False
            reserve=sum(float(t.stake_amount)*(.03+.0035) for t in trades)
            return reserve+amount*rate*g['modeled_loss_per_notional']<=equity*.005
        except Exception:return False

    def order_filled(self,pair,trade,order,current_time,**kwargs):
        if order.ft_order_side==trade.entry_side:
            if trade.get_custom_data('bonus_plan') is not None:return
            g=self.row_plan(pair,current_time,'short' if trade.is_short else 'long',trade.open_rate)
            if g:
                trade.set_custom_data('bonus_plan',g)
                trade.set_custom_data('initial_geometry',g)
                trade.set_custom_data('bonus_partial_done',False)
        elif trade.nr_of_successful_exits>0:
            # Native fill is the state transition; duplicate callbacks are idempotent.
            trade.set_custom_data('bonus_partial_done',True)

    def custom_roi(self,pair,trade,current_time,trade_duration,entry_tag,side,**kwargs):
        g=trade.get_custom_data('bonus_plan')
        return trade.calc_profit_ratio(g['target']) if g else None

    def custom_stoploss(self,pair,trade,current_time,current_rate,current_profit,after_fill=False,**kwargs):
        g=trade.get_custom_data('bonus_plan')
        if not g:return None
        stop=g['stop']
        prior_tight=trade.get_custom_data('bonus_tight_stop')
        sign=-1 if trade.is_short else 1
        if prior_tight is not None:
            if sign*(current_rate-prior_tight)<=0:return None
            if sign*(prior_tight-stop)>0:stop=prior_tight
        if self.position_adjustment_enable and trade.get_custom_data('bonus_partial_done'):
            # Persist maximum favorable stop so a restart cannot loosen it.
            be=trade.open_rate*(1+sign*.0035)
            desired=be
            f,_=self.dp.get_analyzed_dataframe(pair,self.timeframe)
            if not f.empty:
                row=f.iloc[-1];key='swing_high' if trade.is_short else 'swing_low'
                known=row.get(key+'_known_at')
                value=row.get(key)
                if pd.notna(known) and pd.Timestamp(known)<=pd.Timestamp(current_time) and pd.notna(value) and sign*(value-desired)>0:
                    desired=float(value)
            old=trade.get_custom_data('bonus_tight_stop')
            if old is not None and sign*(old-desired)>0:desired=old
            if sign*(desired-stop)>0 and sign*(current_rate-desired)>0:
                stop=desired;trade.set_custom_data('bonus_tight_stop',stop)
        return stoploss_from_absolute(stop,current_rate,is_short=trade.is_short,leverage=trade.leverage)

    def custom_exit(self,pair,trade,current_time,current_rate,current_profit,**kwargs):
        g=trade.get_custom_data('bonus_plan')
        if not g:return 'geometry_unavailable'
        sign=-1 if trade.is_short else 1
        if sign*(current_rate-g['target'])>=0:return 'frozen_target'
        if current_time-trade.open_date_utc>=timedelta(hours=g['max_hold_hours']):return 'max_hold_'+str(g['max_hold_hours'])+'h'
        f,_=self.dp.get_analyzed_dataframe(pair,self.timeframe)
        if not f.empty:
            row=f.iloc[-1]
            if row.get('struct_direction_1h')==('UP' if trade.is_short else 'DOWN') and row.get('adx_1h',0)>=25:
                return 'closed_hour_thesis_invalidated'
        return None

    def adjust_trade_position(self,trade,current_time,current_rate,current_profit,min_stake,max_stake,current_entry_rate,current_exit_rate,current_entry_profit,current_exit_profit,**kwargs):
        if not self.position_adjustment_enable:return None
        if trade.has_open_orders or trade.nr_of_successful_exits>0 or trade.get_custom_data('bonus_partial_done'):return None
        g=trade.get_custom_data('bonus_plan')
        if not g:return None
        sign=-1 if trade.is_short else 1
        moved=sign*(current_rate-trade.open_rate)/trade.open_rate
        final=sign*(g['target']-trade.open_rate)/trade.open_rate
        if moved<g['risk_fraction'] or moved>=final:return None
        half=trade.stake_amount*.5
        if min_stake is None or half<min_stake:return None
        # Engine rounds/validates the stake-reduction amount and native order state.
        return -half,'partial_1R_v1'


class RouterOnlyV1(OpportunityRouterV1):variant='router'
class RouterSMCV1(OpportunityRouterV1):variant='smc'
class RouterICTV1(OpportunityRouterV1):variant='ict'
class RouterProfileV1(OpportunityRouterV1):variant='profile'
class IntegratedM0V1(OpportunityRouterV1):variant='integrated'
class IntegratedM1V1(IntegratedM0V1):position_adjustment_enable=True
class RouterOnlyM1V1(RouterOnlyV1):position_adjustment_enable=True
