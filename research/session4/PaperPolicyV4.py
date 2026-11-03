"""Native Freqtrade paper policy. Freqtrade alone owns orders and inventory."""
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time
import numpy as np
import pandas as pd
from freqtrade.persistence import Trade
from freqtrade.strategy import informative, stoploss_from_absolute
from PolicyV3 import PolicyFixedV3
from session4_features import hourly, indicators, liquidity, candidates
from paper_state import PaperState
from PlaybookRiskV1 import session_features
import talib.abstract as ta


class PaperPolicyV4(PolicyFixedV3):
    startup_candle_count=960
    stoploss=-.025  # 1x default; bot_start scales ROI bound with reviewed leverage.
    position_adjustment_enable=False
    def version(self):return 'structure-execution-v4.0.0'

    def bot_start(self,**kwargs):
        if self.config.get('dry_run') is not True:raise ValueError('paper only')
        if any(self.config.get('exchange',{}).get(k) for k in ('key','secret','password','uid','apiKey')):raise ValueError('credentials forbidden')
        lev=float(self.config.get('policy_leverage',1))
        if lev not in (1,10,20):raise ValueError('unreviewed leverage')
        self.stoploss=-.025*lev
        super().bot_start(**kwargs)
        if getattr(self.config.get('runmode'),'value',self.config.get('runmode'))=='dry_run':
            self._store.close();self._store=PaperState(self.config['policy_state'])
        self._live_slots={};self._receipt_marks={};self._source_health='UNOBSERVED'
        self._last_telemetry=0

    @informative('1h')
    def populate_indicators_1h(self,dataframe,metadata):return hourly(dataframe)

    def populate_indicators(self,dataframe,metadata):return indicators(dataframe)

    def bot_loop_start(self,current_time,**kwargs):
        self._receipt_marks={}
        super().bot_loop_start(current_time,**kwargs)
        mode=getattr(self.config.get('runmode'),'value',self.config.get('runmode'))
        if mode=='dry_run':
            try:
                api=self.dp._exchange._api
                begin=time.monotonic();server=api.fetch_time();received=datetime.now(timezone.utc)
                if time.monotonic()-begin>5 or abs(received.timestamp()*1000-server)>2000:raise ValueError('public clock unqualified')
                frames={};last=None
                for pair in self.dp.current_whitelist():
                    d=self.dp.get_pair_dataframe(pair,self.timeframe)
                    d=d.loc[d.date+pd.Timedelta(minutes=15)<=pd.Timestamp(current_time)].copy()
                    if len(d)<960:continue
                    at=d.date.iloc[-1]+pd.Timedelta(minutes=15)
                    if not pd.Timedelta(0)<=pd.Timestamp(current_time)-at<pd.Timedelta(minutes=15):continue
                    q=liquidity(d);r=q.iloc[-1]
                    h=self.dp.get_pair_dataframe(pair,'1h')
                    h=h.loc[h.date+pd.Timedelta(hours=1)<=pd.Timestamp(current_time)].copy()
                    if len(h)<240:continue
                    hage=pd.Timestamp(current_time)-(h.date.iloc[-1]+pd.Timedelta(hours=1))
                    if not pd.Timedelta(0)<=hage<pd.Timedelta(hours=1):continue
                    bias=float(ta.EMA(h,timeperiod=20).iloc[-1]-ta.EMA(h,timeperiod=50).iloc[-1])
                    if bool(r.eligible):frames[pair]=(r,at,session_features(d).iloc[-1],bias)
                btc=frames.get('BTC/USDT:USDT')
                if not btc:raise ValueError('BTC ranking context missing')
                slots={}
                for recipe in ('continuation','reversal'):
                    for side,sign in [('long',1),('short',-1)]:
                        ranked=[]
                        for pair,(r,at,local,bias) in frames.items():
                            if recipe=='continuation' and sign*bias<=0:continue
                            score=(sign*(r.return4h-(0 if pair=='BTC/USDT:USDT' else btc[0].return4h))+.01*min(float(r.activity),3) if recipe=='continuation' else
                                   sign*(local.close-(local.prior_low if sign==1 else local.prior_high))/local.atr14)
                            if math.isfinite(score):ranked.append((score,pair,at))
                        ranked.sort(key=lambda r:(-r[0],r[1]))
                        for _,pair,at in ranked[:3]:slots.setdefault(at.isoformat(),{}).setdefault(recipe+':'+side,[]).append(pair)
                self._live_slots=slots;self._source_health='PUBLIC_RECEIPT_CLOCK_CHECKED_EVENT_CLOCK_UNAVAILABLE'
            except Exception as error:
                self._live_slots={};self._source_health='SOURCE_UNAVAILABLE:'+type(error).__name__
            if current_time.timestamp()-self._last_telemetry>=30:
                self.event_v3('loop:'+current_time.isoformat(),'PAPER_MONITOR',current_time,
                    account_verdict=self._risk_verdict,source_health=self._source_health,
                    ranked_slots=self._live_slots,open_trades=len(Trade.get_open_trades()))
                self._last_telemetry=current_time.timestamp()

    def populate_entry_trend(self,d,metadata):
        d=d.copy();d['enter_long']=0;d['enter_short']=0;d['enter_tag']='';d['policy_plan']=None
        d['policy_reason']='NO_SETUP';pair=metadata['pair']
        # Only the current closed bar can produce a live order. No historical schedule dependency.
        rows=candidates(d,self.config.get('session4_mode','structure'))
        for item in rows:
            i=item['index'];g=item['plan'];reason=item['reason'];side=item['side']
            if reason=='TRADE' and pair not in self._live_slots.get(item['at'],{}).get(item['recipe']+':'+side,[]):reason='REJECT_CAUSAL_RANK_OR_SOURCE'
            if reason=='TRADE':
                if d.at[i,'enter_'+('short' if side=='long' else 'long')]==1:
                    d.at[i,'enter_long']=0;d.at[i,'enter_short']=0;d.at[i,'policy_plan']=None;reason='CONFLICTING_SIDES'
                else:
                    g['decision_id']=pair+':'+g['decision_id']
                    d.at[i,'enter_'+side]=1;d.at[i,'enter_tag']=item['recipe']+':v4'
                    d.at[i,'policy_plan']=json.dumps(g,sort_keys=True)
            d.at[i,'policy_reason']=reason
        return d

    def mark(self,pair,now):
        mode=getattr(self.config.get('runmode'),'value',self.config.get('runmode'))
        if mode in ('backtest','hyperopt'):return super().mark(pair,now)
        if pair not in self._receipt_marks:
            begin=time.monotonic();q=self.dp._exchange._api.fetch_ticker(pair)
            received=datetime.now(timezone.utc);mark=q.get('markPrice') or q.get('info',{}).get('mark_price')
            if time.monotonic()-begin>5 or abs(received.timestamp()-now.timestamp())>60:raise ValueError('mark receipt stale')
            if mark is None or not math.isfinite(float(mark)) or float(mark)<=0:raise ValueError('mark unavailable')
            self._receipt_marks[pair]=float(mark)
        return self._receipt_marks[pair]

    def risk_size(self,pair,now,side,rate,lev,min_stake=0):
        g=self.row_plan(pair,now,side,rate)
        if not g:return None
        c=self._contracts[pair];tick=float(c['price_precision'])
        # Conservative outward distance for admission; native stops round inward
        # (long UP / short DOWN) and can tighten by a tick. Never manufacture room.
        stop=(math.floor(g['stop']/tick+1e-10) if side=='long' else math.ceil(g['stop']/tick-1e-10))*tick
        distance=(1 if side=='long' else -1)*(rate-stop)/rate
        if not .003<=distance<=.025:return None
        if getattr(self.config.get('runmode'),'value',self.config.get('runmode'))=='dry_run':
            if not self._source_health.startswith('PUBLIC_RECEIPT_CLOCK_CHECKED'):return None
            age=pd.Timestamp(now)-pd.Timestamp(c['observed_at'])
            if not pd.Timedelta(0)<=age<=pd.Timedelta(hours=24):return None
        return super().risk_size(pair,now,side,rate,lev,min_stake)

    def custom_stake_amount(self,*args,**kwargs):
        # All exceptions stay inside this callback: native safe-wrapper defaults must not admit.
        try:return super().custom_stake_amount(*args,**kwargs)
        except Exception:return 0.

    def confirm_trade_entry(self,*args,**kwargs):
        try:return super().confirm_trade_entry(*args,**kwargs)
        except Exception:return False

    def custom_stoploss(self,pair,trade,current_time,current_rate,current_profit,after_fill=False,**kwargs):
        try:
            g=self.sync_trade(trade,current_time)
            if not g:return None  # preinstalled native emergency bound remains
            sign=-1 if trade.is_short else 1;stop=float(trade.get_custom_data('policy_state',{}).get('tight_stop',g['stop']))
            # Never widen during an after-fill refresh, including recovery.
            if trade.stop_loss:
                stop=max(stop,trade.stop_loss) if sign==1 else min(stop,trade.stop_loss)
            if sign*(current_rate-stop)<=0:return None
            return stoploss_from_absolute(stop,current_rate,is_short=trade.is_short,leverage=trade.leverage)
        except Exception:return None

    def custom_exit(self,pair,trade,current_time,current_rate,current_profit,**kwargs):
        # Source/account/event-store failure must not suppress price/time protective exits.
        g=trade.get_custom_data('policy_plan');s=trade.get_custom_data('policy_state',{})
        if not g:return 'geometry_unavailable'
        sign=-1 if trade.is_short else 1
        if sign*(current_rate-float(s.get('tight_stop',g['stop'])))<=0:return 'protective_level_breach'
        if sign*(current_rate-g['target'])>=0:return 'frozen_target'
        if current_time.timestamp()-s.get('first_fill',trade.open_date_utc.timestamp())>=g['max_hold_hours']*3600:return 'max_hold_'+str(g['max_hold_hours'])+'h'
        try:return super().custom_exit(pair,trade,current_time,current_rate,current_profit,**kwargs)
        except Exception:return None


