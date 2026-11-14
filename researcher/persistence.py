"""Versioned, atomic research metadata on top of the existing causal ledger."""
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import uuid
import zlib
from .contracts import ContractError, digest, encode, utc
from .structures import ResearchLedger, Reference


def read_latest_report(path):
    """Operator inspection uses SQLite mode=ro, with no schema/write side effect."""
    from .settings import ROOT
    p=Path(path).absolute()
    if '..' in p.parts or not p.is_relative_to(ROOT/'work') or any(x.is_symlink() for x in (p,*p.parents)):
        raise ContractError('LEDGER_MUST_BE_UNDER_WORK')
    try:
        db=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)
        try:
            if db.execute('PRAGMA user_version').fetchone()[0]!=5:raise ContractError('RESEARCH_DB_VERSION_UNSUPPORTED')
            def read(key,depth=0):
                if depth>2:raise ContractError('RESEARCH_SNAPSHOT_CORRUPT')
                row=db.execute('SELECT body,output_hash FROM run_snapshot WHERE run_key=?',(key,)).fetchone()
                if row is None:raise ContractError('RESEARCH_SNAPSHOT_CORRUPT')
                raw=zlib.decompress(row[0])
                if digest(raw)!=row[1]:raise ContractError('RESEARCH_SNAPSHOT_CORRUPT')
                result=json.loads(raw)
                if result.get('snapshot_delta_version')==1:
                    base=read(result['base_snapshot'],depth+1);base.update(result['overrides'])
                    for key,value in result.get('nested_overrides',{}).items():base[key].update(value)
                    return base
                return result
            row=db.execute('SELECT run_key FROM run_snapshot ORDER BY completed DESC,rowid DESC LIMIT 1').fetchone()
            if not row:raise ContractError('NO_SAVED_RESEARCH_REPORT')
            return read(row[0])
        finally:db.close()
    except (sqlite3.DatabaseError,zlib.error,ValueError):raise ContractError('RESEARCH_SNAPSHOT_CORRUPT') from None


