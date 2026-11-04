"""Reuse safe private backup/restore, restricting members to this research namespace."""
import sys,json
from setup_common import *
import recovery_archive as adapter
adapter.WORK=WORK;adapter.DATA=DATA;adapter.OUT=OUT
adapter.PREFIXES=('user_data/data/setup/','work/setup/')
adapter.MANIFEST='SETUP-BACKUP-MANIFEST.json'
if __name__=='__main__':
    action=sys.argv[1]
    result=adapter.create(sys.argv[2]) if action=='create' else adapter.hydrate(sys.argv[2],sys.argv[3]) if action=='hydrate' else adapter.restore(sys.argv[2],sys.argv[3])
    print(json.dumps(result,indent=2))
