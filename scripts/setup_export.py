"""One-way schema-compatible OpenBot evidence export. No execution interface."""
from setup_common import *
def export():
    import jsonschema
    decisions=read(OUT/'decisions.json');items=[]
    # Deterministic recent records, never choose examples by future profit.
    for x in sorted(decisions,key=lambda x:(x['at'],x['pair'],x['setup_id']))[-100:]:
        items.append(dict(decision_id=x['plan']['decision_id'] if x['plan'] else x['setup_id'][:240],
            venue='gate',symbol=x['pair'],status='RESEARCH_CANDIDATE' if x['state']=='ADMITTED' else ('WATCH' if x['state']=='ARMED' else 'REJECT'),
            reason=x['reason'],environment='BACKTEST_DEVELOPMENT',event_context={'clearance':'UNKNOWN'},orders_created=False,
            geometry=x['plan'],data_gaps=['HISTORICAL_EXECUTED_FLOW_UNKNOWN','COMPLETE_HISTORICAL_PROFILE_UNKNOWN','HISTORICAL_SPREAD_UNKNOWN'],
            opposing_evidence=[x['regime']],evidence_id=x['setup_id']))
    report=dict(schema_version=1,snapshot_id='setup-run-001',generated_at=now(),mode='READ_ONLY_RESEARCH',venue='gate',
        source_provenance=dict(manifest_sha256=sha(OUT/'data-development.json'),protocol_sha256=sha(ROOT/'research/setup/protocol.json')),
        candidates=items,event_briefing=dict(schema_version=1,clearance='UNKNOWN',coverage='NOT_COLLECTED',events=[]),
        orders_created=False,uncertainty=['UNQUALIFIED_DEVELOPMENT_RESEARCH','NO_EXECUTION_AUTHORITY','PROFILE_COMPARISON_NOT_TESTED'])
    jsonschema.validate(report,read(ROOT/'research/foundation/openbot.schema.json'))
    write(OUT/'openbot/research-snapshot.json',report)
    write(OUT/'openbot/manifest.json',dict(schema='research/foundation/openbot.schema.json',sha256=sha(OUT/'openbot/research-snapshot.json'),permission='READ_ONLY_MANUAL_COPY',
        isolation='NO_AGENT_RUNTIME_OR_ADMIN_BRIDGE_STARTED; owner-host isolation remains untested'))
if __name__=='__main__':export()
