"""Synthetic inputs only; no real SDK, game, user path or network required."""
from pathlib import Path
import hashlib,json,tempfile,unittest,zipfile
from unittest.mock import patch
import core,compat_manifest
import guided_workflow as workflow
from test_compat import fake_rom

class GuidedWorkflow(unittest.TestCase):
    def test_cci_and_remaster_metadata_use_same_strict_executable_validation(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'own dump.cci';fake_rom(p)
            with patch.object(core,'ROM_SHA',core.sha(p)):
                report=workflow.rom_report(p)
                self.assertTrue(report['build_allowed']);self.assertEqual(report['format'],'NCSD')
                self.assertEqual(report['encryption'],'unencrypted');self.assertIn('remaster_version',report)
            b=bytearray(p.read_bytes());b[0x58f]=0;b[0x58b]=0;p.write_bytes(b)
            self.assertEqual(workflow.rom_report(p)['support_code'],'ENCRYPTED')

    def test_changed_executable_stays_blocked_and_reports_hashes_only(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'private person game.3ds';fake_rom(p);ids=core.inspect_rom(p)
            with patch.object(compat_manifest,'REFERENCE_NCCH_SHA256','1'*64),patch.object(compat_manifest,'REFERENCE_CODE_SHA256','2'*64),patch.object(compat_manifest,'REFERENCE_EXHEADER_SHA256','3'*64):
                report=workflow.rom_report(p,True)
            self.assertFalse(report['build_allowed']);self.assertEqual(report['code_sha256'],ids['code_sha256'])
            self.assertEqual(report['ncch_sha256'],ids['ncch_sha256']);self.assertEqual(report['sha256'],core.sha(p))
            self.assertFalse(report['reference_matches']['executable'])
            output=Path(td)/'shareable.json'
            workflow.export_report(output,report,[{'stage':'error','message':str(p),'rom':str(p),'done':0}],{'nro_sha256':'4'*64,'input':str(p),'log':str(p)})
            text=output.read_text();self.assertNotIn('private person',text);self.assertNotIn(str(p),text);self.assertNotIn('message',text)
            with self.assertRaises(FileExistsError):workflow.export_report(output)

    def test_detected_sdk_is_reused_only_after_authenticated_hash_checks(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);sdk=root/'SDK with spaces';sdk.mkdir();(sdk/'tool.exe').write_bytes(b'synthetic tool')
            data=root/'pair.data'
            with zipfile.ZipFile(data,'w') as z:z.writestr('manifest.json',json.dumps({'sdk_files':{'tool.exe':{'root':'devkitpro','sha256':core.sha(sdk/'tool.exe')}}}))
            digest=core.sha(data)
            self.assertEqual(workflow.choose_dependencies(data,digest,sdk),(sdk,False))
            (sdk/'tool.exe').write_bytes(b'changed')
            with patch.object(workflow,'devkit_candidates',return_value=[sdk]):self.assertEqual(workflow.choose_dependencies(data,digest),(None,True))
            with self.assertRaises(core.BuildError):workflow.choose_dependencies(data,digest,sdk)
            with self.assertRaises(core.BuildError):workflow.choose_dependencies(data,'0'*64,sdk)

    def test_reports_exclude_arbitrary_raw_data_and_missing_inputs(self):
        with tempfile.TemporaryDirectory() as td:
            report=workflow.rom_report(Path(td)/'missing.3ds')
            self.assertFalse(report['build_allowed']);self.assertNotIn(td,json.dumps(report))
            out=Path(td)/'environment.json';workflow.export_report(out)
            result=json.loads(out.read_text());self.assertFalse(result['privacy']['game_bytes']);self.assertFalse(result['environment']['macos_or_wine_validated'])

if __name__=='__main__':unittest.main()
