"""Registered research-only executable strategy; native Freqtrade owns execution.

The selected plans contain only causal decisions. This policy refuses every
mode except native historical backtesting; it cannot activate persistent paper.
"""
from PaperPolicyV4 import Session4Replay

class RecoveryPolicyR1(Session4Replay):
    def version(self):return 'recovery-v1.0.0'

    def bot_start(self,**kwargs):
        mode=getattr(self.config.get('runmode'),'value',self.config.get('runmode'))
        if mode!='backtest':raise ValueError('RecoveryPolicyR1 is historical research only')
        if float(self.config.get('policy_leverage',1))!=1:raise ValueError('1x only')
        super().bot_start(**kwargs)

    def custom_stake_amount(self,pair,current_time,current_rate,proposed_stake,min_stake,max_stake,leverage,entry_tag,side,**kwargs):
        try:
            g=self.row_plan(pair,current_time,side,current_rate)
            if not g:return 0.
            old=self.config['policy_notional_cap']
            cap=min(25.,.25/g['modeled_loss_per_notional']) if self.config.get('recovery_risk') else 25.
            # Scenario: only half the desired quantity can be allocated. This
            # is a complete capacity portfolio, not a queue-derived fill claim.
            self.config['policy_notional_cap']=cap*float(self.config.get('recovery_allocation_fraction',1))
            try:
                return super(Session4Replay,self).custom_stake_amount(pair,current_time,current_rate,proposed_stake,min_stake,max_stake,leverage,entry_tag,side,**kwargs)
            finally:self.config['policy_notional_cap']=old
        except Exception:return 0.

    def confirm_trade_entry(self,pair,order_type,amount,rate,time_in_force,current_time,entry_tag,side,**kwargs):
        # Native confirmation must enforce the same cap as the sizing callback.
        old=self.config['policy_notional_cap']
        try:
            g=self.row_plan(pair,current_time,side,rate)
            if not g:return False
            cap=min(25.,.25/g['modeled_loss_per_notional']) if self.config.get('recovery_risk') else 25.
            self.config['policy_notional_cap']=cap*float(self.config.get('recovery_allocation_fraction',1))
            return super().confirm_trade_entry(pair,order_type,amount,rate,time_in_force,current_time,entry_tag,side,**kwargs)
        except Exception:return False
        finally:self.config['policy_notional_cap']=old

    def custom_exit(self,pair,trade,current_time,current_rate,current_profit,**kwargs):
        if self.config.get('recovery_management')=='barriers-only':
            g=trade.get_custom_data('policy_plan');s=trade.get_custom_data('policy_state',{})
            if not g:return 'geometry_unavailable'
            sign=-1 if trade.is_short else 1
            if sign*(current_rate-s.get('tight_stop',g['stop']))<=0:return 'protective_level_breach'
            if current_time.timestamp()-s.get('first_fill',trade.open_date_utc.timestamp())>=g['max_hold_hours']*3600:return 'max_hold_'+str(g['max_hold_hours'])+'h'
            return None
        return super().custom_exit(pair,trade,current_time,current_rate,current_profit,**kwargs)


class RecoveryMomentumHourlyR1(RecoveryPolicyR1):
    """Same daily economic rule with real1h inputs; explicitly separate resolution."""
    timeframe='1h'
    startup_candle_count=240

    def signal_row(self,pair,current_time,side=None):
        import pandas as pd
        try:
            d,_=self.dp.get_analyzed_dataframe(pair,self.timeframe)
            if d.empty:return None
            r=d.iloc[-1];available=pd.Timestamp(r.date)+pd.Timedelta(hours=1)
            if not pd.Timedelta(0)<=pd.Timestamp(current_time)-available<pd.Timedelta(minutes=5):return None
            if side and int(r.get('enter_'+side,0))!=1:return None
            return r
        except Exception:return None

    def populate_entry_trend(self,d,metadata):
        import json
        import pandas as pd
        from pathlib import Path
        if not hasattr(self,'_replay_plans'):self._replay_plans=json.loads(Path(self.config['session4_plans']).read_text())
        plans=self._replay_plans.get(metadata['pair'],{})
        d=d.copy();d['enter_long']=0;d['enter_short']=0;d['enter_tag']='';d['policy_plan']=None
        for i,r in d.iterrows():
            g=plans.get((r.date+pd.Timedelta(hours=1)).isoformat())
            if g:
                d.at[i,'enter_'+g['side']]=1;d.at[i,'enter_tag']='momentum:hourly';d.at[i,'policy_plan']=json.dumps(g,sort_keys=True)
        return d

