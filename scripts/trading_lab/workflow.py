"""Owner CLI and bounded Shared inbox. No OpenBot database writes or shell API."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import shutil
import tempfile
import time

from binance_research_data import DataError
import openbot_current_market as previous
from trading_lab.public import capture, write_new, milliseconds
from trading_lab.charts import render
from trading_lab.risk import validate_market_plan, historical_geometry
from trading_lab.execution import readiness

ID = re.compile('[A-Za-z0-9-]{1,80}')


def safe_id(value):
    if not isinstance(value,str) or not ID.fullmatch(value):
        raise DataError('INVALID_IDENTIFIER')
    return value


def build_all(raw, destination):
    destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=True)
    source=previous.load(Path(raw)/'capture.json')
    packets=[]
    default_charts={}
    for symbol in source['ranked']:
        previous.build(Path(raw),destination,selected_symbol=symbol)
    for packet in sorted(destination.iterdir()):
        if packet.is_dir():
            packets.append(previous.verify(packet))
            identity=previous.load(packet/'candidate.json')
            charts=[]
            for tf,count,purpose in [('4h',120,'Structural context'),('1h',150,'Structural context'),
                                     ('15m',144,'Setup structure'),('5m',72,'Entry context')]:
                request={'request_id':'default-'+tf,'candidate_id':packet.name,'symbol':identity['symbol'],
                         'venue':'BINANCE_PUBLIC_USDM','cutoff_ms':identity['as_of_ms'],'timeframe':tf,
                         'visible_candles':count,'overlays':[],'volume':True,
                         'purpose':'Default research view: '+purpose+'; native interpretation pending','revision':1}
                charts.append(render(packet,request,destination.parent/'revisions'/packet.name))
            default_charts[packet.name]=charts
    result={'schema':'openbot.workflow.run.v2','as_of':source['as_of'],
            'broad_context_count':source.get('broad_context_count'),
            'exchange_symbol_count':source.get('exchange_symbol_count'),
            'packets':packets,'default_chart_receipts':default_charts,
            'ranked_symbols':source['ranked'],
            'status':'REVIEW_REQUIRED' if any(p['review_type']=='SETUP_FOR_REVIEW' for p in packets) else 'NO_OPPORTUNITY',
            'decision_basis':'FROZEN_LOCAL_RECOVERY_V1_SCREEN_ONLY_NOT_AGENT_VERDICT',
            'native_orchestration':'PENDING_OPENBOT_OWNER_RUN','demo':readiness()}
    write_new(destination.parent/'index.json',result)
    return result


def gate(packet,proposal=None,account=None,receipts=None):
    packet=Path(packet)
    seal=previous.verify(packet)
    constraints=previous.load(packet/'execution-constraints.json')
    constraints['closed_bar_source_sha256']=[previous.load(packet/'candles'/(tf+'.json'))['source']['sha256'] for tf in previous.LIMITS]
    constraints['structural_anchors']=[]
    for tf in previous.LIMITS:
        source=previous.load(packet/'candles'/(tf+'.json'))
        constraints['structural_anchors'].extend({'source_sha256':source['source']['sha256'],
            'available_at_ms':bar[6]+1,'low':bar[3],'high':bar[2]} for bar in source['bars'])
    return validate_market_plan(proposal,constraints,account,milliseconds(),receipts,seal['packet_sha256'])


def stage_run(run, shared, run_id):
    run,shared=Path(run),Path(shared)
    safe_id(run_id)
    if shared.name!='Shared' or shared.parent.name!='OpenBot' or not shared.is_dir():
        raise DataError('DISCOVERED_OPENBOT_SHARED_REQUIRED')
    index=previous.load(run/'index.json')
    for item in index['packets']:
        if previous.verify(run/'packets'/safe_id(item['candidate_id']))!=item:
            raise DataError('RUN_INDEX_PACKET_MISMATCH')
    inbox=Inbox(shared/'TradingLab-Workflow-v2')
    target=inbox.root/'runs'/run_id
    if target.exists():raise DataError('STAGED_RUN_ALREADY_EXISTS')
    files=list(run.rglob('*'))
    if any(p.is_symlink() for p in files) or sum(p.stat().st_size for p in files if p.is_file())>128*1024*1024:
        raise DataError('STAGE_SYMLINK_OR_BYTE_CAP')
    with tempfile.TemporaryDirectory(prefix='.incoming-',dir=inbox.root/'runs') as temporary:
        pending=Path(temporary)/run_id
        shutil.copytree(run,pending)
        for item in index['packets']:
            previous.verify(pending/'packets'/item['candidate_id'])
        pending.rename(target)
    age=milliseconds()-int(previous.load(run/'raw'/'capture.json')['as_of_ms'])
    return {'run_id':run_id,'packets':len(index['packets']),
            'freshness':'CURRENT_RESEARCH' if 0<=age<=180000 else 'STALE_RESEARCH_RECORD_REFRESH_BEFORE_PROPOSAL',
            'native_status':'PENDING_OPENBOT_OWNER_RUN','addon_namespace':'OpenBot/Shared/TradingLab-Workflow-v2'}


def atomic_reply(path,value):
    # The process lock serializes writers; .pending files are never consumed.
    pending=path.with_suffix('.pending')
    with pending.open('w',encoding='utf-8') as stream:
        json.dump(value,stream,sort_keys=True,indent=2,allow_nan=False)
        stream.flush();os.fsync(stream.fileno())
    os.replace(pending,path)


def lock_worker(root):
    stream=(root/'.worker.lock').open('a+b')
    try:
        if os.name=='nt':
            import msvcrt
            stream.seek(0);stream.write(b'0');stream.flush();stream.seek(0)
            msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:
        stream.close();raise DataError('BRIDGE_ALREADY_RUNNING') from None
    return stream


class Inbox:
    def __init__(self,root):
        self.root=Path(root).resolve()
        if self.root.name!='TradingLab-Workflow-v2':
            raise DataError('DEDICATED_ADDON_NAMESPACE_REQUIRED')
        self.root.mkdir(parents=True,exist_ok=True)
        for name in ['requests','replies','runs','control']:
            path=self.root/name
            if path.is_symlink():raise DataError('BRIDGE_SYMLINK_REJECTED')
            path.mkdir(exist_ok=True)

    def packet(self,payload):
        run_id=safe_id(payload['run_id']);candidate=safe_id(payload['candidate_id'])
        run=self.root/'runs'/run_id
        index=previous.load(run/'index.json')
        if candidate not in [p['candidate_id'] for p in index['packets']]:
            raise DataError('CANDIDATE_NOT_IN_RUN')
        path=run/'packets'/candidate
        if path.resolve()!=path or any(p.is_symlink() for p in [run,run/'packets',path]):
            raise DataError('BRIDGE_PACKET_SYMLINK')
        return path

    def handle(self,path,now=None):
        now=milliseconds() if now is None else now
        if path.is_symlink() or path.stat().st_size>64*1024:
            raise DataError('REQUEST_SYMLINK_OR_SIZE')
        body=path.read_bytes();digest=hashlib.sha256(body).hexdigest()
        request=json.loads(body)
        if (not isinstance(request,dict) or set(request)!={'schema','request_id','kind','created_at_ms','expires_at_ms','payload'}
                or request['schema']!='openbot.shared.request.v2'):
            raise DataError('REQUEST_SCHEMA')
        key=safe_id(request['request_id'])
        if path.name!=key+'.json':raise DataError('REQUEST_FILENAME_MISMATCH')
        reply=self.root/'replies'/(key+'.json')
        if reply.exists():
            result=previous.load(reply)
            if result['request_sha256']!=digest:raise DataError('REQUEST_ID_REUSE')
            return result
        if (type(request['created_at_ms']) is not int or type(request['expires_at_ms']) is not int
                or not request['created_at_ms']<=now<request['expires_at_ms']<=request['created_at_ms']+600_000):
            raise DataError('REQUEST_EXPIRED_FUTURE_OR_TTL')
        data=request['payload'];kind=request['kind']
        if not isinstance(data,dict):raise DataError('PAYLOAD_OBJECT_REQUIRED')
        # The versioned skill contract is also enforced at the actual transport.
        # A valid JSON object must not bypass proposal shapes or introduce accounts.
        from trading_lab.skills import validate_envelope
        validate_envelope(request, now, self.packet(data) if kind in {'CHART', 'GATE'} else None)
        if kind=='SCAN':
            if set(data)-{'universe','shortlist'}:raise DataError('SCAN_UNKNOWN_FIELD')
            run=self.root/'runs'/key
            # An interrupted capture is preserved, never overwritten/relabelled by a retry.
            if run.exists():raise DataError('INTERRUPTED_RUN_USE_NEW_REQUEST_ID')
            run.mkdir()
            capture(run/'raw',universe=data.get('universe',24),shortlist=data.get('shortlist',4))
            result=build_all(run/'raw',run/'packets')
        elif kind=='CHART':
            if set(data)!={'run_id','candidate_id','chart'}:raise DataError('CHART_PAYLOAD_FIELDS')
            packet=self.packet(data)
            result=render(packet,data['chart'],packet.parent.parent/'revisions'/packet.name)
        elif kind=='GATE':
            if set(data)-{'run_id','candidate_id','proposal','native_receipts'}:raise DataError('GATE_PAYLOAD_FIELDS')
            # Signed account state is deliberately not accepted through the agent inbox.
            result=gate(self.packet(data),data.get('proposal'),None,data.get('native_receipts'))
        elif kind=='READINESS':
            if data:raise DataError('READINESS_PAYLOAD_MUST_BE_EMPTY')
            result=readiness()
        else:
            raise DataError('OPERATION_NOT_ALLOWLISTED')
        receipt={'schema':'openbot.shared.reply.v2','request_id':key,'request_sha256':digest,
                 'observed_at_ms':milliseconds(),'status':'COMPLETE','result':result,
                 'native_message_receipt':'NOT_CREATED_BY_FILE_BRIDGE'}
        atomic_reply(reply,receipt)
        return receipt

    def serve(self,max_seconds=300,poll_seconds=1):
        if not 1<=max_seconds<=3600 or not .25<=poll_seconds<=5:raise DataError('WORKER_TIME_BUDGET')
        held=lock_worker(self.root)
        stop=self.root/'control'/'STOP'
        deadline=time.monotonic()+max_seconds
        interrupted=False
        def halt(*_):
            nonlocal interrupted
            interrupted=True
        old=signal.signal(signal.SIGINT,halt)
        try:
            while time.monotonic()<deadline and not stop.exists() and not interrupted:
                for path in sorted((self.root/'requests').glob('*.json'))[:100]:
                    if stop.exists() or interrupted or time.monotonic()>=deadline:break
                    try:self.handle(path)
                    except (DataError,ValueError,KeyError,TypeError,OSError) as error:
                        # A fixed error receipt cannot carry source payloads, secrets, or arbitrary exception text.
                        key=path.stem
                        if ID.fullmatch(key) and not (self.root/'replies'/(key+'.json')).exists():
                            atomic_reply(self.root/'replies'/(key+'.json'),{
                                'request_id':key,'status':'REJECTED','error_class':type(error).__name__,
                                'reason':str(error) if isinstance(error,DataError) else 'INVALID_REQUEST_OR_IO',
                                'request_sha256':hashlib.sha256(path.read_bytes()).hexdigest()
                                    if not path.is_symlink() and path.stat().st_size<=64*1024 else None,
                                'observed_at_ms':milliseconds()})
                time.sleep(min(poll_seconds,max(0,deadline-time.monotonic())))
        finally:
            signal.signal(signal.SIGINT,old);held.close()
        return {'status':'STOPPED','reason':'OWNER_STOP_OR_BOUNDED_DEADLINE'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    actions=parser.add_subparsers(dest='action',required=True)
    scan=actions.add_parser('capture');scan.add_argument('directory',type=Path)
    scan.add_argument('--universe',type=int,default=24);scan.add_argument('--shortlist',type=int,default=4)
    build=actions.add_parser('build');build.add_argument('raw',type=Path);build.add_argument('out',type=Path)
    chart=actions.add_parser('chart');chart.add_argument('packet',type=Path);chart.add_argument('request',type=Path);chart.add_argument('out',type=Path)
    check=actions.add_parser('gate');check.add_argument('packet',type=Path);check.add_argument('--proposal',type=Path)
    check.add_argument('--account',type=Path);check.add_argument('--receipts',type=Path)
    actions.add_parser('readiness')
    history=actions.add_parser('historical-gate');history.add_argument('proposal',type=Path);history.add_argument('evidence',type=Path)
    stage=actions.add_parser('stage');stage.add_argument('run',type=Path);stage.add_argument('shared',type=Path);stage.add_argument('run_id')
    serve=actions.add_parser('serve');serve.add_argument('root',type=Path);serve.add_argument('--max-seconds',type=int,default=300)
    args=parser.parse_args()
    if args.action=='capture':result=capture(args.directory,universe=args.universe,shortlist=args.shortlist)
    elif args.action=='build':result=build_all(args.raw,args.out)
    elif args.action=='chart':result=render(args.packet,previous.load(args.request),args.out)
    elif args.action=='gate':result=gate(args.packet,*(previous.load(p) if p else None for p in [args.proposal,args.account,args.receipts]))
    elif args.action=='serve':result=Inbox(args.root).serve(args.max_seconds)
    elif args.action=='stage':result=stage_run(args.run,args.shared,args.run_id)
    elif args.action=='historical-gate':result=historical_geometry(previous.load(args.proposal),previous.load(args.evidence))
    else:result=readiness()
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (DataError,OSError,ValueError,KeyError,TypeError) as error:
        print(json.dumps({'status':'BLOCKED','reason':str(error) if isinstance(error,DataError) else type(error).__name__}))
        raise SystemExit(1)