class RunLedger(ResearchLedger):
    def __init__(self,path=':memory:'):
        self.path=str(path)
        if self.path!=':memory:':
            from .settings import ROOT
            p=Path(path).absolute()
            if not p.is_relative_to(ROOT/'work') or '..' in p.parts or any(x.is_symlink() for x in [p,*p.parents]):
                raise ContractError('LEDGER_MUST_BE_UNDER_WORK')
        try:
            if self.path!=':memory:' and Path(path).exists():
                probe=sqlite3.connect(Path(path).absolute().as_uri()+'?mode=ro',uri=True)
                try:
                    version=probe.execute('PRAGMA user_version').fetchone()[0]
                    if version not in (0,5):raise ContractError('RESEARCH_DB_VERSION_UNSUPPORTED')
                    names={r[0] for r in probe.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    allowed={'reference','event','hypothesis','lifecycle','run_attempt','run_snapshot','verified_cutoff','watch_revision','evidence_cache'}
                    if names-allowed:raise ContractError('NOT_A_RESEARCH_DATABASE')
                    if probe.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ContractError('RESEARCH_DB_CORRUPT')
                finally:probe.close()
            super().__init__(path)
            if self.db.execute('PRAGMA quick_check').fetchone()[0]!='ok':
                raise ContractError('RESEARCH_DB_CORRUPT')
            version=self.db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0,5):raise ContractError('RESEARCH_DB_VERSION_UNSUPPORTED')
            self.db.executescript('''
                BEGIN IMMEDIATE;
                CREATE TABLE IF NOT EXISTS run_attempt(id TEXT PRIMARY KEY, started TEXT NOT NULL, status TEXT NOT NULL, run_key TEXT);
                CREATE TABLE IF NOT EXISTS run_snapshot(run_key TEXT PRIMARY KEY, completed TEXT NOT NULL, output_hash TEXT NOT NULL, body BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS verified_cutoff(scope TEXT PRIMARY KEY, cutoff TEXT NOT NULL, symbols TEXT NOT NULL, run_key TEXT NOT NULL REFERENCES run_snapshot(run_key));
                CREATE TABLE IF NOT EXISTS watch_revision(id TEXT NOT NULL, run_key TEXT NOT NULL REFERENCES run_snapshot(run_key), first_seen TEXT NOT NULL, body TEXT NOT NULL, PRIMARY KEY(id,run_key));
                CREATE INDEX IF NOT EXISTS watch_run ON watch_revision(run_key);
                CREATE TABLE IF NOT EXISTS evidence_cache(id INTEGER PRIMARY KEY CHECK(id=1), cache_key TEXT NOT NULL, body BLOB NOT NULL, body_hash TEXT NOT NULL);
                PRAGMA user_version=5;
                COMMIT;
            ''')
        except sqlite3.DatabaseError:
            if hasattr(self,'db'):self.db.close()
            raise ContractError('RESEARCH_DB_CORRUPT_OR_BUSY') from None

    @contextmanager
    def writer(self,at):
        # One process owns the write lock throughout a scan. A crash rolls
        # back its unfinished transaction; the durable RUNNING attempt remains
        # and is marked INTERRUPTED by the next lock owner.
        attempt=uuid.uuid4().hex
        try:
            self.db.execute('BEGIN IMMEDIATE')
            self.db.execute("UPDATE run_attempt SET status='INTERRUPTED' WHERE status='RUNNING'")
            self.db.execute('INSERT INTO run_attempt VALUES(?,?,?,NULL)',(attempt,at,'RUNNING'))
            self.db.commit()
            self.db.execute('BEGIN IMMEDIATE')
        except sqlite3.OperationalError:
            self.db.rollback()
            raise ContractError('RESEARCH_WRITER_BUSY') from None
        try:
            yield attempt
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise

    def cached(self,key,depth=0):
        if depth>2:raise ContractError('RESEARCH_SNAPSHOT_CORRUPT')
        row=self.db.execute('SELECT body,output_hash FROM run_snapshot WHERE run_key=?',(key,)).fetchone()
        if not row:return None
        try:
            raw=zlib.decompress(row[0])
            if digest(raw)!=row[1]:raise ValueError()
            value=json.loads(raw)
            if value.get('snapshot_delta_version')==1:
                base=self.cached(value['base_snapshot'],depth+1)
                if base is None:raise ValueError()
                base.update(value['overrides'])
                for key,changes in value.get('nested_overrides',{}).items():base[key].update(changes)
                return base
            return value
        except (zlib.error,ValueError,TypeError):raise ContractError('RESEARCH_SNAPSHOT_CORRUPT') from None

    def cutoffs(self):
        return {s:{'cutoff':t,'symbols':json.loads(n),'run_key':k} for s,t,n,k in
            self.db.execute('SELECT scope,cutoff,symbols,run_key FROM verified_cutoff')}

    def latest(self):
        row=self.db.execute('SELECT run_key FROM run_snapshot ORDER BY completed DESC, rowid DESC LIMIT 1').fetchone()
        value=self.cached(row[0]) if row else None
        if value:
            cache=self.db.execute('SELECT body,body_hash FROM evidence_cache WHERE id=1 AND cache_key=?',(value.get('cache_key'),)).fetchone()
            if cache:
                try:
                    raw=zlib.decompress(cache[0])
                    if digest(raw)!=cache[1]:raise ValueError()
                    rows=json.loads(raw)
                    for p in value['packs']:p['measurements']=rows[p['timeframe']]
                except (ValueError,KeyError,zlib.error):raise ContractError('RESEARCH_SNAPSHOT_CORRUPT') from None
            value['numeric_cache_available']=bool(cache) or all('measurements' in p for p in value.get('packs',()))
        return value

    def finish(self,attempt,key,report,*,bundles=(),verified=(),terminals=(),crash_hook=None):
        """All references, watches, receipts/output and cutoffs commit together."""
        old=self.cached(key)
        # Historical snapshots retain source receipts, coverage, nominations,
        # frozen references and output hashes. Only ONE current scalar export
        # is cached; this ledger does not become a broad historical feature store.
        compact={**report,'packs':[{k:v for k,v in p.items() if k!='measurements'} for p in report['packs']],
            'numerical_storage':'ONE_CURRENT_CACHE; HISTORICAL_SCALAR_ROWS_NOT_RETAINED',
            'atomic_output_payload_sha256':digest(encode(report).encode())}
        stored=compact
        base_key=report.get('reuse',{}).get('original_snapshot')
        base=self.cached(base_key) if base_key else None
        if base:
            stored={'snapshot_delta_version':1,'base_snapshot':base_key,
                'overrides':{k:v for k,v in compact.items() if k not in base or encode(v)!=encode(base[k])}}
            if isinstance(base.get('research_shortlist'),dict) and isinstance(compact.get('research_shortlist'),dict):
                stored['overrides'].pop('research_shortlist',None)
                stored['nested_overrides']={'research_shortlist':{k:v for k,v in compact['research_shortlist'].items()
                    if k not in base['research_shortlist'] or encode(v)!=encode(base['research_shortlist'][k])}}
        raw=encode(stored).encode()
        if old is None:
            if report.get('cache_key') and not report.get('reuse'):
                current=encode({p['timeframe']:p.get('measurements',{}) for p in report['packs']}).encode()
                self.db.execute('INSERT INTO evidence_cache VALUES(1,?,?,?) ON CONFLICT(id) DO UPDATE SET cache_key=excluded.cache_key,body=excluded.body,body_hash=excluded.body_hash',
                    (report['cache_key'],zlib.compress(current),digest(current)))
            for ref,events,hypotheses in bundles:
                self.record(ref,events,hypotheses=hypotheses,cutoff=report['completed_at_utc'],
                    snapshot_cutoff=report['frozen_cutoffs'][ref.timeframe],allow_historical_insert=True)
            for ref,state,at in terminals:self.transition(ref,state=state,at=at)
            if crash_hook:crash_hook()
            self.db.execute('INSERT INTO run_snapshot VALUES(?,?,?,?)',
                (key,report['completed_at_utc'],digest(raw),zlib.compress(raw)))
            for watch in report['watches']:
                prior=self.db.execute('SELECT first_seen FROM watch_revision WHERE id=? ORDER BY rowid LIMIT 1',(watch['id'],)).fetchone()
                first=prior[0] if prior else watch['first_seen']
                if watch['first_seen']!=first:raise ContractError('IMMUTABLE_LEDGER_CONFLICT')
                last=self.db.execute('SELECT body FROM watch_revision WHERE id=? ORDER BY rowid DESC LIMIT 1',(watch['id'],)).fetchone()
                if last and last[0]==encode(watch):continue
                self.db.execute('INSERT INTO watch_revision VALUES(?,?,?,?)',(watch['id'],key,first,encode(watch)))
            for scope,cutoff,names in verified:
                prior=self.cutoffs().get(scope)
                if prior and utc(cutoff)<utc(prior['cutoff']):raise ContractError('RESEARCH_CUTOFF_REGRESSION')
                self.db.execute('INSERT INTO verified_cutoff VALUES(?,?,?,?) ON CONFLICT(scope) DO UPDATE SET cutoff=excluded.cutoff,symbols=excluded.symbols,run_key=excluded.run_key',
                    (scope,cutoff,encode(sorted(names)),key))
        self.db.execute("UPDATE run_attempt SET status=?,run_key=? WHERE id=?",(report['operation_status'],key,attempt))

    def metrics(self):
        return {**self.counts(),'run_snapshots':self.db.execute('SELECT count(*) FROM run_snapshot').fetchone()[0],
            'watch_revisions':self.db.execute('SELECT count(*) FROM watch_revision').fetchone()[0],
            'interrupted_attempts':self.db.execute("SELECT count(*) FROM run_attempt WHERE status='INTERRUPTED'").fetchone()[0],
            'schema_version':5,'database_bytes':Path(self.path).stat().st_size if self.path!=':memory:' else None}
