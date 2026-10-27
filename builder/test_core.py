from pathlib import Path
import hashlib,json,struct,tempfile,unittest,zipfile
from unittest.mock import patch
import os
import core

def payload(path,entries):
    records={name:{'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data in entries.items()}
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('manifest.json',json.dumps({'schema':1,'builder_version':core.VERSION,'files':records}))
        for name,data in entries.items():z.writestr(name,data)
    return core.sha(path)

class Safety(unittest.TestCase):
    def test_payload_checks_every_file(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'data';digest=payload(p,{'runtime/test.txt':b'allowed'})
            core.unpack_payload(p,root/'out',digest)
            self.assertEqual((root/'out/runtime/test.txt').read_bytes(),b'allowed')
            with self.assertRaises(core.BuildError):core.unpack_payload(p,root/'other','0'*64)
            with self.assertRaises(core.BuildError):core.unpack_payload(p,root/'out',digest)

    def test_windows_path_attacks_and_duplicates_are_rejected(self):
        for name in ('../outside.txt','C:/outside','a\\outside','/absolute','CON.txt','folder/file.','foo:bar'):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as d:
                root=Path(d);p=root/'data';digest=payload(p,{name:b'bad'})
                with self.assertRaises(core.BuildError):core.unpack_payload(p,root/'out',digest)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'data';digest=payload(p,{'A.txt':b'a','a.txt':b'b'})
            with self.assertRaises(core.BuildError):core.unpack_payload(p,root/'out',digest)

    def test_internal_manifest_cannot_hide_corruption(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'data'
            with zipfile.ZipFile(p,'w') as z:
                z.writestr('manifest.json',json.dumps({'schema':1,'builder_version':core.VERSION,'files':{'x':{'bytes':1,'sha256':'0'*64}}}))
                z.writestr('x','x')
            with self.assertRaises(core.BuildError):core.unpack_payload(p,root/'out',core.sha(p))

    def test_input_guard_uses_contents_and_exact_revision(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'mine.3ds';b=bytearray(0x5800)
            b[0x100:0x104]=b'NCSD';struct.pack_into('<I',b,0x120,2)
            struct.pack_into('<I',b,0x124,0x20)
            b[0x500:0x504]=b'NCCH';struct.pack_into('<Q',b,0x518,core.TITLE)
            struct.pack_into('<I',b,0x504,0x20)
            b[0x58F]=4;struct.pack_into('<I',b,0x5A0,8);struct.pack_into('<I',b,0x5A4,4)
            struct.pack_into('<I',b,0x580,0x400)
            b[0x1400:0x1408]=b'.code\0\0\0'
            struct.pack_into('<II',b,0x1408,0,0x100)
            p.write_bytes(b)
            with self.assertRaises(core.BuildError):core.validate_rom(p)
            with patch.object(core,'ROM_SHA',core.sha(p)):
                self.assertEqual(core.validate_rom(p)['title_id'],'000400000011C400')
            b[0x58F]=0;b[0x58B]=1;p.write_bytes(b)
            with patch.object(core,'ROM_SHA',core.sha(p)):
                with self.assertRaisesRegex(core.BuildError,'encrypted'):core.validate_rom(p)
            p.rename(p.with_suffix('.cia'))
            with self.assertRaisesRegex(core.BuildError,'CIA'):core.validate_rom(p.with_suffix('.cia'))

    def test_existing_output_is_preserved_before_any_tools_run(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);keep=root/'keep';keep.mkdir();(keep/'save').write_bytes(b'unchanged')
            with self.assertRaises(core.BuildError):core.build(root/'missing.3ds',keep,'none','none','none','none')
            self.assertEqual((keep/'save').read_bytes(),b'unchanged')

    def test_network_inputs_are_rejected(self):
        with self.assertRaises(core.BuildError):core.local_path(r'\\server\share\game.3ds')

    def test_logs_redact_input_workspace_and_profile(self):
        message=core.redact(r'C:\Users\Alice\secret.3ds C:\Users\Bob\folder',[(r'C:\Users\Alice\secret.3ds','<personal-dump>')])
        self.assertNotIn('Alice',message);self.assertNotIn('Bob',message)

    def test_codegen_cannot_read_host_hints_from_appdata(self):
        with patch.dict(os.environ,{'APPDATA':'private-existing-profile'}):
            env=core.isolated_env(Path('fresh-work'),'sdk')
            self.assertEqual(env['APPDATA'],str(Path('fresh-work/private-cache')))
            self.assertEqual(env['APPDATA'],env['LOCALAPPDATA'])
            self.assertEqual(os.environ['APPDATA'],'private-existing-profile')

if __name__=='__main__':unittest.main()
