"""Trusted local OpenBot identity. Paths stay private; session references are hashes.

No provider/account login files, prompts, or model-generated identity are read.
The path-only config is owner-managed and must be under ignored work/.
"""
import errno
import json
import os
from pathlib import Path, PureWindowsPath
from contextlib import contextmanager
import sqlite3
import stat
from .contracts import ContractError, digest
from .settings import ROOT

ERRORS = frozenset({'NATIVE_AUDIT_CONFIG_MISSING','NATIVE_AUDIT_CONFIG_INVALID',
    'NATIVE_PROVIDER_UNSUPPORTED','NATIVE_MODEL_SWITCHED','NATIVE_NOT_INVOKED',
    'NATIVE_IDENTITY_UNAVAILABLE','NATIVE_SESSION_MISMATCH','NATIVE_AGENT_MISMATCH',
    'NATIVE_READ_INCOMPLETE','NATIVE_REPLY_PROVENANCE','NATIVE_REVIEW_TIMED_OUT',
    'NATIVE_REVIEW_INCOMPLETE','NATIVE_UNAUTHORIZED_TOOL','NATIVE_HANDOFF_UNATTESTED',
    'NATIVE_PROVIDER_SCHEMA_UNSUPPORTED','NATIVE_REQUEST_STALE','NATIVE_STORAGE_UNAVAILABLE','NATIVE_STORAGE_TIMED_OUT',
    'NATIVE_STORAGE_LOCKED','NATIVE_READER_PROCESS_UNAVAILABLE','NATIVE_TASK_FAILED','NATIVE_TOOL_DISCOVERY_UNVERIFIED',
    'NATIVE_SUBMISSION_OUTSIDE_WINDOW','NATIVE_RESPONSE_OUTSIDE_WINDOW',
    'NATIVE_PROJECTION_AFTER_SNAPSHOT','NATIVE_CHILD_CLOCK_INVALID',
    'NATIVE_PARENT_OUTPUT_TRUNCATED','NATIVE_PARENT_ARGUMENT_MISMATCH',
    'NATIVE_PARENT_OUTPUT_TOO_LARGE','NATIVE_PARENT_DELIVERY_UNCONFIRMED'})
ADAPTERS = {'opencode': 'OPENCODE_V2_SESSION_MESSAGE', 'codex': 'CODEX_ROLLOUT_0169'}

# Diagnostics are labels, never provider values or exception text.
DIAGNOSTIC_LABELS={
    'stage':frozenset({'ENVELOPE','SESSION','EVIDENCE','IDENTITY'}),
    'check':frozenset({'JSON','TIMESTAMP','ORDER','VERSION','IDENTITY','BACKEND','CONTEXT','TURN','INPUT','FINAL','TOOLS','COMPLETENESS',
        'CONFIGURED_PROVIDER','CONFIGURED_MODEL','CONFIGURED_ADAPTER','APP_PARENT_MODEL','APP_PARENT_PROVIDER',
        'CODEX_PARENT_THREAD_MODEL','ROLLOUT_TURN_CONTEXT_MODEL','APP_CHILD_MODEL','APP_CHILD_PROVIDER',
        'CODEX_CHILD_THREAD_MODEL','ROLLOUT_SETTINGS_MODEL'}),
    'schema_variant':frozenset({'CODEX_0169','CODEX_0169_ORDINAL','UNRECOGNIZED'})}

STORAGE_LABELS={
    'stage':{'SQLITE_OPEN','SQLITE_QUERY_ONLY','SQLITE_QUERY','READER','WINDOWS_OBSERVE_HANDOFF','WINDOWS_COLLECT'},
    'category':{'SQLITE','OS','PROCESS'},
    'classification':{'BUSY','IO','CANNOT_OPEN','INVALID_DATABASE','FIXED_SCHEMA_MISMATCH','OTHER',
        'PERMISSION_DENIED','MISSING_FILE','CALLER_DEADLINE','PROCESS_TIMEOUT'},
    'retryability':{'TRANSIENT','UNKNOWN','TERMINAL'}}

def safe_diagnostic(value):
    if not isinstance(value,dict):return {}
    labels=STORAGE_LABELS if set(value)==set(STORAGE_LABELS) else DIAGNOSTIC_LABELS
    if set(value)!=set(labels) or any(not isinstance(v,str) or v not in labels[k] for k,v in value.items()):
        return {}
    return dict(value)


