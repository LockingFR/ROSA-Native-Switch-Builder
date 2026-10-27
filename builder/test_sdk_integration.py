"""Isolated wiring tests: no game data, compiler or network required."""
from pathlib import Path
from unittest import TestCase, mock
import json, tempfile
import core, sdk

class ReachedGenerator(Exception):pass

class WiringTests(TestCase):
    def setup_fixture(self,root):
        rom=root/'owner.3ds'
        out=root/'fresh-workspace'
        data=root/'original.data';data.write_bytes(b'not an actual payload')
        mesa=root/'mesa';mesa.mkdir()
        devkit=root/'devkit';devkit.mkdir()
        managed_devkit=root/'fresh-workspace'/'managed-sdk'/'devkitpro'
        return rom,out,data,mesa,devkit,managed_devkit

    def run_until_codegen(self,managed):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);rom,out,data,mesa,devkit,managed_devkit=self.setup_fixture(root)
            seen=[]
            def unpack(datafile,payload,expected):
                self.assertEqual(datafile,data)
                payload.mkdir()
                (payload/'manifest.json').write_text(json.dumps({'sdk_files':{}}))
                return {}
            def verify_mesa(payload,path):
                seen.append('verify_mesa');self.assertEqual(path,mesa)
            def prepare(payload,work,emit,mesa_root):
                self.assertTrue(payload.is_dir());self.assertEqual(mesa_root,mesa)
                seen.append('prepare')
                return managed_devkit,mesa
            def check_toolset(dkit,msdk):
                seen.append('check_tools')
                self.assertEqual(dkit,managed_devkit if managed else devkit)
                self.assertEqual(msdk,mesa)
                return {'cc':'gcc','ar':'ar','elf2nro':'elf2nro'}
            def verify_all(payload,dkit,msdk):
                seen.append('verify_all')
                self.assertEqual(dkit,managed_devkit if managed else devkit)
            def fake_run(*args,**kwargs):raise ReachedGenerator()
            disk=mock.Mock();disk.free=16*1024**3
            patches=[
                mock.patch.object(core,'validate_rom',return_value={'bytes':1}),
                mock.patch.object(core,'unpack_payload',side_effect=unpack),
                mock.patch.object(core,'check_tools',side_effect=check_toolset),
                mock.patch.object(core,'run',side_effect=fake_run),
                mock.patch.object(core.shutil,'disk_usage',return_value=disk),
                mock.patch.object(sdk,'verify_mesa_files',side_effect=verify_mesa),
                mock.patch.object(sdk,'prepare',side_effect=prepare),
                mock.patch.object(sdk,'verify_sdk_files',side_effect=verify_all)]
            with patches[0],patches[1],patches[2],patches[3],patches[4],patches[5],patches[6],patches[7]:
                with self.assertRaises(ReachedGenerator):
                    core.build(rom,out,devkit,mesa,data,'dummy',managed_sdk=managed)
            return seen

    def test_managed_sdk_path_is_staged_and_verified(self):
        steps=self.run_until_codegen(True)
        self.assertEqual(steps,['verify_mesa','prepare','check_tools','verify_all'])

    def test_manual_sdk_never_contacts_package_installer(self):
        steps=self.run_until_codegen(False)
        self.assertEqual(steps,['check_tools','verify_all'])

    def test_managed_sdk_refuses_bad_mesa_before_download(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            rom,out,data,mesa,devkit,managed_devkit=self.setup_fixture(root)
            def unpack(datafile,payload,expected):
                payload.mkdir();return {}
            disk=mock.Mock();disk.free=16*1024**3
            with mock.patch.object(core,'validate_rom',return_value={'bytes':1}), \
                 mock.patch.object(core,'unpack_payload',side_effect=unpack), \
                 mock.patch.object(core.shutil,'disk_usage',return_value=disk), \
                 mock.patch.object(sdk,'verify_mesa_files',side_effect=core.BuildError('Wrong Mesa')), \
                 mock.patch.object(sdk,'prepare') as download:
                with self.assertRaisesRegex(core.BuildError,'Wrong Mesa'):
                    core.build(rom,out,devkit,mesa,data,'dummy',managed_sdk=True)
                download.assert_not_called()
