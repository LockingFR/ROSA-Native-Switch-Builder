import unittest,tempfile,struct
from pathlib import Path
from unittest.mock import patch
import core,compat_manifest

def fake_rom(path):
    buf=bytearray(0x5800)
    buf[0x100:0x104]=b'NCSD'
    struct.pack_into('<I',buf,0x120,2) # 0x400
    struct.pack_into('<I',buf,0x124,0x20) # NCCH total 0x4000
    base=0x400
    buf[base+0x100:base+0x104]=b'NCCH'
    struct.pack_into('<I',buf,base+0x104,0x20)
    struct.pack_into('<Q',buf,base+0x118,core.TITLE)
    struct.pack_into('<I',buf,base+0x180,0x400)
    buf[base+0x18F]=4
    struct.pack_into('<I',buf,base+0x1A0,8) # ExeFS @ + 0x1000
    struct.pack_into('<I',buf,base+0x1A4,4) # ExeFS size 0x800
    exefs=base+0x1000
    buf[exefs:exefs+8]=b'.code\x00\x00\x00'
    struct.pack_into('<II',buf,exefs+8,0,0x100)
    buf[exefs+0x200:exefs+0x300]=bytes(range(256))
    buf[base+0x200:base+0x600]=b'x'*0x400
    path.write_bytes(buf)

class Compatibility(unittest.TestCase):
    def test_b20_exact_still_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'game.3ds';fake_rom(f)
            with patch.object(core,'ROM_SHA',core.sha(f)):
                self.assertEqual(core.validate_rom(f)['revision'],'exact-B20-reference')

    def test_non_game_trailing_bytes_allowed_if_ncch_same(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'game.3ds';fake_rom(f)
            with patch.object(compat_manifest,'REFERENCE_NCCH_SHA256',core.inspect_rom(f)['ncch_sha256']),patch.object(compat_manifest,'REFERENCE_CODE_SHA256',core.inspect_rom(f)['code_sha256']),patch.object(compat_manifest,'REFERENCE_EXHEADER_SHA256',core.inspect_rom(f)['exheader_sha256']):
                f.write_bytes(f.read_bytes()+b'NON_GAME_TRAILER')
                self.assertEqual(core.validate_rom(f)['revision'],'identical-game-partition')

    def test_only_code_equivalent_requires_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'game.3ds';fake_rom(f)
            ids=core.inspect_rom(f)
            with patch.object(compat_manifest,'REFERENCE_NCCH_SHA256',ids['ncch_sha256']),patch.object(compat_manifest,'REFERENCE_CODE_SHA256',ids['code_sha256']),patch.object(compat_manifest,'REFERENCE_EXHEADER_SHA256',ids['exheader_sha256']):
                b=bytearray(f.read_bytes());b[0x400+0x3000]=99;f.write_bytes(b)
                with self.assertRaisesRegex(core.BuildError,'experimental code-equivalent'):
                    core.validate_rom(f)
                self.assertTrue(core.validate_rom(f,allow_code_equivalent=True)['revision'].startswith('EXPERIMENTAL-'))
                b[0x400+0x1000+0x200+0x10]=99;f.write_bytes(b)
                with self.assertRaisesRegex(core.BuildError,'Unsupported executable'):
                    core.validate_rom(f,allow_code_equivalent=True)

    def test_reject_invalid_content(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'game.3ds';fake_rom(f)
            b=bytearray(f.read_bytes());b[0x400+0x100:0x400+0x104]=b'FAIL';f.write_bytes(b)
            with self.assertRaisesRegex(core.BuildError,'executable partition'):
                core.validate_rom(f)
