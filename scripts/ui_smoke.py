"""Local authenticated HTTP checks. Never prints passwords or tokens."""
import base64
import json
from pathlib import Path
import urllib.request
import urllib.error
from datetime import datetime,timezone
root=Path(__file__).resolve().parents[1]
api=json.loads((root/'user_data/runtime/api.json').read_text())['api_server']
base='http://127.0.0.1:8080'
records=[]

def call(path, headers=None, method='GET', expect=200):
    request=urllib.request.Request(base+path,headers=headers or {},method=method)
    try:
        response=urllib.request.urlopen(request,timeout=15)
        status=response.status;data=response.read()
    except urllib.error.HTTPError as e:
        status=e.code;data=e.read()
    records.append({'path':path,'method':method,'status':status,'expected':expect,'pass':status==expect})
    if status != expect: raise ValueError('HTTP smoke failed: '+path+' '+str(status))
    return data

html=call('/')
assert b'<html' in html.lower() and b'<script' in html.lower()
import re
assets=re.findall(rb'(?:src|href)=[\"\']([^\"\']+\.(?:js|css))',html)
asset_sizes={}
for asset in assets:
    path=asset.decode()
    if path.startswith('/'):
        asset_sizes[path]=len(call(path))
call('/api/v1/ping')
call('/api/v1/version',expect=401)
credential=base64.b64encode((api['username']+':'+api['password']).encode()).decode()
token=json.loads(call('/api/v1/token/login',{'Authorization':'Basic '+credential},'POST'))['access_token']
headers={'Authorization':'Bearer '+token}
version=json.loads(call('/api/v1/version',headers))
history=json.loads(call('/api/v1/backtest/history',headers))
assert history, 'native history not visible'
item=history[0]
from urllib.parse import urlencode
strategy=item.get('strategy','TrendPullbackBaselineV1')
filename=item.get('filename') or item.get('file')
if not filename: raise ValueError('unknown history schema; inspect only public result metadata')
result=json.loads(call('/api/v1/backtest/history/result?'+urlencode({'filename':filename,'strategy':strategy}),headers))
native=result['backtest_result']['strategy'][strategy]
assert native['total_trades'] == 386, 'expected committed baseline result'
summary={'backtest_result_trade_count':native['total_trades'],'static_assets_bytes':asset_sizes,'checked_utc':datetime.now(timezone.utc).isoformat(),'records':records,
         'static_ui_html_bytes':len(html),'engine_version_response':version,
         'backtest_history_entries':len(history),'history_example':item,
         'result_top_level_keys':sorted(result),
         'verification':'Authenticated HTTP and supported backtest-history/result endpoints; graphical browser rendering not observed.',
         'tokens_redacted':True}
(root/'evidence/session-1/ui-http-smoke.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
