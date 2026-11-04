"""Explicit H1 expiry plumbing repair and native terminal-order observation.

Original runner, results, source seals and failed expiry trials remain immutable.
No threshold or price/stop/target rule changes. The native configuration's entry
timeout must agree with the already preregistered 30-minute plan expiry.
"""
from diagnosis_common import *

def run(cohort,variant,fee=.00075,detail=False,short=False,through=False,replay_id='expiry-corrected'):
    from freqtrade.commands import optimize_commands
    from freqtrade.optimize.backtesting import Backtesting
    from policy_features import execution_plan
    from PolicyV3 import PolicyFixedV3
    from diagnosis_native import native
    import pandas as pd
    amendment=read(OUT/'execution-addendum-001.json')
    if sha(Path(__file__))!=amendment['adapter_sha256']:raise ValueError('unsealed expiry adapter')
    original_config=optimize_commands.setup_optimize_configuration
    def configured(args,mode):
        if variant=='passive-30m':
            path=Path(args['config'][0]);cfg=read(path)
            cfg['unfilledtimeout']=dict(cfg['unfilledtimeout'],entry=30)
            write(path,cfg)
        return original_config(args,mode)
    original_manage=Backtesting.manage_open_orders;original_timeout=PolicyFixedV3.check_entry_timeout
    callbacks=[];terminals=[]
    def timeout(self,pair,trade,order,current_time,**kwargs):
        answer=original_timeout(self,pair,trade,order,current_time,**kwargs)
        callbacks.append(dict(pair=pair,trade_id=trade.id,order_id=order.order_id,at=current_time.isoformat(),cancel=bool(answer)))
        return answer
    def managed(self,trade,current_time,row):
        pending=[o for o in trade.orders if o.ft_order_side==trade.entry_side and not o.filled]
        before=len(callbacks);answer=original_manage(self,trade,current_time,row)
        if answer:
            for order in pending:
                age=(current_time-order.order_date_utc).total_seconds()/60
                terminals.append(dict(pair=trade.pair,trade_id=trade.id,order_id=order.order_id,created_at=order.order_date_utc.isoformat(),
                    terminal_at=current_time.isoformat(),age_minutes=age,native_entry_timeout_minutes=self.config['unfilledtimeout']['entry'],
                    native_terminal='REMOVED_UNFILLED_ENTRY',custom_timeout_callbacks=callbacks[before:],
                    classification='NATIVE_REMOVAL_OBSERVED;ORIGINAL_ORDER_OBJECT_STATUS_MAY_REMAIN_OPEN'))
        return answer
    optimize_commands.setup_optimize_configuration=configured;Backtesting.manage_open_orders=managed;PolicyFixedV3.check_entry_timeout=timeout
    try:native(cohort,variant,fee,detail,short,through,replay_id)
    finally:
        optimize_commands.setup_optimize_configuration=original_config;Backtesting.manage_open_orders=original_manage;PolicyFixedV3.check_entry_timeout=original_timeout
    label=f'{cohort}-{variant}'+('-oct5' if short else '')+('-detail5m' if detail else '')+('-through' if through else '-touch')+'-'+str(round(fee*1e6))+'-'+replay_id
    write(OUT/'native'/label/'entry-lifecycle.json',dict(addendum_sha256=sha(OUT/'execution-addendum-001.json'),adapter_sha256=sha(Path(__file__)),
        configured_entry_timeout_minutes=30 if variant=='passive-30m' else 5,terminal_events=terminals,custom_callback_events=callbacks,
        interpretation='Observed native removal supplies terminal time; the retained original native Order object can still say open after it is removed from the simulated trade.'))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('cohort',choices=['development','earlier','later']);p.add_argument('variant');p.add_argument('--fee',type=float,default=.00075)
    p.add_argument('--detail',action='store_true');p.add_argument('--short',action='store_true');p.add_argument('--through',action='store_true');p.add_argument('--replay-id',default='expiry-corrected')
    a=p.parse_args();run(a.cohort,a.variant,a.fee,a.detail,a.short,a.through,a.replay_id)
