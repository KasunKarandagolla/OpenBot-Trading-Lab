"""Setup-specific historical policy on the existing native risk/order lifecycle."""
import math
import pandas as pd
from RecoveryPolicyR1 import RecoveryPolicyR1
from freqtrade.strategy import stoploss_from_absolute
from policy_risk import native_exit_reduction
from setup_features import thesis_failed

class SetupPolicyV1(RecoveryPolicyR1):
    def version(self):return 'setup-v1.0.0'

    def bot_start(self,**kwargs):
        mode=getattr(self.config.get('runmode'),'value',self.config.get('runmode'))
        if mode!='backtest':raise ValueError('SetupPolicyV1 is historical research only')
        super().bot_start(**kwargs)
        self.position_adjustment_enable=bool(self.config.get('setup_management',False))

    def sync_trade(self,trade,now):
        g=super().sync_trade(trade,now)
        if g:
            state=trade.get_custom_data('policy_state',{})
            state['lifecycle']='EXITED' if not trade.is_open else ('MANAGED' if state.get('exited_amount',0)>0 else ('FILLED' if state.get('entry_amount',0)>0 else 'ORDER_PENDING'))
            trade.set_custom_data('policy_state',state)
        return g

    def confirm_trade_entry(self,*args,**kwargs):
        # A consumed setup cannot be admitted again after nonfill, exit or restart.
        pair=kwargs.get('pair',args[0] if args else None)
        now=kwargs.get('current_time',args[5] if len(args)>5 else None)
        rate=kwargs.get('rate',args[3] if len(args)>3 else None)
        side=kwargs.get('side',args[7] if len(args)>7 else None)
        try:
            g=self.row_plan(pair,now,side,rate)
            if not g or self._store.get('consumed:'+g['setup_id']):return False
            accepted=super().confirm_trade_entry(*args,**kwargs)
            if accepted:self._store.put('consumed:'+g['setup_id'],True)
            return accepted
        except Exception:return False

    def custom_exit(self,pair,trade,current_time,current_rate,current_profit,**kwargs):
        g=trade.get_custom_data('policy_plan');state=trade.get_custom_data('policy_state',{})
        if not g:return 'geometry_unavailable'
        s=-1 if trade.is_short else 1
        # These paths deliberately require no account/source/event-store success.
        if s*(current_rate-state.get('tight_stop',g['stop']))<=0:return 'protective_level_breach'
        first=state.get('first_fill',trade.open_date_utc.timestamp())
        limit=min(15,float(g['max_hold_hours']))
        if current_time.timestamp()-first>=limit*3600:return 'max_hold_'+str(int(limit))+'h'
        if state.get('late_fill'):return 'late_fill_after_expiry'
        try:
            frame,_=self.dp.get_analyzed_dataframe(pair,self.timeframe)
            q=frame.loc[(frame.date+pd.Timedelta(minutes=15)<=pd.Timestamp(current_time)) & (frame.date+pd.Timedelta(minutes=15)>pd.Timestamp(first,unit='s',tz='UTC'))]
            if thesis_failed(g,q):return g['recipe']+'_thesis_failed'
        except Exception:pass
        return None

    def custom_roi(self,pair,trade,current_time,trade_duration,entry_tag,side,**kwargs):
        g=trade.get_custom_data('policy_plan')
        if not g:return None
        second=g.get('second_objective')
        target=second['price'] if self.position_adjustment_enable and second else g['target']
        return trade.calc_profit_ratio(target)

    def adjust_trade_position(self,trade,current_time,current_rate,current_profit,min_stake,max_stake,current_entry_rate,current_exit_rate,current_entry_profit,current_exit_profit,**kwargs):
        if not self.position_adjustment_enable or trade.has_open_orders:return None
        g=self.sync_trade(trade,current_time)
        if not g or not g.get('second_objective'):return None
        s=-1 if trade.is_short else 1
        if s*(current_exit_rate-g['first_objective']['price'])<0:return None
        state=trade.get_custom_data('policy_state',{})
        wanted=max(0,state['entry_amount']/3-state['exited_amount'])
        c=self._contracts[trade.pair];step=c['contract_size']*c['step_contracts']
        qty=math.floor((min(wanted,trade.amount)/step)+1e-9)*step
        minimum=c['contract_size']*c['min_contracts']
        if qty<minimum or trade.amount-qty<minimum or qty*current_exit_rate<c.get('min_notional',0):return None
        reduction=native_exit_reduction(qty,trade)
        if not 0<reduction<trade.stake_amount:return None
        if min_stake is not None and min(reduction,trade.stake_amount-reduction)<min_stake:return None
        return -reduction,'first_objective_one_third'

    def custom_stoploss(self,pair,trade,current_time,current_rate,current_profit,after_fill=False,**kwargs):
        try:
            g=self.sync_trade(trade,current_time)
            if not g:return None
            state=trade.get_custom_data('policy_state',{});s=-1 if trade.is_short else 1
            stop=float(state.get('tight_stop',g['stop']))
            if trade.stop_loss:stop=max(stop,trade.stop_loss) if s==1 else min(stop,trade.stop_loss)
            if self.position_adjustment_enable and state.get('partial_done'):
                frame,_=self.dp.get_analyzed_dataframe(pair,self.timeframe)
                if len(frame):
                    r=frame.iloc[-1];key='swing_high' if trade.is_short else 'swing_low';stamp=r.get(key+'_known_at')
                    if pd.notna(r.get(key)) and pd.notna(stamp) and pd.Timestamp(state['first_fill'],unit='s',tz='UTC')<pd.Timestamp(stamp)<=pd.Timestamp(current_time):
                        proposed=float(r[key])-s*.2*float(r.atr14)
                        reserve=.0023*trade.open_rate+max(0,-float(trade.funding_fee_running or 0))/max(trade.amount,1e-12)
                        be=(trade.open_rate*(1+s*trade.fee_open)+s*reserve)/(1-s*trade.fee_close)
                        # No arbitrary1R/ATR trail. A new confirmed swing must
                        # support a stop beyond cost-aware breakeven itself.
                        if s*(proposed-be)>0 and s*(proposed-stop)>0 and s*(current_rate-proposed)>0:
                            stop=proposed;state['tight_stop']=stop;trade.set_custom_data('policy_state',state)
                            self.event_v3(f'stop:{trade.id}:{stop}','STOP_TIGHTEN',current_time,stop=stop,decision_id=g['decision_id'])
            if s*(current_rate-stop)<=0:return None
            return stoploss_from_absolute(stop,current_rate,is_short=trade.is_short,leverage=trade.leverage)
        except Exception:return None