class NativeEvidenceError(ContractError):
    def __init__(self,code,stage=None,check=None,variant='UNRECOGNIZED',*,diagnostic=None):
        super().__init__(code if code in ERRORS else 'NATIVE_PROVIDER_SCHEMA_UNSUPPORTED')
        self.diagnostic=safe_diagnostic(diagnostic or {'stage':stage,'check':check,'schema_variant':variant})


def storage_fault(error, stage):
    sqlite=isinstance(error,sqlite3.Error)
    classification='OTHER';retryability='UNKNOWN';code='NATIVE_STORAGE_UNAVAILABLE'
    if sqlite:
        primary=getattr(error,'sqlite_errorcode',0) & 0xff
        if primary in {sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED} or str(error).lower() in {'database is locked','database is busy'}:
            classification='BUSY';retryability='TRANSIENT';code='NATIVE_STORAGE_LOCKED'
        elif primary==sqlite3.SQLITE_ERROR and str(error).lower().startswith(('no such table:', 'no such column:')):
            classification='FIXED_SCHEMA_MISMATCH';retryability='TERMINAL';code='NATIVE_PROVIDER_SCHEMA_UNSUPPORTED'
        elif primary in {sqlite3.SQLITE_CORRUPT,sqlite3.SQLITE_NOTADB}:
            classification='INVALID_DATABASE';retryability='TERMINAL';code='NATIVE_PROVIDER_SCHEMA_UNSUPPORTED'
        elif primary==sqlite3.SQLITE_CANTOPEN:classification='CANNOT_OPEN'
        elif primary==sqlite3.SQLITE_IOERR or str(error).lower()=='disk i/o error':classification='IO'
    elif isinstance(error,OSError):
        if error.errno in {errno.EACCES,errno.EPERM}:classification='PERMISSION_DENIED'
        elif error.errno==errno.ENOENT:classification='MISSING_FILE'
        elif error.errno==errno.EIO:classification='IO'
    return code,{'stage':stage,'category':'SQLITE' if sqlite else 'OS',
        'classification':classification,'retryability':retryability}


def ref(value):
    return digest(str(value).encode())


WINDOWS_EXTENDED = '\\\\?\\'


def _ordinary_path(value):
    value=str(value)
    extended_unc=WINDOWS_EXTENDED+'UNC\\'
    if value[:len(extended_unc)].casefold()==extended_unc.casefold():
        return '\\\\'+value[len(extended_unc):]
    return value.removeprefix(WINDOWS_EXTENDED)


def local_path(value):
    """Return a normal path for scope comparisons, without resolving links."""
    raw=str(value)
    value=_ordinary_path(raw)
    if (os.name=='nt' and value.startswith('/mnt/') and value[5:6].isascii()
            and value[5:6].isalpha() and value[6:7]=='/'):
        value=value[5].upper()+':/'+value[7:]
    if os.name=='nt' or raw.startswith(('\\\\', WINDOWS_EXTENDED)) or value[1:2]==':':
        windows=PureWindowsPath(value)
        drive=windows.drive
        drive_letter=len(drive)==2 and drive[0].isascii() and drive[0].isalpha() and drive[1]==':'
        share_parts=drive[2:].split('\\') if drive.startswith('\\\\') else []
        unc=len(share_parts)==2 and all(share_parts) and '..' not in share_parts
        if (not windows.is_absolute() or not (drive_letter or unc)
                or value.startswith(('\\\\.\\','\\\\?\\')) or '\x00' in value):
            raise ValueError('Invalid Windows path')
        if any(part!='..' and (part.endswith(('.', ' ')) or any(c in part for c in ':*?"<>|')
                or PureWindowsPath(part).is_reserved()) for part in (*share_parts,*windows.parts[1:])):
            raise ValueError('Invalid Windows path component')
        if os.name!='nt':
            if not drive_letter:raise ValueError('Windows share requires a Windows reader')
            return Path('/mnt',drive[0].lower(),*windows.parts[1:])
    return Path(value).absolute()


