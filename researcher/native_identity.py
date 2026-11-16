"""Trusted local OpenBot identity. Paths stay private; session references are hashes.

No provider/account login files, prompts, or model-generated identity are read.
The path-only config is owner-managed and must be under ignored work/.
"""
import json
from pathlib import Path, PureWindowsPath
from contextlib import contextmanager
import sqlite3
from .contracts import ContractError, digest
from .settings import ROOT

ERRORS = frozenset({'NATIVE_AUDIT_CONFIG_MISSING','NATIVE_AUDIT_CONFIG_INVALID',
    'NATIVE_PROVIDER_UNSUPPORTED','NATIVE_MODEL_SWITCHED','NATIVE_NOT_INVOKED',
    'NATIVE_IDENTITY_UNAVAILABLE','NATIVE_SESSION_MISMATCH','NATIVE_AGENT_MISMATCH',
    'NATIVE_READ_INCOMPLETE','NATIVE_REPLY_PROVENANCE','NATIVE_REVIEW_TIMED_OUT',
    'NATIVE_REVIEW_INCOMPLETE','NATIVE_UNAUTHORIZED_TOOL','NATIVE_HANDOFF_UNATTESTED',
    'NATIVE_PROVIDER_SCHEMA_UNSUPPORTED','NATIVE_REQUEST_STALE','NATIVE_STORAGE_UNAVAILABLE','NATIVE_STORAGE_TIMED_OUT','NATIVE_TASK_FAILED'})
ADAPTERS = {'opencode': 'OPENCODE_V2_SESSION_MESSAGE', 'codex': 'CODEX_ROLLOUT_0169'}

# Diagnostics are labels, never provider values or exception text.
DIAGNOSTIC_LABELS={
    'stage':frozenset({'ENVELOPE','SESSION','EVIDENCE'}),
    'check':frozenset({'JSON','TIMESTAMP','ORDER','VERSION','IDENTITY','BACKEND','CONTEXT','TURN','INPUT','FINAL','TOOLS','COMPLETENESS'}),
    'schema_variant':frozenset({'CODEX_0169','CODEX_0169_ORDINAL','UNRECOGNIZED'})}


def safe_diagnostic(value):
    if not isinstance(value,dict) or set(value)!=set(DIAGNOSTIC_LABELS):return {}
    if any(not isinstance(v,str) or v not in DIAGNOSTIC_LABELS[k] for k,v in value.items()):return {}
    return dict(value)


class NativeEvidenceError(ContractError):
    def __init__(self,code,stage,check,variant='UNRECOGNIZED'):
        super().__init__(code if code in ERRORS else 'NATIVE_PROVIDER_SCHEMA_UNSUPPORTED')
        self.diagnostic=safe_diagnostic({'stage':stage,'check':check,'schema_variant':variant})


def ref(value):
    return digest(str(value).encode())


def local_path(value):
    """Translate a Windows path only on WSL; never resolve through a symlink."""
    import os
    value=str(value).removeprefix('\\\\?\\')
    if os.name=='nt' and value.startswith('/mnt/') and len(value)>7 and value[6]=='/':
        value=value[5].upper()+':/'+value[7:]
    if os.name!='nt' and len(value)>2 and value[1]==':' and value[0].isalpha():
        value='/mnt/'+value[0].lower()+'/'+value[3:].replace('\\','/')
    return Path(value).absolute()


def path_key(value):
    value=str(value).removeprefix('\\\\?\\')
    if value.startswith('/mnt/') and len(value)>7 and value[6]=='/':
        value=value[5].upper()+':/'+value[7:]
    return str(PureWindowsPath(value)).casefold()


def under_work(value):
    p=local_path(value)
    if ('..' in p.parts or not p.is_relative_to(ROOT/'work') or
            any(x.is_symlink() for x in (p,*p.parents))):
        raise ContractError('NATIVE_REVIEW_MUST_BE_UNDER_WORK')
    return p


