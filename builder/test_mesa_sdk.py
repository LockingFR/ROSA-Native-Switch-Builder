"""Fixtures test failure paths only; real SDK/link evidence is recorded separately."""
from pathlib import Path
import hashlib,json,tempfile,unittest,zipfile
from unittest.mock import patch
import core,mesa_sdk

def ar(machine=183):
    b=bytearray(24);b[:6]=b'\x7fELF\x02\x01';b[18:20]=machine.to_bytes(2,'little')
    return b'!<arch>\n'+b'a.o/            '+b'0           '+b'0     '+b'0     '+b'100644  '+str(len(b)).encode().ljust(10)+b'`\n'+b

class MesaTests(unittest.TestCase):
    def test_existing_sdk_does_not_require_package_source_and_notices(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);p,s=self.fixture(r);cache=mesa_sdk.setup(p,cache=r/'cache')
            s['files']['PROVENANCE.json']={'bytes':1,'sha256':'0'*64}
            (p/'mesa-sdk.json').write_text(json.dumps(s))
            self.assertEqual(mesa_sdk.setup(p,'existing',existing=cache),cache)
            with self.assertRaisesRegex(core.BuildError,'PROVENANCE.json'):mesa_sdk.validate(cache,s)

    def fixture(self,root):
        payload=root/'payload';payload.mkdir();(payload/'sdk').mkdir()
        entries={n:bytes(ar()) for n in ('lib/libEGL.a','lib/libglapi.a','lib/libz.a')}
        entries['include/EGL/egl.h']=b'header'
        records={n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in entries.items()}
        archive=payload/'sdk/mesa-switch.zip'
        with zipfile.ZipFile(archive,'w') as z:
            for n,b in entries.items():z.writestr(n,b)
            z.writestr('manifest.json',json.dumps({'schema':1,'builder_version':core.VERSION,'files':records}))
        spec={'files':records,'sha256':core.sha(archive)}
        (payload/'mesa-sdk.json').write_text(json.dumps(spec))
        return payload,spec

    def test_auto_spaces_reuse_and_original_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);p,s=self.fixture(r);before=core.sha(p/'sdk/mesa-switch.zip');cache=r/'SDK with spaces'
            self.assertEqual(mesa_sdk.setup(p,cache=cache),cache)
            with patch.object(core,'unpack_payload',side_effect=AssertionError('unnecessary extraction')):
                self.assertEqual(mesa_sdk.setup(p,cache=cache),cache)
            self.assertEqual(core.sha(p/'sdk/mesa-switch.zip'),before)

    def test_missing_wrong_root_and_dependency(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);p,s=self.fixture(r)
            with self.assertRaisesRegex(core.BuildError,'lib/libEGL.a'):mesa_sdk.setup(p,'existing',existing=r/'absent')
            cache=mesa_sdk.setup(p,cache=r/'cache')
            with self.assertRaises(core.BuildError):mesa_sdk.validate(cache.parent,s)
            (cache/'include/EGL/egl.h').unlink()
            with self.assertRaisesRegex(core.BuildError,'include/EGL/egl.h'):mesa_sdk.validate(cache,s)

    def test_missing_egl_and_wrong_hash(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);p,s=self.fixture(r);cache=mesa_sdk.setup(p,cache=r/'cache')
            f=cache/'lib/libEGL.a';f.write_bytes(b'wrong')
            with self.assertRaises(mesa_sdk.SDKValidationError) as raised:mesa_sdk.validate(cache,s)
            first=raised.exception.diagnostic['files'][0]
            self.assertEqual(first['name'],'lib/libEGL.a');self.assertIn('actual_sha256',first)
            self.assertNotEqual(first['actual_sha256'],first['expected_sha256'])
            f.unlink()
            with self.assertRaisesRegex(core.BuildError,'lib/libEGL.a: missing'):mesa_sdk.validate(cache,s)

    def test_auto_recovers_bad_managed_cache_without_overwriting_it(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);payload,spec=self.fixture(root);cache=root/'cache'
            mesa_sdk.setup(payload,cache=cache)
            bad=cache/'lib/libEGL.a';bad.write_bytes(b'preserve damaged cache')
            with patch.object(mesa_sdk,'cache_root',return_value=cache):
                recovered=mesa_sdk.setup(payload)
                self.assertNotEqual(recovered,cache)
                self.assertEqual(mesa_sdk.setup(payload),recovered)
                self.assertEqual(bad.read_bytes(),b'preserve damaged cache')
                self.assertTrue(mesa_sdk.diagnose(recovered,spec)['compatible'])

    def test_parent_selection_resolves_only_an_exact_matching_sdk(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);payload,spec=self.fixture(root)
            actual=root/'container/opt/devkitpro/portlibs/switch'
            mesa_sdk.setup(payload,cache=actual)
            self.assertEqual(mesa_sdk.resolve_existing(root/'container',spec),actual)
            (actual/'lib/libEGL.a').write_bytes(b'unknown archive')
            with self.assertRaises(mesa_sdk.SDKValidationError) as caught:mesa_sdk.resolve_existing(root/'container',spec)
            self.assertFalse(caught.exception.diagnostic['compatible'])
            self.assertNotIn(str(root),str(caught.exception))

    def test_corrupt_archive_and_import_hash_even_with_cache(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);p,s=self.fixture(r);cache=mesa_sdk.setup(p,cache=r/'cache');bad=r/'corrupt.zip';bad.write_bytes(b'broken')
            with self.assertRaisesRegex(core.BuildError,'SHA-256'):mesa_sdk.setup(p,'import',archive=bad,cache=cache)
            with self.assertRaisesRegex(core.BuildError,'SHA-256'):mesa_sdk.setup(p,'import',archive=bad,cache=r/'new')
            self.assertFalse((r/'new').exists())

    def test_wrong_architecture(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'wrong.a';p.write_bytes(ar(62))
            with self.assertRaisesRegex(core.BuildError,'non-AArch64'):mesa_sdk.aarch64_archive(p)

    def test_import_and_no_network_for_auto(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);p,s=self.fixture(r)
            with patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('network forbidden')):
                mesa_sdk.setup(p,'import',archive=p/'sdk/mesa-switch.zip',cache=r/'cache')
                mesa_sdk.setup(p,cache=r/'second')

if __name__=='__main__':unittest.main()
