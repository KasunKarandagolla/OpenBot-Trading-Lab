"""Explicit source/input seal, required by the native entry point."""
from setup_common import *
def seal():
    if RUN_ID!='run-003':raise ValueError('new candidate namespace required')
    if (OUT/'freeze.json').exists():raise ValueError('completed seal is immutable')
    sources=list((ROOT/'research/setup').glob('*.py'))+[ROOT/'research/session3/causal_structure.py']
    for folder in ['policy','session4','session3','recovery','bonus','intelligence','foundation','master_audit']:
        sources+=list((ROOT/'research'/folder).glob('*.py'))
    sources+=list((ROOT/'user_data/strategies').glob('*.py'))
    sources += [ROOT/'scripts'/x for x in ['setup_candidate.py','setup_candidate_report.py','setup_fix_tests.py','session4_metadata.py']]
    sources += [ROOT/'scripts'/x for x in ['setup_common.py','setup_prepare.py','setup_native.py','setup_verify.py','setup_seal.py','setup_export.py']]
    sources += [protocol_path(),ROOT/'scripts/lab-setup.sh']
    sources += [OUT/'contracts.json',DATA/'contract-source.json']
    write(OUT/'freeze.json',dict(at=now(),starting_commit='f0ef4453144869ca013ad156fdd46c81b767af2c',
        decision_source_hashes={str(p.relative_to(ROOT)):sha(p) for p in sources},plans_manifest=sha(OUT/'plans.json'),
        features_manifest=sha(OUT/'features.json'),source_manifest=sha(OUT/'data-development.json'),
        before_new_native_outcomes=True,classification='OWNER_DIRECTED_BUNDLED_DEVELOPMENT_FIXES',
        profile_source_hashes=read(OUT/'profile-inputs.json').get('input_hashes',{}),
        profile_input_index_sha256=sha(DATA/'profile-index.json') if (DATA/'profile-index.json').exists() else None))
    print('Candidate source, feature, plan and market-input seal written',flush=True)
if __name__=='__main__':seal()