class Session4Replay(PaperPolicyV4):
    """Read immutable causal feature/plan inputs; native Freqtrade still simulates portfolios."""
    @informative('1h')
    def populate_indicators_1h(self,dataframe,metadata):
        # The exact causal hourly calculations are already in the sealed cache;
        # don't recalculate an unused merge before returning that same cache.
        return dataframe
    def populate_indicators(self,d,metadata):
        pair=metadata['pair'];path=Path(self.config['session4_features'])/(pair.replace('/','_').replace(':','_')+'.pkl')
        f=pd.read_pickle(path)
        return d[['date']].merge(f,on='date',how='left',validate='one_to_one').set_axis(d.index)

    def populate_entry_trend(self,d,metadata):
        if not hasattr(self,'_replay_plans'):self._replay_plans=json.loads(Path(self.config['session4_plans']).read_text())
        plans=self._replay_plans.get(metadata['pair'],{})
        d=d.copy();d['enter_long']=0;d['enter_short']=0;d['enter_tag']='';d['policy_plan']=None
        for i,r in d.iterrows():
            g=plans.get((r.date+pd.Timedelta(minutes=15)).isoformat())
            if g:
                d.at[i,'enter_'+g['side']]=1;d.at[i,'enter_tag']=g['recipe']+':'+g.get('methodology','v4')
                d.at[i,'policy_plan']=json.dumps(g,sort_keys=True)
        return d

    def custom_stake_amount(self,pair,current_time,current_rate,proposed_stake,min_stake,max_stake,leverage,entry_tag,side,**kwargs):
        if not self.config.get('session4_constant_risk'):return super().custom_stake_amount(pair,current_time,current_rate,proposed_stake,min_stake,max_stake,leverage,entry_tag,side,**kwargs)
        try:
            g=self.row_plan(pair,current_time,side,current_rate)
            if not g:return 0.
            old=self.config['policy_notional_cap'];self.config['policy_notional_cap']=min(50.,.25/g['modeled_loss_per_notional'])
            try:return super().custom_stake_amount(pair,current_time,current_rate,proposed_stake,min_stake,max_stake,leverage,entry_tag,side,**kwargs)
            finally:self.config['policy_notional_cap']=old
        except Exception:return 0.
