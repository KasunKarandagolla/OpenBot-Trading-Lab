"""Fixed Windows data reader for WSL WAL interoperability. No model/network.

Only named read operations exist. There is no SQL, code, command, URL or model
operation supplied by the caller. Requests and private paths stay below work/.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
from .contracts import ContractError,encode
from .settings import ROOT

OPERATIONS=frozenset({'configured_identity','active_identity','assert_current','owner_proof','collect','attest_start','review_count','delivery_proof'})


def delegated(config):return os.name!='nt' and bool(config.get('native_python'))


def call(config,operation,values=None):
    from .native_identity import local_path,under_work
    from .native_app import _windows
    if operation not in OPERATIONS:raise ContractError('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED')
    executable=local_path(config.get('native_python',''))
    if executable.name.casefold()!='python.exe' or not executable.is_file() or not config.get('_config_file'):
        raise ContractError('NATIVE_AUDIT_CONFIG_INVALID')
    request={'config_file':str(config['_config_file']),'values':values or {}}
    temp=None
    try:
        (ROOT/'work').mkdir(exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=ROOT/'work',prefix='native-read-',suffix='.json',delete=False) as f:
            temp=Path(f.name);f.write(encode(request));f.flush();os.fsync(f.fileno())
        bootstrap="import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); sys.argv[0]='native_read'; runpy.run_module('researcher.native_host',run_name='__main__')"
        command=[str(executable),'-X','utf8','-c',bootstrap,_windows(ROOT),'--operation',operation,'--input',_windows(under_work(temp))]
        result=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            encoding='utf-8',timeout=30)
        if len(result.stdout.encode())>256*1024:raise ContractError('NATIVE_REVIEW_FILE_SIZE')
        try:response=json.loads(result.stdout)
        except ValueError:raise ContractError('NATIVE_STORAGE_UNAVAILABLE') from None
        if result.returncode or not isinstance(response,dict) or 'result' not in response:
            from .native_identity import ERRORS
            code=response.get('reason') if isinstance(response,dict) else None
            if code not in ERRORS and code not in {'RUNNER_OWNER_START_REQUIRED','RUNNER_START_UNATTESTED'}:
                code='NATIVE_STORAGE_UNAVAILABLE'
            from .native_identity import NativeEvidenceError,safe_diagnostic
            diagnostic=safe_diagnostic(response.get('diagnostic')) if isinstance(response,dict) else {}
            if diagnostic:raise NativeEvidenceError(code,diagnostic['stage'],diagnostic['check'],diagnostic['schema_variant'])
            raise ContractError(code)
        return response['result']
    except subprocess.TimeoutExpired:raise ContractError('NATIVE_STORAGE_TIMED_OUT') from None
    finally:
        if temp is not None:temp.unlink(missing_ok=True)


def execute(operation,input_file):
    from .native_identity import load_private,under_work
    p=under_work(input_file)
    if p.stat().st_size>256*1024:raise ContractError('NATIVE_REVIEW_FILE_SIZE')
    payload=json.loads(p.read_text(encoding='utf-8'))
    if not isinstance(payload,dict) or set(payload)!={'config_file','values'} or not isinstance(payload['values'],dict):
        raise ContractError('NATIVE_AUDIT_CONFIG_INVALID')
    config=load_private(payload['config_file']);v=payload['values']
    from . import native_identity as identity
    if operation=='configured_identity':return identity.configured_identity(config)
    if operation=='active_identity':return identity.active_identity(config)
    if operation=='assert_current':return identity.assert_current(v['identity'],config)
    if operation=='collect':
        from .native_runtime import collect
        return collect(v['request'],config,as_of=v['as_of'])
    if operation in {'owner_proof','attest_start'}:
        from .openbot_runner import _owner_proof,attest_start
        return _owner_proof(v['identity'],config) if operation=='owner_proof' else attest_start(v['state'],config)
    if operation=='delivery_proof':
        from .native_runtime import delivery_proof
        return delivery_proof(v['state'],config)
    if operation=='review_count':
        with identity.read_db(config['openbot_db']) as db:
            return db.execute("SELECT count(*) FROM projection_agent_threads WHERE agent_id=? AND title=? AND origin='agent'",
                (v['agent_id'],v['title'])).fetchone()[0]
    raise ContractError('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operation',choices=sorted(OPERATIONS),required=True);parser.add_argument('--input',required=True)
    args=parser.parse_args()
    try:
        if os.name!='nt':raise ContractError('NATIVE_WINDOWS_READER_REQUIRED')
        print(encode({'result':execute(args.operation,args.input)}));return 0
    except (ValueError,TypeError,KeyError,OSError,__import__('sqlite3').Error) as error:
        code=str(error) if isinstance(error,ContractError) else 'NATIVE_STORAGE_UNAVAILABLE'
        from .native_identity import safe_diagnostic
        diagnostic=safe_diagnostic(getattr(error,'diagnostic',None))
        print(encode({'reason':code,**({'diagnostic':diagnostic} if diagnostic else {})}));return 2


if __name__=='__main__':raise SystemExit(main())
