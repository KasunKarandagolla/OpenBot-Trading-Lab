"""Independent Decimal reconciliation: no strategy, candle reader or economics import."""
import csv
from decimal import Decimal as D
from bonus_common import *


def reconcile():
    check();results={}
    for name in spec()['variants']:
        path=OUT/'native-results'/(name+'.json')
        result=read(path)['strategy'][name];net=D(0);gross=D(0);fees=D(0);funding=D(0);maximum=D(0)
        for t in result['trades']:
            orders=t['orders'];entries=[o for o in orders if o['ft_is_entry']];exits=[o for o in orders if not o['ft_is_entry']]
            amount=sum(D(str(o['amount'])) for o in entries)
            entry=sum(D(str(o['amount']))*D(str(o['safe_price'])) for o in entries)/amount
            sign=D(-1 if t['is_short'] else 1)
            g=sum(sign*D(str(o['amount']))*(D(str(o['safe_price']))-entry) for o in exits)
            f=sum(D(str(o['amount']))*D(str(o['safe_price']))*D(str(t['fee_open'] if o['ft_is_entry'] else t['fee_close'])) for o in orders)
            u=D(str(t.get('funding_fees',0) or 0));p=D(str(t['profit_abs']))
            if abs(sum(D(str(o['amount'])) for o in exits)-amount)>D('0.00000001'):raise ValueError('unbalanced native fill quantity')
            residual=abs(p-(g-f+u));maximum=max(maximum,residual)
            if residual>D('.00001'):raise ValueError('independent trade reconciliation failure')
            net+=p;gross+=g;fees+=f;funding+=u
        with (OUT/'trade-ledgers'/(name+'.csv')).open() as file:
            rows=list(csv.DictReader(file));ledger=sum(D(r['net_usdt']) for r in rows)
        if len(rows)!=len(result['trades']) or abs(net-ledger)>D('.000001'):raise ValueError('ledger/native mismatch')
        results[name]={'trades':len(rows),'native_net_usdt':str(net),'fill_gross_usdt':str(gross),
                       'fill_fees_usdt':str(fees),'funding_signed_usdt':str(funding),
                       'aggregate_residual_usdt':str(net-(gross-fees+funding)),
                       'maximum_trade_residual_usdt':str(maximum),'pass':True}
    obj={'method':'Independent Decimal native-order accounting; no candle reads, strategy execution or shared PnL helper',
         'all_pass':True,'variants':results}
    write(OUT/'independent-reconciliation.json',obj);print(json.dumps(obj,indent=2));return obj