def _filesystem_path(path):
    if os.name!='nt':return path
    if path.drive.startswith('\\\\'):
        return Path(WINDOWS_EXTENDED+'UNC\\'+str(path)[2:])
    return Path(WINDOWS_EXTENDED+str(path))


def checked_path(value, *, root=None, error='NATIVE_AUDIT_CONFIG_INVALID'):
    """Validate ordinary path scope before opening any component."""
    try:
        path=local_path(value)
        boundary=local_path(root) if root is not None else None
    except (ValueError, TypeError):
        raise ContractError(error) from None
    if '..' in path.parts or (boundary is not None and not path.is_relative_to(boundary)):
        raise ContractError(error)
    # On Windows the link check itself needs long-path-safe lstat. Walk
    # top-down and reject each redirect before inspecting any descendant.
    for component in (*reversed(path.parents),path):
        try:
            info=_filesystem_path(component).lstat()
        except FileNotFoundError:
            break
        # Windows name-surrogate reparse points include symlinks and junctions.
        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_reparse_tag',0)&0x20000000:
            raise ContractError(error)
    return _filesystem_path(path)


def path_key(value):
    value=_ordinary_path(value)
    if value.startswith('/mnt/') and len(value)>7 and value[6]=='/':
        value=value[5].upper()+':/'+value[7:]
    return str(PureWindowsPath(value)).casefold()


def under_work(value):
    return checked_path(value,root=ROOT/'work',error='NATIVE_REVIEW_MUST_BE_UNDER_WORK')


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
            p=checked_path(v)
            if k!='agent_workspace' and not p.is_file():raise ValueError()
            if k=='agent_workspace' and not p.is_dir():raise ValueError()
        return {**config,'_config_file':str(config_file)}
    except (OSError,ValueError,TypeError):
        raise ContractError('NATIVE_AUDIT_CONFIG_INVALID') from None


@contextmanager
def read_db(path):
    db=None;stage='SQLITE_OPEN'
    try:
        db=sqlite3.connect(local_path(path).as_uri()+'?mode=ro',uri=True,timeout=.2)
        stage='SQLITE_QUERY_ONLY'
        db.execute('PRAGMA query_only=ON')
        stage='SQLITE_QUERY'
        yield db
    except sqlite3.Error as error:
        code,diagnostic=storage_fault(error,stage)
        raise NativeEvidenceError(code,diagnostic=diagnostic) from None
    finally:
        if db is not None:db.close()


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
        rows=db.execute('''SELECT t.thread_id,t.active_turn_id,p.id,p.external_session_id,p.model,p.provider,r.started_at
            FROM projection_threads t JOIN projection_agents a ON a.thread_id=t.thread_id
            JOIN projection_provider_sessions p ON p.thread_id=t.thread_id
            JOIN projection_turns r ON r.turn_id=t.active_turn_id AND r.provider_session_id=p.id AND r.thread_id=t.thread_id
            WHERE a.agent_id=? AND t.agent_id=a.agent_id AND p.state='active' AND r.completed_at IS NULL''',(identity['agent_id'],)).fetchall()
    if len(rows)!=1:raise ContractError('NATIVE_NOT_INVOKED')
    thread,turn,sid,external,model,provider,started=rows[0]
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
        'session_ref':ref(sid),'external_session_ref':ref(external),'parent_started_at_utc':started}


def _assert_configured_owner(identity,current,*,require_configured_model):
    if any(current[field]!=identity.get(field) for field in ('agent_id','agent_name')):
        raise ContractError('NATIVE_AGENT_MISMATCH')
    fields=[('provider','CONFIGURED_PROVIDER'),('adapter','CONFIGURED_ADAPTER')]
    if require_configured_model:fields.append(('model','CONFIGURED_MODEL'))
    for field,check in fields:
        if current[field]!=identity.get(field):
            raise NativeEvidenceError('NATIVE_MODEL_SWITCHED','IDENTITY',check)
    model=identity.get('model')
    if not isinstance(model,str) or not model:raise ContractError('NATIVE_IDENTITY_UNAVAILABLE')


