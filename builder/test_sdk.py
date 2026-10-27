"""Offline safety/integrity tests for sdk.py; no game or official SDK needed."""
import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]

import core
import sdk
BuildError = core.BuildError

# Prefer the actual zstandard package on Windows; the Linux CI fallback
# relies on its local zstd binary when the Python binding is unavailable.
try:
    import zstandard as real_zstandard
except ImportError:
    real_zstandard = None
if real_zstandard is None:
    if not shutil.which("zstd"):
        raise unittest.SkipTest("zstandard Python package or zstd fixture CLI is needed")
    class ZstdDecompressor:
        def stream_reader(self, raw):
            proc = subprocess.run(["zstd", "-d", "-q", "-c"], input=raw.read(), capture_output=True)
            if proc.returncode:
                raise RuntimeError("Invalid compressed test fixture")
            return io.BytesIO(proc.stdout)
    sdk._decoder = lambda: ZstdDecompressor()

def make_zst(path, members):
    tar_bytes = io.BytesIO()
    with tarfile.open(fileobj=tar_bytes, mode="w") as archive:
        for name, kind, content in members:
            info = tarfile.TarInfo(name)
            if kind == "file":
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))
            elif kind == "dir":
                info.type = tarfile.DIRTYPE
                archive.addfile(info)
            elif kind == "link":
                info.type = tarfile.LNKTYPE
                info.linkname = content
                archive.addfile(info)
            elif kind == "symlink":
                info.type = tarfile.SYMTYPE
                info.linkname = content
                archive.addfile(info)
            else:
                raise ValueError(kind)
    if real_zstandard is not None:
        path.write_bytes(real_zstandard.ZstdCompressor().compress(tar_bytes.getvalue()))
    else:
        compressed = subprocess.run(["zstd", "-q", "-c"], input=tar_bytes.getvalue(), capture_output=True, check=True)
        path.write_bytes(compressed.stdout)
    return path


class StubHTTPResponse:
    def __init__(self, url, body, content_length=None):
        self.url = url
        self.body = io.BytesIO(body)
        self.headers = {"Content-Length": str(len(body) if content_length is None else content_length)}
    def geturl(self): return self.url
    def read(self, size): return self.body.read(size)
    def __enter__(self): return self
    def __exit__(self, *args): return False

class StubHTTPOpener:
    def __init__(self, response): self.response = response
    def open(self, request, timeout=None): return self.response


