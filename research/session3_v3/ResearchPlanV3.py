"""Offline native lifecycle for source-sealed v3 plans, reusing existing Freqtrade callbacks."""
import hashlib
import json
from pathlib import Path
import sys
import pandas as pd
from freqtrade.enums import RunMode

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research/local_recovery'))
from SetupFirst5mV1 import SetupFirst5mV1


class ResearchPlanV3(SetupFirst5mV1):
    family=None
    variant=None

    def version(self):return '3.0.2-research'

    def bot_start(self, **kwargs):
        if self.config.get('runmode')!=RunMode.BACKTEST or self.config.get('dry_run') is not True:
            raise ValueError('OFFLINE_BACKTEST_ONLY')
        path=Path(self.config['recovery_plans'])
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=self.config['plan_sha256']:
            raise ValueError('FROZEN_PLAN_INTEGRITY')
        super().bot_start(**kwargs)
        for p in self.plans.values():
            if p['family']!=self.family or p['variant']!=self.variant or p['feature_version']!='multi-playbook-v3.0.2':
                raise ValueError('WRONG_PLAYBOOK_OR_VARIANT')
            if (p['diagnostics']!='GEOMETRY_PASS_RESEARCH_ONLY' or p['leverage']!=1
                    or p['notional_cap']!=25 or p['execution_authority']!='NONE'
                    or pd.Timestamp(p['boundary_known_at'])>pd.Timestamp(p['decision_at'])
                    or pd.Timestamp(p['earliest_order_at'])!=pd.Timestamp(p['decision_at'])
                    or not 0<p['max_hold_minutes']<=900):
                raise ValueError('INVALID_PLAN_AUTHORITY_OR_TIMING')

    def custom_stake_amount(self,pair,current_time,current_rate,proposed_stake,min_stake,max_stake,
                            leverage,entry_tag,side,**kwargs):
        p=self.plans.get(entry_tag)
        if not p or leverage!=1:return 0.
        risk=abs(current_rate-p['stop'])/current_rate+p['admission_cost_allowance']
        amount=min(25.,max_stake,2.5/risk)
        return 0. if min_stake is not None and amount<min_stake else amount

    def confirm_trade_entry(self,pair,order_type,amount,rate,time_in_force,current_time,entry_tag,side,**kwargs):
        p=self.plans.get(entry_tag)
        if not p or p['family']!=self.family or p['variant']!=self.variant:return False
        if not super().confirm_trade_entry(pair,order_type,amount,rate,time_in_force,current_time,entry_tag,side,**kwargs):return False
        sign=1 if side=='long' else -1
        return .0025<=sign*(rate-p['stop'])/rate<=.025 and pd.Timestamp(current_time)<pd.Timestamp(p['expires_at'])

    def custom_exit(self,pair,trade,current_time,current_rate,current_profit,**kwargs):
        # Full stop/target only; no untested partial/breakeven claim. Existing M0 callbacks
        # retain frozen plan prices. Thesis invalidation is distinct from protective stop.
        reason=super().custom_exit(pair,trade,current_time,current_rate,current_profit,**kwargs)
        if reason:return reason
        p=self.plans[trade.enter_tag]
        # Predeclared progress timeout: four hours continuation / two hours reversal;
        # exit only if no positive progress at this completed-bar decision.
        progress_minutes=240 if self.family=='BREAKOUT_RETEST' else 120
        if (pd.Timestamp(current_time)>=pd.Timestamp(trade.open_date_utc)+pd.Timedelta(minutes=progress_minutes)
                and current_profit<=0):return 'NO_PROGRESS_TIMEOUT'
        return None
