"""Source-candle casebook figures. Run on a host with matplotlib after review.

Entry figures consume only pre-cutoff arrays and never reference trade outcomes.
Subsequent path figures are distinct artifacts and explicitly label hindsight.
"""
import json
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as dates
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/master-audit/charts'


def candles(axis,rows,minutes):
    frame=pd.DataFrame(rows)
    if frame.empty:
        axis.text(.5,.5,'No source candles',transform=axis.transAxes);return
    stamp=pd.to_datetime(frame.date,utc=True)
    x=dates.date2num(stamp)
    width=minutes/1440*.7
    for at,(_,row) in zip(x,frame.iterrows()):
        color='#168274' if row.close>=row.open else '#c15155'
        axis.vlines(at,row.low,row.high,color=color,linewidth=.8)
        axis.add_patch(Rectangle((at-width/2,min(row.open,row.close)),width,
                                max(abs(row.close-row.open),(row.high-row.low)*.015),
                                color=color,alpha=.85))
    axis.autoscale_view()
    if 'vwap' in frame:
        axis.plot(x,frame.vwap,color='#335fc9',linewidth=1,label='Session VWAP')
    axis.xaxis_date()
    axis.xaxis.set_major_formatter(dates.DateFormatter('%d %b\n%H:%M',tz=stamp.dt.tz))
    axis.grid(alpha=.18)
    axis.set_ylabel('Gate USDT price')


def levels(axis,item):
    plan=item.get('plan')
    if plan:
        for key,color in [('reference','#425466'),('stop','#c15155'),('target','#168274')]:
            axis.axhline(plan[key],color=color,ls='--',lw=.9,label=key)
    for obstacle in item['obstacles'][:3]:
        axis.axhline(obstacle['value'],color='#bc8625',ls=':',lw=.7,label=obstacle['source'])


def entry_chart(item):
    at=pd.Timestamp(item['at'])
    for key,minutes in [('entry_15m',15),('entry_1h',60)]:
        assert all(pd.Timestamp(row['date'])+pd.Timedelta(minutes=minutes)<=at for row in item[key])
    fig,axes=plt.subplots(2,1,figsize=(11,7.5),layout='constrained')
    candles(axes[0],item['entry_15m'],15);levels(axes[0],item)
    candles(axes[1],item['entry_1h'],60)
    info=item['information_at_entry']
    axes[0].set_title('15m information available at decision cutoff')
    axes[1].set_title(f"Closed 1h context | ADX {info['adx_1h']:.1f} | structure {info['struct_direction_1h']}")
    handles,labels=axes[0].get_legend_handles_labels()
    if handles:axes[0].legend(handles,labels,loc='best',fontsize=7,ncol=3)
    fig.suptitle(f"{item['case_id']} · {item['symbol']} · {item['side']} {item['recipe']}\nENTRY INFORMATION ONLY · as of {at.strftime('%Y-%m-%d %H:%M')} UTC",fontsize=11)
    fig.savefig(OUT/(item['case_id']+'-entry.png'),dpi=145)
    plt.close(fig)


def path_chart(item):
    fig,axis=plt.subplots(figsize=(11,4.8),layout='constrained')
    candles(axis,item['path'],15);levels(axis,item)
    axis.axvline(dates.date2num(pd.Timestamp(item['at'])),color='#425466',ls='--',lw=1,label='decision')
    for label,trade,color in [('router',item.get('trade'),'#c15155'),('parent',item.get('parent'),'#7338a0')]:
        if not trade:continue
        at=dates.date2num(pd.Timestamp(trade['close_date']))
        axis.scatter(at,trade['close_rate'],color=color,marker='x',s=55,zorder=5,
                     label=f"{label} exit: {trade['exit_reason']} ({trade['profit_abs']:+.4f} USDT)")
    axis.legend(loc='best',fontsize=7,ncol=2)
    axis.set_title(f"{item['case_id']} · {item['symbol']} · SUBSEQUENT PRICE PATH / HINDSIGHT\n15m candles do not establish queue fills or intrabar order",fontsize=10)
    fig.savefig(OUT/(item['case_id']+'-path.png'),dpi=145)
    plt.close(fig)


def main():
    OUT.mkdir()  # refuse overwrite
    items=json.loads((ROOT/'work/master-chart-data.json').read_text())
    for item in items:
        entry_chart(item);path_chart(item)
    print(len(items)*2,'figures; entry and outcome paths separated')


if __name__=='__main__':
    main()
