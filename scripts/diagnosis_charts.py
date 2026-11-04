"""Reproducible actual-candle cases; known geometry is separated from future paths."""
import json
from datetime import datetime,timedelta
from diagnosis_common import *

def export():
    from diagnosis_audit import candles,clean
    import pandas as pd
    rows=[r for r in read(OUT/'trade-forensics.json') if r['source_strategy']=='v4']
    changed=read(OUT/'structural-changes.json');missed=read(OUT/'passive-missed.json')
    bykey={r['key']:r for r in rows}
    selections=[('largest-winner',max(rows,key=lambda r:r['ledger']['net'])['key']),
        ('first-protective-loss',next(r['key'] for r in rows if r['ledger']['exit_reason']=='stop_loss')),
        ('largest-missed-passive-winner',max(missed,key=lambda r:r['original_v4_net'])['key'])]
    selections.extend(('structural-change-'+str(i+1),x['key']) for i,x in enumerate(changed))
    root=WORK/'chart-inputs';root.mkdir(parents=True,exist_ok=True);index=[]
    for name,key in selections:
        r=bykey[key];g=r['plan'];at=pd.Timestamp(g['available_at']);end=pd.Timestamp(r['trade']['close_date'])
        alternative=next((x for x in changed if x['key']==key),None)
        if alternative:end=max(end,pd.Timestamp(alternative['structural']['trade']['close_date']))
        z=candles(r['trade']['pair']);z=z.loc[(z.date>=at-pd.Timedelta(hours=3))&(z.date<end+pd.Timedelta(hours=3))]
        data=dict(name=name,key=key,pair=r['trade']['pair'],plan=g,trade=r['trade'],alternative=alternative,
            candles=clean(z[['date','open','high','low','close']].to_dict('records')),
            interpretation='Actual original15m OHLCV. Gray future region starts at the decision; entry/stop/TP/frozen boundary were known then. Candles cannot reveal exchange queue or exact within-bar order. Post-exit movement is hindsight only.')
        write(root/(name+'.json'),clean(data));index.append(dict(name=name,key=key,input=str((root/(name+'.json')).relative_to(ROOT)),input_sha256=sha(root/(name+'.json'))))
    write(OUT/'chart-index.json',dict(cases=index,interpretation='Case selection is descriptive hindsight, including all six structural changes. No chart-derived rule or profit estimate.'))

def plot():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as md
    from matplotlib.patches import Rectangle
    root=OUT/'charts';root.mkdir(parents=True,exist_ok=True)
    for path in sorted((WORK/'chart-inputs').glob('*.json')):
        x=read(path);g=x['plan'];t=x['trade'];at=datetime.fromisoformat(g['available_at']);fig,ax=plt.subplots(figsize=(12,5.5))
        dates=[datetime.fromisoformat(c['date']) for c in x['candles']]
        for c,date in zip(x['candles'],dates):
            a=md.date2num(date);color='#07856a' if c['close']>=c['open'] else '#bc3545'
            ax.vlines(a,c['low'],c['high'],color=color,linewidth=.7)
            height=max(abs(c['close']-c['open']),abs(c['open'])*.00001)
            ax.add_patch(Rectangle((a-.0035,min(c['open'],c['close'])),.007,height,facecolor=color,edgecolor=color))
        ax.axvspan(at,dates[-1]+timedelta(minutes=15),color='#d8dce1',alpha=.35,label='Subsequent prices (hindsight)')
        alt=x.get('alternative');boundary=alt['structural']['plan'].get('boundary') if alt else g.get('boundary')
        for price,color,label in [(g['reference'],'#2365aa','Frozen entry reference'),(g['stop'],'#ba2135','Original protective stop'),(g['target'],'#087a48','Fixed original TP'),(boundary,'#8c6ab1','Challenger frozen VWAP reference' if alt else 'Frozen thesis boundary')]:
            if price:ax.axhline(price,color=color,lw=1,ls='--',label=label)
        ax.axvline(at,color='black',lw=1,label='Decision / available closed inputs')
        end=datetime.fromisoformat(t['close_date']);ax.scatter([end],[t['close_rate']],color='black',marker='x',s=60,zorder=5,label='V4 modeled exit')
        a=x.get('alternative')
        if a:
            # The schema includes complete original/challenger rows; select the structural record.
            alternative=a.get('structural',a.get('challenger',{}));tr=alternative.get('trade',{})
            if tr:ax.scatter([datetime.fromisoformat(tr['close_date'])],[tr['close_rate']],color='#c66d00',marker='D',s=25,zorder=5,label='Structural modeled exit')
        ax.set_title(f"{x['pair']} | {g['side']} {g['recipe']} | {x['name']}\nDecision {at.isoformat()} · V4 net {t['profit_abs']:+.6f} USDT")
        ax.set_ylabel('Quoted USDT price');ax.set_xlabel('UTC · 15-minute original candles · range touches do not establish queue fills')
        ax.xaxis.set_major_formatter(md.DateFormatter('%m-%d %H:%M',tz=at.tzinfo));ax.grid(alpha=.18);ax.legend(loc='best',fontsize=8,ncol=2)
        fig.autofmt_xdate();fig.tight_layout();fig.savefig(root/(x['name']+'.svg'))
        if x['name']=='structural-change-1':fig.savefig(WORK/'chart-preview.png',dpi=120)
        plt.close(fig)
    print('Exported actual-candle SVG cases',len(list(root.glob('*.svg'))),flush=True)

if __name__=='__main__':
    import sys
    export() if len(sys.argv)>1 and sys.argv[1]=='export' else plot()