def load_private(value):
    p=under_work(value);config_file=p
    if not p.is_file():raise ContractError('NATIVE_AUDIT_CONFIG_MISSING')
    if p.stat().st_size>4096:raise ContractError('NATIVE_AUDIT_CONFIG_INVALID')
    try:
        config=json.loads(p.read_text(encoding='utf-8'))
        if (not isinstance(config,dict) or set(config)-{'openbot_db','provider_db','agent_workspace','native_python'}
                or not {'openbot_db','provider_db','agent_workspace'}<=set(config)
                or not all(isinstance(v,str) and v and len(v)<2048 for v in config.values())):
            raise ValueError()
        for k,v in config.items():
            p=local_path(v)
            if '..' in p.parts or any(x.is_symlink() for x in (p,*p.parents)):raise ValueError()
            if k!='agent_workspace' and not p.is_file():raise ValueError()
            if k=='agent_workspace' and not p.is_dir():raise ValueError()
        return {**config,'_config_file':str(config_file)}
    except (OSError,ValueError,TypeError):
        raise ContractError('NATIVE_AUDIT_CONFIG_INVALID') from None


@contextmanager
def read_db(path):
    db=sqlite3.connect(local_path(path).as_uri()+'?mode=ro',uri=True,timeout=.2)
    try:
        db.execute('PRAGMA query_only=ON')
        yield db
    finally:db.close()


def configured_identity(config):
    from .native_host import delegated,call
    if delegated(config):return call(config,'configured_identity')
    from .agent_review import AGENT
    with read_db(config['openbot_db']) as db:
        rows=db.execute("SELECT agent_id,model,agent_json FROM projection_agents WHERE json_extract(agent_json,'$.name')=?",(AGENT,)).fetchall()
    if len(rows)!=1:raise ContractError('NATIVE_AGENT_MISMATCH')
    aid,model,raw=rows[0];agent=json.loads(raw);provider=agent.get('provider')
    if provider not in ADAPTERS:raise ContractError('NATIVE_PROVIDER_UNSUPPORTED')
    if (not isinstance(model,str) or not model or agent.get('model')!=model or
            path_key(agent.get('workspacePath',''))!=path_key(config['agent_workspace'])):
        raise ContractError('NATIVE_IDENTITY_UNAVAILABLE')
    return {'agent_id':aid,'agent_name':AGENT,'provider':provider,'model':model,
        'adapter':ADAPTERS[provider]}


def active_identity(config):
    from .native_host import delegated,call
    if delegated(config):return call(config,'active_identity')
    identity=configured_identity(config)
    with read_db(config['openbot_db']) as db:
        rows=db.execute('''SELECT t.thread_id,t.active_turn_id,p.id,p.external_session_id,p.model,p.provider
            FROM projection_threads t JOIN projection_agents a ON a.thread_id=t.thread_id
            JOIN projection_provider_sessions p ON p.thread_id=t.thread_id
            JOIN projection_turns r ON r.turn_id=t.active_turn_id AND r.provider_session_id=p.id
            WHERE a.agent_id=? AND p.state='active' AND r.completed_at IS NULL''',(identity['agent_id'],)).fetchall()
    if len(rows)!=1:raise ContractError('NATIVE_NOT_INVOKED')
    thread,turn,sid,external,model,provider=rows[0]
    if model!=identity['model'] or provider!=identity['provider']:raise ContractError('NATIVE_MODEL_SWITCHED')
    if provider=='codex':
        with read_db(config['provider_db']) as db:
            row=db.execute('SELECT model_provider,model,cwd FROM threads WHERE id=?',(external,)).fetchone()
        if not row or path_key(row[2])!=path_key(config['agent_workspace']):raise ContractError('NATIVE_SESSION_MISMATCH')
        if row[1]!=model:raise ContractError('NATIVE_MODEL_SWITCHED')
        backend=row[0]
        if not isinstance(backend,str) or not backend:raise ContractError('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED')
    else:
        if '/' not in model:raise ContractError('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED')
        backend=model.split('/',1)[0]
    return {**identity,'provider_backend':backend,'thread_ref':ref(thread),'turn_ref':ref(turn),
        'session_ref':ref(sid),'external_session_ref':ref(external)}


def assert_current(identity,config):
    from .native_host import delegated,call
    if delegated(config):return call(config,'assert_current',{'identity':identity})
    current=configured_identity(config)
    if current['agent_id']!=identity.get('agent_id'):raise ContractError('NATIVE_AGENT_MISMATCH')
    if any(current[k]!=identity.get(k) for k in ('provider','model','adapter')):
        raise ContractError('NATIVE_MODEL_SWITCHED')
    active=active_identity(config)
    if any(active.get(k)!=identity.get(k) for k in ('thread_ref','turn_ref','session_ref','external_session_ref','provider_backend')):
        raise ContractError('NATIVE_SESSION_MISMATCH')
    return current