def parent_binding(identity,config,*,require_configured_model=True,as_of=None):
    """Resolve the captured parent from durable relations, never active pointers.

    Internal to the storage host: raw identifiers never cross native_host.
    The Codex historical model comes from the exact bound turn. The model
    columns on its app session and Codex thread follow later executions.
    Active callers also pin the configuration and both projections.
    """
    current=configured_identity(config)
    _assert_configured_owner(identity,current,require_configured_model=require_configured_model)
    with read_db(config['openbot_db']) as db:
        rows=db.execute('''SELECT h.thread_id,t.turn_id,p.id,p.external_session_id,
          p.model,p.provider,t.started_at,t.completed_at,t.status
          FROM projection_threads h JOIN projection_turns t ON t.thread_id=h.thread_id
          JOIN projection_provider_sessions p ON p.id=t.provider_session_id AND p.thread_id=h.thread_id
          WHERE h.agent_id=?''',(identity['agent_id'],)).fetchall()
    matches=[r for r in rows if all(ref(v)==identity.get(k) for v,k in zip(r[:4],
        ('thread_ref','turn_ref','session_ref','external_session_ref')))]
    if len(matches)!=1:raise ContractError('NATIVE_SESSION_MISMATCH')
    thread,turn,sid,external,model,provider,start,end,status=matches[0]
    if identity.get('parent_started_at_utc',start)!=start:raise ContractError('NATIVE_SESSION_MISMATCH')
    if provider!=identity['provider']:
        raise NativeEvidenceError('NATIVE_MODEL_SWITCHED','IDENTITY','APP_PARENT_PROVIDER')
    if (require_configured_model or provider!='codex') and model!=identity['model']:
        raise NativeEvidenceError('NATIVE_MODEL_SWITCHED','IDENTITY','APP_PARENT_MODEL')
    from .contracts import utc
    started_at=utc(start)
    completed_at=utc(end) if end is not None else None
    if completed_at is not None and completed_at<started_at:raise ContractError('NATIVE_SESSION_MISMATCH')
    if provider=='codex':
        with read_db(config['provider_db']) as db:
            row=db.execute('SELECT model_provider,model,cwd FROM threads WHERE id=?',(external,)).fetchone()
        if not row or path_key(row[2])!=path_key(config['agent_workspace']):raise ContractError('NATIVE_SESSION_MISMATCH')
        if require_configured_model and row[1]!=identity['model']:
            raise NativeEvidenceError('NATIVE_MODEL_SWITCHED','IDENTITY','CODEX_PARENT_THREAD_MODEL')
        if row[0]!=identity.get('provider_backend'):raise ContractError('NATIVE_SESSION_MISMATCH')
        if not require_configured_model:
            from .native_codex import attest_turn_model
            bound_end=completed_at if completed_at is not None else (utc(as_of) if as_of is not None else None)
            if bound_end is None or bound_end<started_at:raise ContractError('NATIVE_REVIEW_INCOMPLETE')
            attest_turn_model(config,external,turn,identity['model'],config['agent_workspace'],
                start=started_at,end=bound_end,backend=row[0])
    return {'thread':thread,'turn':turn,'session_id':sid,'external':external,
        'started_at':start,'completed_at':end,'status':status}


def assert_parent(identity,config,*,require_configured_model=False,as_of=None):
    """Check the original owner and parent, optionally for active work."""
    from .native_host import delegated,call
    if delegated(config):return call(config,'assert_parent',{'identity':identity,
        'require_configured_model':require_configured_model,'as_of':as_of})
    parent_binding(identity,config,require_configured_model=require_configured_model,as_of=as_of)
    return {key:identity[key] for key in ('agent_id','agent_name','provider','model','adapter')}


def assert_current(identity,config):
    from .native_host import delegated,call
    if delegated(config):return call(config,'assert_current',{'identity':identity})
    current=configured_identity(config)
    _assert_configured_owner(identity,current,require_configured_model=True)
    active=active_identity(config)
    _assert_configured_owner(identity,active,require_configured_model=True)
    if any(active.get(k)!=identity.get(k) for k in ('thread_ref','turn_ref','session_ref','external_session_ref','provider_backend')):
        raise ContractError('NATIVE_SESSION_MISMATCH')
    if identity.get('parent_started_at_utc',active['parent_started_at_utc'])!=active['parent_started_at_utc']:
        raise ContractError('NATIVE_SESSION_MISMATCH')
    return current
