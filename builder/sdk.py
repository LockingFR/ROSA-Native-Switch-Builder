"""Version-pinned, game-data-free SDK provisioning for ROSA Builder.

This module installs only the devkitPro toolchain described by an explicitly
pinned sdk-plan.json. It does NOT install Mesa Switch, load ROMs, or change a
system-wide SDK. It is designed for integration with the existing Builder.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tarfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Callable

try:
    from core import BuildError, sha
except ImportError as exc:
    # Do not silently replace the Builder's actual API in production. A dummy
    # core.py is supplied ONLY in unit tests.
    raise ImportError("ROSA Builder core.py is required to integrate sdk.py") from exc

HOST = "pkg.devkitpro.org"
MAX_PACKAGE_BYTES = 512 * 1024**2
MAX_UNPACKED_PACKAGE_BYTES = 1024**3
MAX_UNPACKED_ALL_BYTES = 3 * 1024**3
MAX_MEMBERS_PER_PACKAGE = 20_000
MAX_PACKAGES = 64
_BLOCK_SIZE = 1024 * 1024
_PACKAGE_NAME = re.compile(r"[A-Za-z0-9_.+-]+\.pkg\.tar\.zst\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_RESERVED_WINDOWS = re.compile(r"(?i)(?:CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9]|CONIN\$|CONOUT\$)(?:\..*)?\Z")
_BAD_WINDOWS_CHARS = set('<>:"\\|?*')
_METADATA = {".PKGINFO", ".BUILDINFO", ".MTREE", ".INSTALL"}


def package_url(value: str) -> str:
    """Only version-pinned HTTPS packages from the official devkitPro host."""
    if not isinstance(value, str) or any(ord(c) < 32 for c in value):
        raise BuildError("Unapproved SDK download address.")
    try:
        u = urllib.parse.urlsplit(value)
        port = u.port
    except (ValueError, TypeError) as exc:
        raise BuildError("Unapproved SDK download address.") from exc
    if (u.scheme != "https" or u.hostname != HOST or port not in (None, 443)
            or u.username or u.password or u.query or u.fragment
            or not u.path.startswith("/packages/")
            or u.path.startswith("/packages//")
            or any(seg in ("", ".", "..") for seg in u.path.split("/")[1:])
            or "%" in u.path or "\\" in u.path):
        raise BuildError("Unapproved SDK download address.")
    return value


class OfficialRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        package_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def validated_record(record: dict) -> dict:
    if not isinstance(record, dict):
        raise BuildError("Invalid pinned SDK package record.")
    name = record.get("name")
    expected = record.get("sha256")
    size = record.get("bytes")
    url = record.get("url")
    if (not isinstance(name, str) or not _PACKAGE_NAME.fullmatch(name)
            or not isinstance(expected, str) or not _DIGEST.fullmatch(expected)
            or type(size) is not int or not 0 < size < MAX_PACKAGE_BYTES
            or not isinstance(url, str)):
        raise BuildError("Invalid pinned SDK package record.")
    package_url(url)
    if urllib.parse.urlsplit(url).path.rsplit("/", 1)[-1] != name:
        raise BuildError("SDK package URL does not match pinned filename.")
    return record


def _emit(emit, **event):
    if emit is not None:
        emit(**event)


def download(record: dict, destination: Path, emit: Callable) -> None:
    """Download to a temporary file, verify length and SHA-256, then rename."""
    validated_record(record)
    destination = Path(destination)
    expected, size = record["sha256"], record["bytes"]
    if destination.exists():
        if destination.is_file() and destination.stat().st_size == size and sha(destination) == expected:
            _emit(emit, stage="download", message="Reusing verified " + record["name"], done=size, total=size)
            return
        raise BuildError("An SDK package file already exists but fails verification; it was preserved.")
    partial = destination.with_name(destination.name + ".partial")
    if partial.exists():
        raise BuildError("An incomplete SDK download exists; remove the .partial file after checking it.")
    request = urllib.request.Request(record["url"], headers={
        "User-Agent": "ROSA-Builder/0.1", "Accept-Encoding": "identity"})
    opener = urllib.request.build_opener(OfficialRedirect())
    promoted = False
    try:
        with opener.open(request, timeout=30) as response:
            package_url(response.geturl())
            length = response.headers.get("Content-Length")
            if length is not None:
                try:
                    if int(length) != size:
                        raise BuildError("Official SDK package size changed; obtain an updated pinned plan.")
                except ValueError as exc:
                    raise BuildError("Invalid HTTP content length for SDK package.") from exc
            digest = hashlib.sha256()
            done = 0
            _emit(emit, stage="download", message="Downloading " + record["name"], done=0, total=size)
            with partial.open("xb") as out:
                while True:
                    block = response.read(min(_BLOCK_SIZE, size - done + 1))
                    if not block:
                        break
                    done += len(block)
                    if done > size:
                        raise BuildError("SDK download exceeded its pinned size.")
                    out.write(block)
                    digest.update(block)
                    _emit(emit, stage="download", message="Downloading " + record["name"], done=done, total=size)
            if done != size or digest.hexdigest() != expected:
                raise BuildError("SDK download failed SHA-256/size verification. Nothing was executed.")
        partial.rename(destination)
        promoted = True
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise BuildError("Could not download the pinned SDK from the official devkitPro host. No game data was uploaded.") from exc
    finally:
        # A failed/corrupt partial is not reusable: a fresh retry can run safely.
        if not promoted and partial.is_file():
            partial.unlink()


def relative_member(name: str) -> Path:
    """Validate an archive member against Windows-safe relative paths."""
    if not isinstance(name, str) or not name or len(name) > 4096 or name.startswith("/"):
        raise BuildError("Unsafe SDK archive path.")
    if any(ord(c) < 32 or c in _BAD_WINDOWS_CHARS for c in name):
        raise BuildError("Unsafe SDK archive path.")
    # Keep a trailing '/' on directory entries valid, but refuse ambiguous
    # aliases (empty middle parts, dot segments, Windows trailing dots/spaces).
    raw = name.rstrip("/").split("/")
    if (not raw or any(not p or p in (".", "..") or len(p) > 255
                       or p.endswith((" ", ".")) or _RESERVED_WINDOWS.fullmatch(p)
                       for p in raw)):
        raise BuildError("Unsafe SDK archive path.")
    if raw[:2] != ["opt", "devkitpro"]:
        raise BuildError("SDK file outside the official toolchain prefix.")
    return Path(*raw[2:])


def _decoder():
    try:
        import zstandard
    except ImportError as exc:
        raise BuildError("The Builder must bundle the zstandard Python module for .pkg.tar.zst archives.") from exc
    return zstandard.ZstdDecompressor()


def extract(package: Path, destination: Path, emit: Callable,
            seen_global: set | None = None, budget: list | None = None) -> int:
    """Extract only regular files and safe hardlinks from a devkitPro tar.zst.

    The parent staging directory must be newly created by prepare().
    Any failure leaves staging data for analysis, never touches an existing SDK.
    """
    package, destination = Path(package), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    seen = set() if seen_global is None else seen_global
    written = set()
    links = []
    total = 0
    count = 0
    with package.open("rb") as raw, _decoder().stream_reader(raw) as stream:
        with tarfile.open(fileobj=stream, mode="r|") as archive:
            for member in archive:
                count += 1
                if count > MAX_MEMBERS_PER_PACKAGE:
                    raise BuildError("Too many SDK archive members.")
                if member.name in _METADATA:
                    if not member.isfile() or member.size < 0 or member.size > 1024**2:
                        raise BuildError("Invalid SDK package metadata.")
                    continue
                # Official packages include their ancestor directory entry.
                # Skip only this exact directory, never a file/link or sibling.
                if member.name in ('opt','opt/') and member.isdir():
                    continue
                rel = relative_member(member.name)
                if not rel.parts:
                    if member.isdir():
                        continue
                    raise BuildError("Invalid SDK prefix entry.")
                key = rel.as_posix().casefold()
                target = destination / rel
                if member.isdir():
                    # Refuse a later directory that collides with a prior file.
                    if target.exists() and not target.is_dir():
                        raise BuildError("Conflicting SDK directory entry.")
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                if key in seen or target.exists():
                    raise BuildError("Duplicate SDK file: not overwriting existing SDK data.")
                seen.add(key)
                if member.isfile():
                    if member.size < 0:
                        raise BuildError("Invalid SDK member length.")
                    increase = member.size
                elif member.islnk():
                    source = relative_member(member.linkname)
                    if not source.parts:
                        raise BuildError("Invalid SDK hardlink target.")
                    links.append((rel, source))
                    increase = 0
                else:
                    raise BuildError("SDK symlink or special file rejected.")
                total += increase
                if total > MAX_UNPACKED_PACKAGE_BYTES:
                    raise BuildError("SDK package extraction exceeds size cap.")
                if budget is not None:
                    budget[0] += increase
                    if budget[0] > MAX_UNPACKED_ALL_BYTES:
                        raise BuildError("SDK installation exceeds total size cap.")
                target.parent.mkdir(parents=True, exist_ok=True)
                if member.isfile():
                    src = archive.extractfile(member)
                    if src is None:
                        raise BuildError("Cannot read SDK archive member.")
                    with src, target.open("xb") as out:
                        shutil.copyfileobj(src, out, _BLOCK_SIZE)
                    if target.stat().st_size != member.size:
                        raise BuildError("Extracted SDK file size mismatch.")
                    written.add(rel)
                if count % 64 == 0:
                    _emit(emit, stage="sdk", message=f"Extracted {count} package members")
    for rel, source in links:
        # Hardlinks must point to a genuine regular file in the *same* package.
        if source not in written:
            raise BuildError("SDK hardlink does not target a regular file in this package.")
        file_size = (destination / source).stat().st_size
        total += file_size
        if total > MAX_UNPACKED_PACKAGE_BYTES:
            raise BuildError("SDK hardlink copies exceed size cap.")
        if budget is not None:
            budget[0] += file_size
            if budget[0] > MAX_UNPACKED_ALL_BYTES:
                raise BuildError("SDK installation exceeds total size cap.")
        shutil.copyfile(destination / source, destination / rel)
    return count


def _load_plan(payload: Path):
    path = payload / "sdk-plan.json"
    if not path.is_file():
        raise BuildError("sdk-plan.json is missing. Managed SDK setup is not configured for this Builder.")
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise BuildError("Cannot parse managed SDK plan.") from exc
    if not isinstance(plan, dict) or plan.get("schema") != 1:
        raise BuildError("Invalid managed SDK plan schema.")
    records = plan.get("packages")
    if not isinstance(records, list) or not 0 < len(records) <= MAX_PACKAGES:
        raise BuildError("Managed SDK plan must pin 1-64 packages.")
    names = set()
    for record in records:
        validated_record(record)
        name = record["name"].casefold()
        if name in names:
            raise BuildError("Duplicate SDK package in pin plan.")
        names.add(name)
    return plan


def verify_sdk_files(payload: Path, devkit: Path, mesa: Path | None) -> None:
    """Compare built SDK files to the hashes already pinned in DATA manifest."""
    manifest_path = payload / "manifest.json"
    if not manifest_path.is_file():
        raise BuildError("The Builder manifest.json is missing; SDK cannot be verified.")
    try:
        required = json.loads(manifest_path.read_text(encoding="utf-8"))["sdk_files"]
    except (ValueError, OSError, KeyError) as exc:
        raise BuildError("Invalid SDK file manifest.") from exc
    if not isinstance(required, dict) or not required:
        raise BuildError("SDK hash inventory is missing.")
    for name, info in required.items():
        if not isinstance(info, dict) or not _DIGEST.fullmatch(info.get("sha256", "")):
            raise BuildError("Invalid SDK file hash inventory.")
        # Path is under an already selected local root; never trust traversal.
        if not isinstance(name, str) or not name or any(
                p in ("", ".", "..") for p in name.split("/")) or \
                any(ch in _BAD_WINDOWS_CHARS or ord(ch) < 32 for ch in name):
            raise BuildError("Invalid SDK file path inventory.")
        root_name = info.get("root")
        if root_name == "devkitpro":
            root = devkit
        elif root_name == "mesa":
            if mesa is None:
                # Caller may provision devkitPro first, then prompt for Mesa.
                continue
            root = mesa
        else:
            raise BuildError("Unknown SDK root in file manifest.")
        target = root / Path(*name.split("/"))
        if not target.is_file() or sha(target) != info["sha256"]:
            raise BuildError("SDK file missing or hash mismatch: " + name)


def verify_mesa_files(payload: Path, mesa: Path) -> None:
    """Fail before SDK download if Mesa does not match R7/B20 pinned files."""
    path = Path(payload) / "manifest.json"
    if not path.is_file():
        raise BuildError("Missing authenticated DATA manifest for Mesa SDK.")
    try:
        required = json.loads(path.read_text(encoding="utf-8"))["sdk_files"]
    except (OSError, ValueError, KeyError) as exc:
        raise BuildError("Invalid Mesa SDK inventory.") from exc
    selected = {name: info for name, info in required.items()
                if isinstance(info, dict) and info.get("root") == "mesa"}
    if not selected:
        raise BuildError("No pinned Mesa SDK files in authenticated DATA manifest.")
    # Reuse the full path and SHA-256 validation without requiring an installed
    # devkitPro compiler (which this mode will download).
    for name, info in selected.items():
        if (not isinstance(name, str) or not name or any(
                x in ("", ".", "..") for x in name.split("/"))
                or any(c in _BAD_WINDOWS_CHARS or ord(c) < 32 for c in name)
                or not isinstance(info.get("sha256"), str)
                or not _DIGEST.fullmatch(info["sha256"])):
            raise BuildError("Invalid Mesa SDK inventory entry.")
        target = Path(mesa).joinpath(*name.split("/"))
        if not target.is_file() or sha(target) != info["sha256"]:
            raise BuildError("Missing or incompatible Mesa SDK file: " + name)


def prepare(payload, work, emit=lambda **event: None, mesa_root=None):
    """Stage verified devkitPro packages without changing any global SDK.

    Caller still needs Mesa Switch 26.2.4 (not bundled in R7 DATA). The
    returned Mesa path may be None; require it before attempting a game build.
    """
    payload, work = Path(payload), Path(work)
    plan = _load_plan(payload)  # fail BEFORE creating output directory
    if work.exists():
        raise BuildError("Managed SDK output already exists; preserved.")
    work.mkdir(parents=True)
    downloads = work / "packages"
    downloads.mkdir()
    staged = work / "devkitpro.partial"
    staged.mkdir()
    seen = set()
    budget = [0]
    for record in plan["packages"]:
        package = downloads / record["name"]
        download(record, package, emit)
        _emit(emit, stage="sdk", message="Preparing " + record["name"])
        extract(package, staged, emit, seen_global=seen, budget=budget)
    # Verify toolchain before promoting staged install.
    mesa = Path(mesa_root) if mesa_root is not None else None
    verify_sdk_files(payload, staged, mesa)
    devkit = work / "devkitpro"
    staged.rename(devkit)
    (work / "sdk-origin.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    _emit(emit, stage="sdk", message="Verified SDK prepared locally")
    return devkit, mesa
