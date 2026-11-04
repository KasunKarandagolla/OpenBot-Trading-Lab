"""One-way schema-compatible OpenBot evidence export. No execution interface."""
from setup_common import *

def export_event(x):
    """An event owns its payload; shared setup identity never selects geometry."""
    import hashlib,json
    at=x['at'];state=x['state'];g=x.get('plan')
    if g is None and state=='REJECTED':g=x.get('candidate_geometry')
    if state in ('ARMED','WATCH','DISCOVERED'):g=None
    if g and __import__('pandas').Timestamp(g.get('confirmation_at',g['available_at']))>__import__('pandas').Timestamp(at):
        raise ValueError('future geometry in event payload')
    identity=json.dumps([x['pair'],at,x['setup_id'],state,x['reason']],separators=(',',':'))
    event_id='event:'+hashlib.sha256(identity.encode()).hexdigest()[:32]
    return dict(decision_id=g.get('decision_id',event_id) if g else event_id,event_id=event_id,decision_at=at,
        setup_id=x['setup_id'],state=state,venue='gate',symbol=x['pair'],
        status='RESEARCH_CANDIDATE' if state in ('ADMITTED','CONFIRMED','READY') else ('WATCH' if state in ('ARMED','WATCH') else 'REJECT'),
        reason=x['reason'],environment='BACKTEST_DEVELOPMENT',event_context={'clearance':'UNKNOWN'},orders_created=False,
        geometry=g,data_gaps=['HISTORICAL_EXECUTED_FLOW_UNKNOWN','COMPLETE_HISTORICAL_PROFILE_UNKNOWN','HISTORICAL_SPREAD_UNKNOWN'],
        opposing_evidence=[x.get('regime','UNKNOWN')],evidence_id=x['setup_id'])

def export():
    import jsonschema
    decisions=read(OUT/'decisions.json');items=[]
    # Deterministic recent records, never choose examples by future profit.
    for x in sorted(decisions,key=lambda x:(x['at'],x['pair'],x['setup_id']))[-100:]:
        items.append(export_event(x))
    report=dict(schema_version=1,snapshot_id='setup-'+RUN_ID,generated_at=now(),mode='READ_ONLY_RESEARCH',venue='gate',
        source_provenance=dict(manifest_sha256=sha(OUT/'data-development.json'),protocol_sha256=sha(protocol_path())),
        candidates=items,event_briefing=dict(schema_version=1,clearance='UNKNOWN',coverage='NOT_COLLECTED',events=[]),
        orders_created=False,uncertainty=['UNQUALIFIED_DEVELOPMENT_RESEARCH','NO_EXECUTION_AUTHORITY','PROFILE_COMPARISON_NOT_TESTED'])
    jsonschema.validate(report,read(ROOT/'research/foundation/openbot.schema.json'))
    write(OUT/'openbot/research-snapshot.json',report)
    write(OUT/'openbot/manifest.json',dict(schema='research/foundation/openbot.schema.json',sha256=sha(OUT/'openbot/research-snapshot.json'),permission='READ_ONLY_MANUAL_COPY',
        isolation='NO_AGENT_RUNTIME_OR_ADMIN_BRIDGE_STARTED; owner-host isolation remains untested'))
if __name__=='__main__':export()
