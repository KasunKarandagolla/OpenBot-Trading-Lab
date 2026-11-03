"""Integrated deterministic v3 candidate. Native Freqtrade owns every order.

No DCA, administrative interface, agent control or persistent activation here.
SQLite holds account checkpoints; native Trade custom_data holds position state.
"""
from datetime import timedelta
from pathlib import Path
import json
import math
import pandas as pd
from freqtrade.persistence import Trade
from freqtrade.strategy import stoploss_from_absolute
from OpportunityRouterV1 import OpportunityRouterV1
from intelligence_features import profiles, COST
from policy_features import features,raw_signals,suitability,plan,execution_plan
from policy_risk import Account,health,size
from policy_state import StateStore

class PolicyFixedV3(OpportunityRouterV1):
    use_custom_roi=True
    position_adjustment_enable=False
    max_entry_position_adjustment=0
    retrace=False
    objective=False
    stoploss=-.99  # geometry set immediately after fill; no artificial 3% leveraged stop
    trailing_stop=False
    def version(self): return 'controlled-pullback-failure-v3.0.0'
    def bot_start(self,**kwargs):
        self._store=StateStore(self.config['policy_state'])
        self._contracts=json.loads(Path(self.config['policy_contracts']).read_text())
        self._marks={}; self._risk_verdict='ACCOUNT_UNOBSERVED'
        mode=getattr(self.config.get('runmode'),'value',self.config.get('runmode'))
        if mode=='dry_run':
            from policy_paper_funding import install
            install(self.dp._exchange,self._contracts)
    def ensure_state(self):
        if not hasattr(self,'_store'): self.bot_start()
    def populate_indicators(self,d,metadata):
        return features(profiles(super().populate_indicators(d,metadata)))
    def populate_entry_trend(self,d,metadata):
        d=d.copy(); signals=raw_signals(d,self.validity(d)); schedule={}
        path=self.config.get('policy_schedule')
        if path and Path(path).exists(): schedule=json.loads(Path(path).read_text())['decisions']
        d['enter_long']=0;d['enter_short']=0;d['enter_tag']='';d['policy_plan']=None;d['policy_details']=None
        d['parent_candidate']=0;d['policy_reason']='NO_SETUP'
        possible=signals[('continuation','long')].copy()
        for mask in list(signals.values())[1:]: possible|=mask
        for idx,r in d.loc[possible].iterrows():
            results=[]; accepted=[]; at=(r.date+pd.Timedelta(minutes=15)).isoformat()
            for (recipe,side),mask in signals.items():
                if not mask.at[idx]: continue
                reason=suitability(r,recipe,side)
                g,geometry_reason=plan(r,recipe,side,self.retrace,self.objective)
                if reason=='MATCH': reason=geometry_reason
                if reason=='TRADE' and metadata['pair'] not in schedule.get(at,{}).get(recipe+':'+side,[]): reason='REJECT_SIGNED_RANK'
                results.append(dict(recipe=recipe,side=side,reason=reason,plan=g))
                if reason=='TRADE': accepted.append((recipe,side,g))
            d.at[idx,'parent_candidate']=1
            if len({s for _,s,_ in accepted})>1:
                for x in results:
                    if x['reason']=='TRADE': x['reason']='REJECT_CONFLICTING_SIDES'
                accepted=[]
            if accepted:
                recipe,side,g=accepted[0]; g['decision_id']=f"{metadata['pair']}:{recipe}:{side}:{at}"
                d.at[idx,'enter_'+side]=1; d.at[idx,'enter_tag']=recipe+':policy-v3'
                d.at[idx,'policy_plan']=json.dumps(g,sort_keys=True);d.at[idx,'policy_reason']='TRADE'
            else: d.at[idx,'policy_reason']=results[0]['reason']
            d.at[idx,'policy_details']=json.dumps(results,sort_keys=True)
        return d
    def row_plan(self,pair,now,side,rate):
        r=self.signal_row(pair,now,side)
        if r is None or not isinstance(r.get('policy_plan'),str): return None
        return execution_plan(json.loads(r.policy_plan),rate,now)
    def event_v3(self,id,kind,now,**payload):
        self.ensure_state()
        item=dict(event_id=id,event=kind,at=now.isoformat(),policy_id=self.version(),**payload)
        if self._store.event(id,item):
            p=Path(self.config['policy_events']);p.parent.mkdir(parents=True,exist_ok=True)
            with p.open('a') as f: f.write(json.dumps(item,allow_nan=False,sort_keys=True)+'\n')
    def mark(self,pair,now):
        mode=getattr(self.config.get('runmode'),'value',self.config.get('runmode'))
        if mode in ('backtest','hyperopt'):
            if pair not in self._marks:
                p=Path(self.config['policy_marks'])/(pair.replace('/','_').replace(':','_')+'-1h-mark.feather')
                self._marks[pair]=pd.read_feather(p)
            f=self._marks[pair]; q=f.loc[f.date<=pd.Timestamp(now)].tail(1)
            if q.empty or pd.Timestamp(now)-q.iloc[0].date>pd.Timedelta(hours=1): raise ValueError('historical mark unavailable')
            # Hourly OPEN only, never current candle close/high/low.
            return float(q.iloc[0].open)
        q=self.dp.ticker(pair); info=q.get('info',{})
        stamp=q.get('timestamp'); value=info.get('mark_price')
        if value is None or stamp is None or not 0<=now.timestamp()*1000-float(stamp)<=5000: raise ValueError('fresh exchange mark unavailable')
        return float(value)
    def account(self,now):
        self.ensure_state(); self.wallets.update()
        trades=Trade.get_open_trades(); closed=Trade.get_trades_proxy(is_open=False)
        cash=float(self.wallets.get_total('USDT')); free=float(self.wallets.get_free('USDT'))
        unrealized=margin=pending_margin=open_risk=pending_risk=gross=0.
        for t in trades:
            self.sync_trade(t,now)
            if t.get_custom_data('policy_funding_health',{}).get('status')=='UNKNOWN':raise ValueError('native funding accounting unavailable')
            g=t.get_custom_data('policy_plan'); sign=-1 if t.is_short else 1
            observed=sum(float(o.filled or 0)*(1 if o.ft_order_side==t.entry_side else -1) for o in t.orders)
            qty=max(observed,0.)
            reserve_qty=max(float(t.amount or 0),qty)
            entries=[o for o in t.orders if o.ft_order_side==t.entry_side and o.filled]
            filled_entry=sum(float(o.filled) for o in entries)
            entry_price=sum(float(o.filled)*float(o.safe_price) for o in entries)/filled_entry if filled_entry else t.open_rate
            # Native crystallizes open partial exits on cancellation/closure.
            # Include their observed realized result before that transition.
            cash+=sum(sign*float(o.filled or 0)*(float(o.safe_price)-entry_price)-float(o.filled or 0)*(entry_price*t.fee_open+float(o.safe_price)*t.fee_close)
                for o in t.open_orders if o.ft_order_side==t.exit_side)
            if not g: raise ValueError('frozen geometry unavailable')
            mark=self.mark(t.pair,now)
            if not math.isfinite(mark) or mark<=0: raise ValueError('invalid mark')
            unrealized+=sign*qty*(mark-entry_price)-qty*(entry_price*t.fee_open+mark*t.fee_close)+float(t.funding_fee_running or 0)
            margin+=reserve_qty*entry_price/t.leverage;gross+=reserve_qty*mark
            protective=t.get_custom_data('policy_state',{}).get('tight_stop',g['stop'])
            open_risk+=reserve_qty*(max(sign*(mark-protective),0)+mark*COST)
            for o in t.open_orders:
                if o.ft_order_side==t.entry_side:
                    remaining=max(0,float(o.amount or 0)-float(o.filled or 0)); rate=float(o.safe_price)
                    pending_margin+=remaining*rate/t.leverage
                    pending_risk+=remaining*(max(sign*(rate-g['stop']),0)+rate*COST)
                    gross+=remaining*rate
                # Pending exits retain all quantity, stop risk and margin until filled.
        checkpoint=self._store.checkpoint(now.timestamp(),cash+unrealized,closed,not trades)
        return Account(cash,unrealized,free+pending_margin,margin,pending_margin,open_risk,pending_risk,gross,gross,len(trades),
            checkpoint['day_start'],checkpoint['peak'],checkpoint['loss_streak'],checkpoint['cooldown_until'],now.timestamp(),True)
    def bot_loop_start(self,current_time,**kwargs):
        try:
            a=self.account(current_time); self._risk_verdict=health(a,current_time.timestamp())
            if current_time.timestamp()%3600==0:
                from dataclasses import asdict
                self.event_v3('account:'+current_time.isoformat(),'ACCOUNT_SNAPSHOT',current_time,account=asdict(a),equity=a.equity,verdict=self._risk_verdict)
        except Exception as e: self._risk_verdict='ACCOUNT_STATE_UNAVAILABLE:'+type(e).__name__
    def leverage(self,pair,current_time,current_rate,proposed_leverage,max_leverage,entry_tag,side,**kwargs):
        return max(1.,min(float(self.config.get('policy_leverage',1)),float(max_leverage),20.))
    def risk_size(self,pair,now,side,rate,lev,min_stake=0):
        g=self.row_plan(pair,now,side,rate)
        if not g:return None
        a=self.account(now)
        return size(a,clock=now.timestamp(),side=side,entry=rate,stop=g['stop'],leverage=lev,
            contract=self._contracts.get(pair),cap=float(self.config.get('policy_notional_cap',250)),min_margin=min_stake or 0)
    def custom_stake_amount(self,pair,current_time,current_rate,proposed_stake,min_stake,max_stake,leverage,entry_tag,side,**kwargs):
        try:
            v=self.risk_size(pair,current_time,side,current_rate,leverage,min_stake)
            return min(v['margin'],max_stake) if v and v['status']=='PASS' else 0.
        except Exception:return 0.
    def confirm_trade_entry(self,pair,order_type,amount,rate,time_in_force,current_time,entry_tag,side,**kwargs):
        try:
            lev=float(self.config.get('policy_leverage',1));g=self.row_plan(pair,current_time,side,rate)
            v=self.risk_size(pair,current_time,side,rate,lev)
            if g is None or v is None or v['status']!='PASS' or amount*rate>v['notional']+max(1e-7,v['notional']*1e-8): return False
            if any(t.pair==pair for t in Trade.get_open_trades()):return False
            # Immutable approved geometry survives a crash before the first fill.
            g.update(leverage=lev,approved_notional=amount*rate,approved_risk=amount*rate*g['modeled_loss_per_notional'])
            self._store.plan(g['decision_id'],pair,side,pd.Timestamp(g['available_at']).timestamp(),pd.Timestamp(g['expires_at']).timestamp(),g)
            self.event_v3('admit:'+g['decision_id'],'ADMITTED',current_time,decision_id=g['decision_id'],risk=v,plan=g)
            return True
        except Exception:return False
    def custom_entry_price(self,pair,trade,current_time,proposed_rate,entry_tag,side,**kwargs):
        r=self.signal_row(pair,current_time,side)
        return json.loads(r.policy_plan)['reference'] if r is not None and isinstance(r.get('policy_plan'),str) else proposed_rate
    def adjust_entry_price(self,trade,order,pair,current_time,proposed_rate,current_order_rate,entry_tag,side,**kwargs):
        return current_order_rate
    def check_entry_timeout(self,pair,trade,order,current_time,**kwargs):
        try:
            g=trade.get_custom_data('policy_plan') or self._store.find_plan(pair,'short' if trade.is_short else 'long',order.order_date_utc.timestamp())
            if not g or pd.Timestamp(current_time)>=pd.Timestamp(g['expires_at']):return True
            if float(order.filled or 0)>0:return True  # native crystallizes partial and cancels remainder
            if health(self.account(current_time),current_time.timestamp())!='PASS':return True
            row,_=self.dp.get_analyzed_dataframe(pair,self.timeframe)
            if row.empty:return True
            rate=float(row.iloc[-1].close)
            if (1 if not trade.is_short else -1)*(rate-g['stop'])<=0:return True
            return False
        except Exception:return True
    def check_exit_timeout(self,pair,trade,order,current_time,**kwargs):
        # Native cancels and rechecks deterministic exit next loop. Stops remain.
        return float(order.filled or 0)>0 or current_time-order.order_date_utc>=timedelta(minutes=5)
    def adjust_exit_price(self,trade,order,pair,current_time,proposed_rate,current_order_rate,entry_tag,side,**kwargs):
        return current_order_rate  # cancellation/replacement through native timeout only
    def sync_trade(self,trade,now):
        self.ensure_state();g=trade.get_custom_data('policy_plan')
        if g is None:
            entries=[o for o in trade.orders if o.ft_order_side==trade.entry_side]
            stamp=min((o.order_date_utc.timestamp() for o in entries),default=trade.open_date_utc.timestamp())
            g=self._store.find_plan(trade.pair,'short' if trade.is_short else 'long',stamp)
            if g: trade.set_custom_data('policy_plan',g)
        if not g:return None
        state=trade.get_custom_data('policy_state',{})
        state.setdefault('tight_stop',g['stop']);state.setdefault('entry_amount',0.);state.setdefault('exited_amount',0.)
        entry=sum(float(o.filled or 0) for o in trade.orders if o.ft_order_side==trade.entry_side)
        exited=sum(float(o.filled or 0) for o in trade.orders if o.ft_order_side==trade.exit_side)
        state['entry_amount']=max(state['entry_amount'],entry);state['exited_amount']=max(state['exited_amount'],exited)
        first=min((o.order_filled_utc.timestamp() for o in trade.orders if o.ft_order_side==trade.entry_side and o.filled and o.order_filled_utc),default=None)
        if first is not None: state.setdefault('first_fill',first)
        state['partial_done']=exited>0
        for o in trade.orders:
            if not o.filled:continue
            id=f'fill:{trade.id}:{o.order_id}:{float(o.filled)}:{o.status}'
            self.event_v3(id,'ENTRY_FILL' if o.ft_order_side==trade.entry_side else 'EXIT_FILL',now,
                decision_id=g['decision_id'],trade_id=trade.id,order_id=o.order_id,quantity=float(o.filled),
                price=float(o.safe_price),status=o.status,remaining=float(o.remaining or 0),native_simulated=True)
        trade.set_custom_data('policy_state',state)
        return g
    def order_filled(self,pair,trade,order,current_time,**kwargs):
        g=self.sync_trade(trade,current_time)
        if g and order.ft_order_side==trade.entry_side:
            s=trade.get_custom_data('policy_state');s.setdefault('first_fill',current_time.timestamp())
            if pd.Timestamp(current_time)>=pd.Timestamp(g['expires_at']):s['late_fill']=True
            trade.set_custom_data('policy_state',s)
    def custom_roi(self,pair,trade,current_time,trade_duration,entry_tag,side,**kwargs):
        g=trade.get_custom_data('policy_plan')
        return trade.calc_profit_ratio(g['target']) if g else None
    def custom_stoploss(self,pair,trade,current_time,current_rate,current_profit,after_fill=False,**kwargs):
        g=self.sync_trade(trade,current_time)
        if not g: return stoploss_from_absolute(trade.open_rate*(1+(.025 if trade.is_short else -.025)),current_rate,is_short=trade.is_short,leverage=trade.leverage)
        state=trade.get_custom_data('policy_state');sign=-1 if trade.is_short else 1;stop=state['tight_stop']
        if self.position_adjustment_enable and state.get('partial_done'):
            funding_paid=max(0,-float(trade.funding_fee_running or 0))/max(float(trade.amount),1e-12)
            # Solve remaining-lot breakeven including entry+exit fees; add friction/funding.
            reserve=.0023*trade.open_rate+funding_paid
            be=(trade.open_rate*(1+sign*trade.fee_open)+sign*reserve)/(1-sign*trade.fee_close)
            desired=be
            frame,_=self.dp.get_analyzed_dataframe(pair,self.timeframe)
            if not frame.empty:
                r=frame.iloc[-1];known=pd.Timestamp(r.date)+pd.Timedelta(minutes=15)
                if pd.Timestamp(trade.open_date_utc)<known<=pd.Timestamp(current_time) and math.isfinite(float(r.atr14)):
                    trail=float(r.close)-sign*2*float(r.atr14)
                    if sign*(trail-desired)>0:desired=trail
                    key='swing_high' if trade.is_short else 'swing_low';v=r.get(key);stamp=r.get(key+'_known_at')
                    if pd.notna(v) and pd.notna(stamp) and pd.Timestamp(trade.open_date_utc)<pd.Timestamp(stamp)<=pd.Timestamp(current_time) and sign*(float(v)-desired)>0:desired=float(v)
            if sign*(desired-stop)>0 and sign*(current_rate-desired)>0:
                stop=desired;state['tight_stop']=stop;trade.set_custom_data('policy_state',state)
                self.event_v3(f'stop:{trade.id}:{stop}','STOP_TIGHTEN',current_time,trade_id=trade.id,stop=stop,decision_id=g['decision_id'])
        if sign*(current_rate-stop)<=0:return None  # native existing stop remains; custom_exit also catches breach
        return stoploss_from_absolute(stop,current_rate,is_short=trade.is_short,leverage=trade.leverage)
    def custom_exit(self,pair,trade,current_time,current_rate,current_profit,**kwargs):
        g=self.sync_trade(trade,current_time)
        if not g:return 'geometry_unavailable'
        s=trade.get_custom_data('policy_state',{});sign=-1 if trade.is_short else 1
        if s.get('late_fill'):return 'late_fill_after_expiry'
        if sign*(current_rate-s['tight_stop'])<=0:return 'protective_level_breach'
        first=s.get('first_fill',trade.open_date_utc.timestamp())
        if current_time.timestamp()-first>=g['max_hold_hours']*3600:return 'max_hold_'+str(g['max_hold_hours'])+'h'
        frame,_=self.dp.get_analyzed_dataframe(pair,self.timeframe)
        if frame.empty:return None
        r=frame.iloc[-1];known=pd.Timestamp(r.date)+pd.Timedelta(minutes=15)
        if not pd.Timestamp(trade.open_date_utc)<known<=pd.Timestamp(current_time):return None
        if g['recipe']=='continuation' and bool(r.get('thesis_lost_'+('short' if trade.is_short else 'long'),False)):return 'closed_pullback_thesis_lost'
        if g['recipe']=='reversal' and sign*(float(r.close)-g['boundary'])<0:return 'failed_boundary_reaccepted'
        return None
    def adjust_trade_position(self,trade,current_time,current_rate,current_profit,min_stake,max_stake,current_entry_rate,current_exit_rate,current_entry_profit,current_exit_profit,**kwargs):
        if not self.position_adjustment_enable or trade.has_open_orders:return None
        g=self.sync_trade(trade,current_time)
        if not g:return None
        s=trade.get_custom_data('policy_state',{});sign=-1 if trade.is_short else 1
        # Quantity already filled, including a canceled partially-filled exit,
        # determines remaining one-third allocation. Never repeat a whole partial.
        initial=s['entry_amount'];desired=max(0,initial/3-s['exited_amount'])
        if desired<=max(1e-12,initial*1e-8) or trade.amount<=0:return None
        r=sign*(trade.open_rate-g['stop'])
        move=sign*(current_exit_rate-trade.open_rate)
        if move<1.5*r or sign*(g['target']-current_exit_rate)<=0:return None
        contract=self._contracts.get(trade.pair,{})
        step=float(contract.get('contract_size',0))*float(contract.get('step_contracts',0))
        if step<=0:return None
        qty=math.floor((min(desired,trade.amount)/step)+1e-9)*step
        minimum=float(contract.get('min_contracts',0))*float(contract.get('contract_size',0))
        reduction=trade.stake_amount*qty/trade.amount
        remaining=trade.stake_amount-reduction
        if qty<minimum or trade.amount-qty<minimum or qty*current_exit_rate<contract.get('min_notional',0):return None
        if min_stake is not None and (reduction<min_stake or remaining<min_stake):return None
        if reduction<=0 or reduction>=trade.stake_amount:return None
        return -reduction,'partial_1.5R_third_v3'

class PolicyManagedV3(PolicyFixedV3):
    position_adjustment_enable=True

class PolicyRetraceV3(PolicyFixedV3):
    retrace=True

class PolicyObjectiveV3(PolicyFixedV3):
    objective=True
