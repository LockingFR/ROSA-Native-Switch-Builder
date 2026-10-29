"""Synthetic mutation tests: metadata can explain refusal, never authorize it."""
import struct
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
import compat_manifest
import core
import guided_workflow as workflow
import reference_diagnostics
import rom_diagnostics
from test_compat import fake_rom


class Diagnostics(unittest.TestCase):
    def test_independent_tester_identity_remains_blocked(self):
        # Report identities only, not game/exheader bytes or a compatibility claim.
        identity={
            'code_sha256':'7046fdd23c28858856cea14b359b69caca68742fb21acaa49f737ca610fa9bd5',
            'exheader_sha256':'34bb6a98bafe13e957ed15d195b263a9447ca351caf771489f3b4c33a846c32c',
            'ncch_sha256':'15ab5126a08a2a7d0e6df683d53bebbe83d230aea06963913ae93ce7bc74c9a7',
        }
        # setUp enrolls synthetic reference identities for the other tests.
        with patch.object(compat_manifest,'REFERENCE_CODE_SHA256',identity['code_sha256']), \
             patch.object(compat_manifest,'REFERENCE_EXHEADER_SHA256','63c5eeddc891be395bf24b1882448f2bc4b50ee7e4deb8e6be75b70cc2eb67a3'), \
             patch.object(compat_manifest,'REFERENCE_NCCH_SHA256','7d2eb6ec0a241e055b295101d310328db58289ee53d84a78737d0ee452ea8d41'):
            for opt_in in (False,True):
                with self.assertRaises(core.CompatibilityError) as raised:
                    core.classify_rom_identity(identity,'36ebd51f45463f1f29a50adb02d4b5686cd2aa868fa91254141b61a3e0166b89',opt_in)
                self.assertEqual(raised.exception.support_code,'EXHEADER_NOT_ENROLLED')

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'private-name.3ds'
        fake_rom(self.path)
        # Add a synthetic non-code ExeFS resource and RomFS.
        raw=bytearray(self.path.read_bytes())
        raw[0x1410:0x1418]=b'icon\0\0\0\0'
        struct.pack_into('<II',raw,0x1418,0x200,0x80)
        struct.pack_into('<II',raw,0x5b0,0x10,2)
        self.path.write_bytes(raw)
        self.ids=core.inspect_rom(self.path,diagnostics=True)
        self.stack=ExitStack()
        self.addCleanup(self.stack.close)
        for name,key in (('REFERENCE_NCCH_SHA256','ncch_sha256'),
                         ('REFERENCE_CODE_SHA256','code_sha256'),
                         ('REFERENCE_EXHEADER_SHA256','exheader_sha256')):
            self.stack.enter_context(patch.object(compat_manifest,name,self.ids[key]))
        self.stack.enter_context(patch.object(compat_manifest,'REFERENCE_DIAGNOSTICS',self.ids['diagnostic_profile']))

    def mutate(self,offset):
        raw=bytearray(self.path.read_bytes());raw[offset]^=1;self.path.write_bytes(raw)

    def test_same_code_changed_critical_exheader_always_blocked(self):
        original=self.path.read_bytes()
        # Compression, mappings, stack, BSS, dependencies, services, capabilities,
        # system modes, scheduling and even unknown/reserved bytes.
        for offset in (0x0d,0x10,0x14,0x18,0x1c,0x20,0x30,0x3c,0x40,
                       0x1c0,0x200,0x208,0x20c,0x20d,0x20e,0x20f,
                       0x210,0x230,0x250,0x360,0x36f,0x370,0x3f0):
            with self.subTest(offset=hex(offset)):
                self.path.write_bytes(original);self.mutate(0x600+offset)
                for opt_in in (False,True):
                    report=workflow.rom_report(self.path,opt_in)
                    self.assertFalse(report['build_allowed'])
                    self.assertEqual(report['support_code'],'EXHEADER_NOT_ENROLLED')
                    self.assertTrue(report['reference_matches']['executable'])
                    comparison=report['diagnostic_comparison']
                    self.assertIn(False,comparison['exheader_blocks'].values())
                    self.assertTrue(comparison['resources']['romfs_sha256'])
                    with self.assertRaises(core.CompatibilityError) as raised:
                        core.validate_rom(self.path,opt_in)
                    self.assertEqual(raised.exception.support_code,'EXHEADER_NOT_ENROLLED')

    def test_code_mismatch_is_distinct(self):
        self.mutate(0x1600)
        report=workflow.rom_report(self.path,True)
        self.assertFalse(report['build_allowed'])
        self.assertEqual(report['support_code'],'CODE_NOT_ENROLLED')
        self.assertTrue(report['reference_matches']['exheader'])

    def test_resources_and_header_changes_are_not_conflated(self):
        original=self.path.read_bytes()
        for offset,changed in ((0x2400,'romfs_sha256'),(0x1800,'exefs_noncode_sha256'),
                               (0x550,'ncch_header_sha256')):
            with self.subTest(changed=changed):
                self.path.write_bytes(original);self.mutate(offset)
                report=workflow.rom_report(self.path)
                self.assertEqual(report['support_code'],'RESOURCES_NOT_VALIDATED')
                self.assertFalse(report['diagnostic_comparison']['resources'][changed])
                self.assertTrue(report['reference_matches']['executable'])
                self.assertTrue(report['reference_matches']['exheader'])
                self.assertTrue(workflow.rom_report(self.path,True)['build_allowed'])

    def test_unknown_reference_is_unknown_and_diagnostics_cannot_enroll(self):
        result=rom_diagnostics.compare(self.ids['diagnostic_profile'],None)
        self.assertTrue(all(v is None for section in result.values() for v in section.values()))
        self.mutate(0x610)
        profile=core.inspect_rom(self.path,diagnostics=True)['diagnostic_profile']
        with patch.object(compat_manifest,'REFERENCE_DIAGNOSTICS',profile):
            self.assertEqual(workflow.rom_report(self.path,True)['support_code'],'EXHEADER_NOT_ENROLLED')

    def test_export_drops_nested_unknown_data(self):
        report=workflow.rom_report(self.path)
        report['diagnostic_profile']['exheader']['fields']['text_address']='private-path'
        report['diagnostic_profile']['exheader']['blocks']['service_access']='raw-service-bytes'
        report['diagnostic_profile']['resources']['injected']='private-path'
        report['diagnostic_comparison']={'injected':'private-path'}
        out=Path(self.temp.name)/'report.json'
        body=workflow.export_report(out,report)
        text=out.read_text()
        for secret in ('private-path','raw-service-bytes','private-name','injected'):
            self.assertNotIn(secret,text)
        self.assertEqual(body['schema'],2)

    def test_bounds_rejected_before_hashing_resources(self):
        original=self.path.read_bytes()
        for offset,value in ((0x5b0,0xfffffff),(0x5b0,8),(0x1418,0xffffffff),
                             (0x5a0,2)):
            with self.subTest(offset=offset,value=value):
                raw=bytearray(original);struct.pack_into('<I',raw,offset,value);self.path.write_bytes(raw)
                with self.assertRaises(core.BuildError):core.inspect_rom(self.path,diagnostics=True)

    def test_short_exheader_has_unknown_not_fabricated_fields(self):
        profile=rom_diagnostics.exheader_profile(bytes(0x200))
        self.assertNotIn('program_id',profile['fields'])
        self.assertNotIn('service_access',profile['blocks'])

    def test_reference_derivation_rejects_unenrolled_dump(self):
        with self.assertRaisesRegex(core.BuildError,'Reference digest mismatch'):
            reference_diagnostics.derive(self.path)
        with patch.object(core,'ROM_SHA',core.sha(self.path)):
            self.assertEqual(reference_diagnostics.derive(self.path),self.ids['diagnostic_profile'])


if __name__=='__main__':unittest.main()
