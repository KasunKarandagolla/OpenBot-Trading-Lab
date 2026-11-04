"""Hypothetical account arithmetic only; actual native execution remains1x."""
from setup_common import *
from policy_risk import Account,size
def report():
    rows=[];contracts=read(OUT/'contracts.json')
    for pair,z in read(WORK/'plans/setup.json').items():
        for at,g in z.items():
            clock=__import__('datetime').datetime.fromisoformat(at).timestamp()
            a=Account(cash=1000,unrealized_net=0,free_collateral=1000,posted_margin=0,pending_margin=0,open_risk=0,pending_risk=0,gross_notional=0,correlated_notional=0,positions=0,day_start_equity=1000,peak_equity=1000,asof=clock)
            for lev in [1,10,20]:
                v=size(a,clock=clock,side=g['side'],entry=g['reference'],stop=g['stop'],leverage=lev,contract=contracts[pair],cap=min(25,.25/g['modeled_loss_per_notional']))
                rows.append(dict(pair=pair,at=at,leverage=lev,intended_modeled_risk_target=.25,structural_stop=g['stop'],result=v,
                    maintenance_margin=(v['notional']*v['tier']['maintenance_rate'] if v.get('tier') else None),
                    roundtrip_fee_scenario=(v['notional']*.0015 if v.get('notional') else None),
                    adverse_1percent_gap_beyond_stop_modeled_loss=(v['planned_loss']+v['notional']*.01 if v.get('notional') else None)))
    write(OUT/'hypothetical-leverage.json',dict(executed_leverage=1,hypothetical_only=True,rows=rows,
        qualification='Current public specifications, not historical tiers or observed liquidation/gap fills; leverage never changes the structural stop or approved monetary-risk cap. No exchange orders or active leverage changes.'))
if __name__=='__main__':report()
