"""Private archive restores reject traversal, links, corruption and overwrites."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from integrated_archive import restore,MANIFEST

class ArchiveRestore(unittest.TestCase):
    def archive(self,root,name='user_data/data/integrated/sample.json',link=False):
        path=Path(root)/'sample.tar.gz';payload=b'{"actual_fixture":true}'
        with tarfile.open(path,'w:gz') as out:
            member=tarfile.TarInfo(name);member.size=len(payload)
            if link: member.type=tarfile.SYMTYPE;member.linkname='/tmp/forbidden'
            out.addfile(member,io.BytesIO(payload) if not link else None)
            data=json.dumps({name:dict(bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())}).encode()
            member=tarfile.TarInfo(MANIFEST);member.size=len(data);out.addfile(member,io.BytesIO(data))
        return path,hashlib.sha256(path.read_bytes()).hexdigest()

    def test_verified_restore_is_idempotent_and_refuses_different_existing_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            p,digest=self.archive(directory);dest=Path(directory)/'restored'
            self.assertEqual(restore(p,dest,digest)['restored'],1)
            self.assertEqual(restore(p,dest,digest)['identical_existing'],1)
            target=dest/'user_data/data/integrated/sample.json';target.write_text('preserve me')
            with self.assertRaisesRegex(ValueError,'differing existing'):restore(p,dest,digest)
            self.assertEqual(target.read_text(),'preserve me')

    def test_traversal_link_and_wrong_archive_checksum_refused(self):
        for name,link in [('user_data/data/integrated/../../escape',False),('user_data/data/integrated/link',True)]:
            with tempfile.TemporaryDirectory() as directory:
                p,digest=self.archive(directory,name,link)
                with self.assertRaisesRegex(ValueError,'unsafe'):restore(p,Path(directory)/'out',digest)
                with self.assertRaisesRegex(ValueError,'archive checksum'):restore(p,Path(directory)/'out','0'*64)

if __name__=='__main__':unittest.main()
