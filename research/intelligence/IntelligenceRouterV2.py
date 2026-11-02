"""Native research variants. No operational allowlist or execution bridge."""
import json
from pathlib import Path
import pandas as pd
from FoundationRouterV1 import FoundationRouterM0V1
from VWAPTrendContinuationV1 import VWAPTrendContinuationV1
from LiquiditySweepReversalV1 import LiquiditySweepReversalV1
from intelligence_features import COST,match,research_plan,profiles


class IntelligenceCostV2(FoundationRouterM0V1):
    selection='absolute'
    matching='legacy'
    target_mode='fixed'
    retrace=False

    def version(self): return 'intelligence-v2-preregistered'

    def populate_indicators(self,dataframe,metadata):
        return profiles(super().populate_indicators(dataframe,metadata))

    def populate_entry_trend(self,d,metadata):
        d=d.copy(); cfg=self.config
        parents={recipe:cls(cfg).populate_entry_trend(d.copy(),metadata) for recipe,cls in
            [('vwap',VWAPTrendContinuationV1),('sweep',LiquiditySweepReversalV1)]}
        absolute=json.loads(Path(cfg['bonus_schedule']).read_text())['decisions']
        signed=json.loads(Path(cfg['intelligence_schedule']).read_text())['decisions']
        d['enter_long']=0; d['enter_short']=0; d['enter_tag']=''; d['bonus_plan']=None
        d['parent_candidate']=0; d['bonus_reason']='NO_SETUP'; d['bonus_recipe']=''; d['candidate_details']=None
        possible=parents['vwap'].enter_long.eq(1)|parents['vwap'].enter_short.eq(1)|parents['sweep'].enter_long.eq(1)|parents['sweep'].enter_short.eq(1)
        for idx,row in d.loc[possible].iterrows():
            at=(row.date+pd.Timedelta(minutes=15)).isoformat(); results=[]; admitted=[]
            for recipe,p in parents.items():
                for side in ('long','short'):
                    if p.at[idx,'enter_'+side]!=1: continue
                    reason='TRADE'
                    if self.matching=='legacy' and ((recipe=='vwap') != (row.adx_1h>=25)):
                        reason='REJECT_LEGACY_REGIME'
                    elif self.matching!='legacy':
                        q=match(row,recipe,side,self.matching=='structure')
                        if q!='MATCH': reason=q
                    if reason=='TRADE' and self.selection!='all':
                        selected=absolute.get(at,{}).get('selected',[]) if self.selection=='absolute' else signed.get(at,{}).get('slots',{}).get(recipe+':'+side,[])
                        if metadata['pair'] not in selected: reason='REJECT_SELECTION'
                    g=research_plan(row,recipe,side,self.target_mode,self.retrace)
                    if reason=='TRADE' and g is None: reason='REJECT_COST_OR_TARGET_GEOMETRY'
                    results.append(dict(recipe=recipe,side=side,reason=reason,plan=g))
                    if reason=='TRADE': admitted.append((recipe,side,g))
            d.at[idx,'parent_candidate']=1
            if len({p[1] for p in admitted})>1:
                for item in results:
                    if item['reason']=='TRADE': item['reason']='REJECT_CONFLICTING_SIDES'
                admitted=[]
            # If both recipes agree, continuation has precedence; no double order.
            if admitted:
                recipe,side,g=admitted[0]
                d.at[idx,'enter_'+side]=1; d.at[idx,'enter_tag']=recipe+':intelligence-v2'
                d.at[idx,'bonus_plan']=json.dumps(g,sort_keys=True)
                d.at[idx,'bonus_recipe']=recipe; d.at[idx,'bonus_reason']='TRADE'
            elif results:
                d.at[idx,'bonus_recipe']=results[0]['recipe']; d.at[idx,'bonus_reason']=results[0]['reason']
            d.at[idx,'candidate_details']=json.dumps(results,sort_keys=True)
        return d

    def row_plan(self,pair,now,side,rate):
        row=self.signal_row(pair,now,side)
        if row is None or not isinstance(row.get('bonus_plan'),str): return None
        g=json.loads(row.bonus_plan); sign=1 if side=='long' else -1
        if abs(rate/g['reference']-1)>min(.0015,.25*row.atr14/g['reference'])+1e-12: return None
        loss=sign*(rate-g['stop'])/rate; reward=sign*(g['target']-rate)/rate
        if not .003<=loss<=.025 or (reward-COST)/(loss+COST)<1.25: return None
        return g|dict(risk_fraction=loss,modeled_loss_per_notional=loss+COST,after_cost_rr=(reward-COST)/(loss+COST))

    def custom_entry_price(self,pair,trade,current_time,proposed_rate,entry_tag,side,**kwargs):
        row=self.signal_row(pair,current_time,side)
        return json.loads(row.bonus_plan)['reference'] if row is not None and isinstance(row.get('bonus_plan'),str) else proposed_rate

    def confirm_trade_entry(self,pair,order_type,amount,rate,time_in_force,current_time,entry_tag,side,**kwargs):
        # Parent callback already invokes V2 row_plan. Its reserve of 0.0335 is
        # raised to 0.0338 by an additional bounded native exposure check.
        from freqtrade.persistence import Trade
        ok=super().confirm_trade_entry(pair,order_type,amount,rate,time_in_force,current_time,entry_tag,side,**kwargs)
        if not ok: return False
        g=self.row_plan(pair,current_time,side,rate)
        return sum(float(t.stake_amount)*(.03+COST) for t in Trade.get_open_trades())+amount*rate*g['modeled_loss_per_notional']<=float(self.wallets.get_total_stake_amount())*.005


class IntelligenceSignedV2(IntelligenceCostV2):
    selection='signed'


class IntelligenceRegimeV2(IntelligenceSignedV2):
    matching='regime'


class IntelligenceAllV2(IntelligenceRegimeV2):
    selection='all'


class IntelligenceStructureV2(IntelligenceRegimeV2):
    matching='structure'


class IntelligenceProfileV2(IntelligenceRegimeV2):
    target_mode='profile'


class IntelligenceTargetV2(IntelligenceRegimeV2):
    target_mode='target'


class IntelligenceNearestV2(IntelligenceRegimeV2):
    target_mode='nearest'


class IntelligenceEntryV2(IntelligenceRegimeV2):
    retrace=True
