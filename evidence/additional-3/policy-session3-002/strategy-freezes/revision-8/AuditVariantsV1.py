"""Predeclared development ablations, all native M0 and research-only.

These candidates have no operational allowlist entry and no profitability label.
Frozen bonus and parent strategy sources remain unchanged.
"""
from datetime import timedelta
import json
import math
from pathlib import Path
import pandas as pd
from OpportunityRouterV1 import RouterOnlyV1
from VWAPTrendContinuationV1 import VWAPTrendContinuationV1
from LiquiditySweepReversalV1 import LiquiditySweepReversalV1


class AuditStructuralCloseM0V1(RouterOnlyV1):
    """Replace only the ADX/opposite-direction exit with a frozen-level breach.

The native initial stop remains active and will generally execute first. This
is effectively removal of the nonstructural early exit, not a tighter stop.
"""
    position_adjustment_enable=False

    def version(self):
        return 'master-structural-close-1.0.0'

    def custom_exit(self,pair,trade,current_time,current_rate,current_profit,**kwargs):
        geometry=trade.get_custom_data('bonus_plan')
        if not geometry:
            return 'geometry_unavailable'
        sign=-1 if trade.is_short else 1
        if sign*(current_rate-geometry['target'])>=0:
            return 'frozen_target'
        if current_time-trade.open_date_utc>=timedelta(hours=geometry['max_hold_hours']):
            return 'max_hold_'+str(geometry['max_hold_hours'])+'h'
        frame,_=self.dp.get_analyzed_dataframe(pair,self.timeframe)
        if not frame.empty:
            row=frame.iloc[-1]
            known=pd.Timestamp(row.date)+pd.Timedelta(minutes=15)
            # A pre-entry or unclosed bar cannot be new thesis invalidation.
            if (pd.Timestamp(trade.open_date_utc)<known<=pd.Timestamp(current_time)
                    and math.isfinite(float(row.close))
                    and sign*(float(row.close)-geometry['stop'])<=0):
                return 'frozen_structure_close_invalidated'
        return None


class AuditNearestObjectiveM0V1(RouterOnlyV1):
    """Conservative nearest-known-obstacle test, no posthoc breakout exception."""
    position_adjustment_enable=False

    def version(self):
        return 'master-nearest-objective-1.0.0'

    def populate_entry_trend(self,dataframe,metadata):
        frame=super().populate_entry_trend(dataframe,metadata)
        for idx,row in frame.loc[frame.bonus_reason.eq('TRADE')].iterrows():
            geometry=json.loads(row.bonus_plan)
            sign=-1 if geometry['side']=='short' else 1
            suffix='low' if sign==-1 else 'high'
            reference=geometry['reference']
            choices=[('original_2R',geometry['target'])]
            for key in ['prior_day_'+suffix,'prior_swing_'+suffix,'vp_val' if sign==-1 else 'vp_vah']:
                value=row.get(key)
                if pd.notna(value) and math.isfinite(float(value)) and sign*(float(value)-reference)>0:
                    choices.append((key,float(value)))
            origin,target=min(choices,key=lambda item:sign*(item[1]-reference))
            rr=(sign*(target-reference)/reference-.0035)/(geometry['risk_fraction']+.0035)
            if rr<1.25:
                frame.at[idx,'enter_long']=frame.at[idx,'enter_short']=0
                frame.at[idx,'bonus_plan']=None
                frame.at[idx,'bonus_reason']='AUDIT_NEAREST_OBJECTIVE_ROOM'
            else:
                geometry.update(target=target,target_origin=origin,after_cost_rr=rr)
                frame.at[idx,'bonus_plan']=json.dumps(geometry,sort_keys=True)
        return frame


class _RankingOnly:
    """Parent signals and management unchanged; only top-three ranking added."""
    def populate_entry_trend(self,dataframe,metadata):
        frame=super().populate_entry_trend(dataframe,metadata)
        schedule=json.loads(Path(self.config['bonus_schedule']).read_text())['decisions']
        mask=[metadata['pair'] in schedule.get((at+pd.Timedelta(minutes=15)).isoformat(),{}).get('selected',[])
              for at in frame.date]
        frame.loc[[not x for x in mask],['enter_long','enter_short']]=0
        return frame


class AuditRankingVWAPV1(_RankingOnly,VWAPTrendContinuationV1):
    pass


class AuditRankingSweepV1(_RankingOnly,LiquiditySweepReversalV1):
    pass


class AuditRegimeOnlyM0V1(RouterOnlyV1):
    """Remove ranking only; keep router geometry, regime and management intact.

    This is not pure regime attribution against the original parent portfolio:
    router geometry and management remain confounders, explicitly reported.
    """
    pass  # Runner supplies the all-market schedule before native resolution.


class AuditRegimeVWAPV1(VWAPTrendContinuationV1):
    """Pure parent regime filter: parent geometry/exits/capital rules retained."""
    def populate_entry_trend(self,dataframe,metadata):
        frame=super().populate_entry_trend(dataframe,metadata)
        frame.loc[~frame.adx_1h.ge(25),['enter_long','enter_short']]=0
        return frame


class AuditRegimeSweepV1(LiquiditySweepReversalV1):
    """Pure parent regime filter: no ranking, router geometry or new exits."""
    def populate_entry_trend(self,dataframe,metadata):
        frame=super().populate_entry_trend(dataframe,metadata)
        frame.loc[~frame.adx_1h.lt(25),['enter_long','enter_short']]=0
        return frame
