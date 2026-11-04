"""Historical-only challenger; inherited Freqtrade orders, risk and stop protection."""
import json
import pandas as pd
from RecoveryPolicyR1 import RecoveryPolicyR1
from market_reader import continuation_failure

class IntegratedPolicyR1(RecoveryPolicyR1):
    def version(self): return 'integrated-r1.0.0'

    def bot_start(self,**kwargs):
        if self.config.get('max_open_trades')!=2 or float(self.config.get('policy_notional_cap',0))>25:
            raise ValueError('research risk bounds')
        super().bot_start(**kwargs)
        self.position_adjustment_enable=False

    def custom_exit(self,pair,trade,current_time,current_rate,current_profit,**kwargs):
        if not self.config.get('integrated_structural_exit'): return super().custom_exit(pair,trade,current_time,current_rate,current_profit,**kwargs)
        g=trade.get_custom_data('policy_plan');state=trade.get_custom_data('policy_state',{})
        if not g: return 'geometry_unavailable'
        sign=-1 if trade.is_short else 1
        # Price/time protection remains independent of market reader or data-store availability.
        if sign*(current_rate-state.get('tight_stop',g['stop']))<=0: return 'protective_level_breach'
        first=state.get('first_fill',trade.open_date_utc.timestamp())
        if current_time.timestamp()-first>=min(15,g['max_hold_hours'])*3600: return 'max_hold_'+str(g['max_hold_hours'])+'h'
        if state.get('late_fill'): return 'late_fill_after_expiry'
        if g['recipe']!='continuation': return super().custom_exit(pair,trade,current_time,current_rate,current_profit,**kwargs)
        try:
            frame,_=self.dp.get_analyzed_dataframe(pair,self.timeframe)
            if 'source15_closed_at' in frame:
                frame=frame.loc[frame.source15_closed_at<=pd.Timestamp(current_time)].drop_duplicates('source15_closed_at')
                rows=frame.loc[frame.source15_closed_at>pd.Timestamp(first,unit='s',tz='UTC')]
                rows=rows.copy();rows['close']=rows.source15_close
            else:
                close=frame.date+pd.Timedelta(minutes=15)
                rows=frame.loc[(close<=pd.Timestamp(current_time))&(close>pd.Timestamp(first,unit='s',tz='UTC'))]
            if continuation_failure(g,rows): return 'defended_zone_structural_failure'
        except Exception: pass
        return None

class IntegratedFiveMinuteR1(IntegratedPolicyR1):
    timeframe='5m'
    startup_candle_count=1  # 15m/1h/4h indicators arrive fully warmed in causal cache.

    def signal_row(self,pair,current_time,side=None):
        try:
            d,_=self.dp.get_analyzed_dataframe(pair,self.timeframe)
            if d.empty: return None
            r=d.iloc[-1]; available=pd.Timestamp(r.date)+pd.Timedelta(minutes=5)
            if not pd.Timedelta(0)<=pd.Timestamp(current_time)-available<pd.Timedelta(minutes=5): return None
            if side and int(r.get('enter_'+side,0))!=1: return None
            return r
        except Exception: return None

    def populate_entry_trend(self,d,metadata):
        from pathlib import Path
        if not hasattr(self,'_replay_plans'): self._replay_plans=json.loads(Path(self.config['session4_plans']).read_text())
        plans=self._replay_plans.get(metadata['pair'],{})
        d=d.copy();d['enter_long']=0;d['enter_short']=0;d['enter_tag']='';d['policy_plan']=None
        for i,r in d.iterrows():
            g=plans.get((r.date+pd.Timedelta(minutes=5)).isoformat())
            if g:
                d.at[i,'enter_'+g['side']]=1;d.at[i,'enter_tag']='continuation:5m-r1';d.at[i,'policy_plan']=json.dumps(g,sort_keys=True)
        return d