class ProvisioningTests(unittest.TestCase):
    def test_official_opt_ancestor_directory_only(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            pkg=make_zst(root/'official.zst',[
                ('opt/','dir',b''),('opt/devkitpro/','dir',b''),
                ('opt/devkitpro/devkitA64/bin/tool.exe','file',b'tool')])
            sdk.extract(pkg,root/'sdk',lambda **e:None)
            self.assertEqual((root/'sdk/devkitA64/bin/tool.exe').read_bytes(),b'tool')
            for name,kind,content in [('opt','file',b'x'),('opt/','symlink','elsewhere'),('opt/other/x','file',b'x')]:
                with self.subTest(name=name,kind=kind):
                    pkg=make_zst(root/'bad.zst',[(name,kind,content)])
                    with self.assertRaises(BuildError):sdk.extract(pkg,root/'rejected',lambda **e:None)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.url = "https://pkg.devkitpro.org/packages/test-1.pkg.tar.zst"

    def record(self, data):
        return {"name": "test-1.pkg.tar.zst", "url": self.url,
                "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

    def test_only_official_package_urls(self):
        good = [self.url, self.url.replace("https://", "https://", 1)]
        for url in good:
            self.assertEqual(sdk.package_url(url), url)
        bad = ["http://pkg.devkitpro.org/packages/test-1.pkg.tar.zst",
               "https://example.org/packages/test-1.pkg.tar.zst",
               "https://pkg.devkitpro.org.evil.test/packages/test.pkg.tar.zst",
               "https://username@pkg.devkitpro.org/packages/test.pkg.tar.zst",
               "https://pkg.devkitpro.org:444/packages/test.pkg.tar.zst",
               "https://pkg.devkitpro.org/packages/../test.pkg.tar.zst",
               "https://pkg.devkitpro.org/packages/%2e%2e/test.pkg.tar.zst",
               "https://pkg.devkitpro.org/packages//test.pkg.tar.zst",
               "https://pkg.devkitpro.org/packages/test.pkg.tar.zst?token=x"]
        for url in bad:
            with self.subTest(url=url), self.assertRaises(BuildError):
                sdk.package_url(url)

    def test_record_schema_rejects_mismatch_or_duplicate_plan(self):
        data = b"correct"
        record = self.record(data)
        sdk.validated_record(record)
        for replacement in [{"name": "different.pkg.tar.zst"}, {"bytes": True},
                            {"sha256": "x" * 64}, {"bytes": -1}]:
            with self.subTest(replacement=replacement), self.assertRaises(BuildError):
                sdk.validated_record(record | replacement)
        self.assertRaises(BuildError, sdk._load_plan, self.path)
        (self.path / "sdk-plan.json").write_text(json.dumps({"schema":1,"packages":[record, record]}))
        self.assertRaises(BuildError, sdk._load_plan, self.path)

    def test_secure_relative_paths(self):
        self.assertEqual(str(sdk.relative_member("opt/devkitpro/devkitA64/bin/aarch64-none-elf-gcc.exe")),
                         str(Path("devkitA64/bin/aarch64-none-elf-gcc.exe")))
        bad = ["../opt/devkitpro/evil", "opt/devkitpro/../other", "opt/devkitpro/a\\evil",
               "/opt/devkitpro/test", "opt/devkitpro/C:/foo", "opt/devkitpro/CON",
               "opt/devkitpro/COM1.exe", "opt/devkitpro/f. ", "opt/devkitpro/a//b",
               "opt/devkitpro/a/./b", "opt/devkitpro/file\nname", "opt/devkitpro/a?b",
               "other/dir/file"]
        for name in bad:
            with self.subTest(name=name), self.assertRaises(BuildError):
                sdk.relative_member(name)

    def test_pinned_download_success_and_reuse(self):
        data = b"known official package bytes simulated"
        dest = self.path / "test-1.pkg.tar.zst"
        response = StubHTTPResponse(self.url, data)
        events = []
        with mock.patch.object(sdk.urllib.request, "build_opener", return_value=StubHTTPOpener(response)):
            sdk.download(self.record(data), dest, lambda **event: events.append(event))
        self.assertEqual(dest.read_bytes(), data)
        self.assertTrue(events)
        sdk.download(self.record(data), dest, lambda **event: events.append(event))
        self.assertFalse(dest.with_name(dest.name + ".partial").exists())

    def test_download_corruption_never_promoted_and_partial_removed(self):
        wanted = b"trusted bytes"
        corrupt = b"corrupt bytes"
        dest = self.path / "test-1.pkg.tar.zst"
        with mock.patch.object(sdk.urllib.request, "build_opener", return_value=StubHTTPOpener(StubHTTPResponse(self.url, corrupt))):
            with self.assertRaises(BuildError):
                sdk.download(self.record(wanted), dest, lambda **e: None)
        self.assertFalse(dest.exists())
        self.assertFalse(dest.with_name(dest.name + ".partial").exists())

    def test_redirect_host_rejected(self):
        dest = self.path / "test-1.pkg.tar.zst"
        data = b"test"
        resp = StubHTTPResponse("https://evil.test/package", data)
        with mock.patch.object(sdk.urllib.request, "build_opener", return_value=StubHTTPOpener(resp)):
            with self.assertRaises(BuildError):
                sdk.download(self.record(data), dest, lambda **e: None)
        self.assertFalse(dest.exists())

    def test_valid_extract_and_safe_hardlink(self):
        package = make_zst(self.path / "test.pkg.tar.zst", [
            (".PKGINFO", "file", b"name = test"),
            ("opt/devkitpro/devkitA64", "dir", ""),
            ("opt/devkitpro/devkitA64/bin/compiler.exe", "file", b"compiled bytes"),
            ("opt/devkitpro/devkitA64/bin/compiler-copy.exe", "link", "opt/devkitpro/devkitA64/bin/compiler.exe")])
        dest = self.path / "sdk"
        self.assertEqual(sdk.extract(package, dest, lambda **e: None), 4)
        self.assertEqual((dest / "devkitA64/bin/compiler.exe").read_bytes(), b"compiled bytes")
        self.assertEqual((dest / "devkitA64/bin/compiler-copy.exe").read_bytes(), b"compiled bytes")

    def test_malicious_extract_blocks_traversal_symlinks_duplicate_and_link_to_old_package(self):
        scenarios = [
            [("opt/devkitpro/../evil", "file", b"oops")],
            [("opt/devkitpro/bin/link", "symlink", "C:\\Windows\\system32")],
            [("opt/devkitpro/bin/A", "file", b"1"), ("opt/devkitpro/bin/a", "file", b"2")],
            [("opt/devkitpro/bin/new", "link", "opt/devkitpro/bin/old")],
        ]
        for idx, scenario in enumerate(scenarios):
            package = make_zst(self.path / f"bad{idx}.pkg.tar.zst", scenario)
            with self.subTest(case=idx), self.assertRaises(BuildError):
                sdk.extract(package, self.path / f"output{idx}", lambda **e: None)

    def test_size_cap(self):
        package = make_zst(self.path / "huge.pkg.tar.zst", [
            ("opt/devkitpro/a", "file", b"x" * 10)])
        with mock.patch.object(sdk, "MAX_UNPACKED_PACKAGE_BYTES", 5):
            with self.assertRaises(BuildError):
                sdk.extract(package, self.path / "output", lambda **e: None)

    def test_prepare_verifies_devkit_hash_and_never_overwrites(self):
        input_data = b"fake compiler build"
        pkg = make_zst(self.path / "p.pkg.tar.zst", [
            ("opt/devkitpro/devkitA64/bin/aarch64-none-elf-gcc.exe", "file", input_data)])
        record = {"name": "p.pkg.tar.zst", "url": "https://pkg.devkitpro.org/packages/p.pkg.tar.zst",
                  "bytes": pkg.stat().st_size, "sha256": hashlib.sha256(pkg.read_bytes()).hexdigest()}
        payload = self.path / "payload"
        payload.mkdir()
        (payload / "sdk-plan.json").write_text(json.dumps({"schema": 1, "packages": [record]}))
        (payload / "manifest.json").write_text(json.dumps({"sdk_files": {
            "devkitA64/bin/aarch64-none-elf-gcc.exe": {
                "root": "devkitpro", "sha256": hashlib.sha256(input_data).hexdigest()}}}))
        out = self.path / "sdk-result"
        with mock.patch.object(sdk, "download", side_effect=lambda rec, dest, emit: shutil.copyfile(pkg, dest)):
            devkit, mesa = sdk.prepare(payload, out)
        self.assertIsNone(mesa)
        self.assertEqual((devkit / "devkitA64/bin/aarch64-none-elf-gcc.exe").read_bytes(), input_data)
        self.assertTrue((out / "sdk-origin.json").exists())
        with self.assertRaises(BuildError):
            sdk.prepare(payload, out)

    def test_missing_mesa_detected_if_requested(self):
        payload = self.path / "payload"
        payload.mkdir()
        (payload / "manifest.json").write_text(json.dumps({"sdk_files": {
            "lib/libEGL.a": {"root": "mesa", "sha256": "0" * 64}}}))
        with self.assertRaises(BuildError):
            sdk.verify_sdk_files(payload, self.path, self.path / "mesa-not-present")


if __name__ == "__main__":
    unittest.main()
